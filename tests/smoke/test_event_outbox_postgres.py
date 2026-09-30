"""Dos workers, RLS forzado y reenvío con commits PostgreSQL reales."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from fastapi import HTTPException
from threading import Event as Signal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import Base_CORE, MSP, Condominio, Casa, Visita, EventOutbox
from backend.db.event import Base_EVENT, Event
from backend.services import visita_service
from backend.services.event_outbox import contexto_evento, enviar_pendientes, publicar_evento, rechazar_operacion


@pytest.mark.integration
def test_workers_concurrentes_rls_y_reenvio():
    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere PostgreSQL desechable con rol sin bypass")
    engine = create_engine(url)
    schema = "axs_outbox_" + uuid.uuid4().hex[:12]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    factory = sessionmaker(bind=scoped)
    taken, release = Signal(), Signal()
    try:
        with engine.begin() as conn:
            assert not conn.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")).scalar_one()
            conn.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(scoped, tables=[MSP.__table__, Condominio.__table__, Casa.__table__, Visita.__table__, EventOutbox.__table__])
        Base_EVENT.metadata.create_all(scoped)
        with factory() as db:
            db.add(MSP(msp_id="a", nombre="A"))
            db.flush()
            db.add_all([Condominio(condominio_id=c, msp_id="a", nombre=c) for c in ("a1", "a2")])
            db.commit()
        with engine.begin() as conn:
            for table in ("visitas", "event_outbox"):
                conn.execute(text(f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY"))
                conn.execute(text(f"ALTER TABLE {schema}.{table} FORCE ROW LEVEL SECURITY"))
                conn.execute(text(f"CREATE POLICY tenant ON {schema}.{table} USING (condominio_id = current_setting('app.tenant_id',true)) WITH CHECK (condominio_id = current_setting('app.tenant_id',true))"))
        audit = contexto_evento(SimpleNamespace(usuario_id="guard"), "test-token")
        with factory() as db:
            _set_postgres_tenant(db, "a1")
            data = SimpleNamespace(nombre_visitante="Test", tipo_visita="eventual", vigencia=None)
            row = visita_service.crear_visita(db, data, "a1", auditoria=audit)
            visita_service.registrar_entrada(db, row.visita_id, auditoria=audit)
            assert db.query(EventOutbox).count() == 2
            with pytest.raises(HTTPException) as rejected:
                rechazar_operacion(db, SimpleNamespace(usuario_id="guard"), "test-token",
                                  "a1", row.visita_id, detail="QR ya utilizado", entidad="qr", accion="validar")
            assert rejected.value.status_code == 400
            assert db.query(EventOutbox).count() == 3
        with factory() as db:
            assert db.query(EventOutbox).count() == 0
            _set_postgres_tenant(db, "a2")
            assert db.query(EventOutbox).count() == 0
        now = datetime.utcnow() + timedelta(seconds=1)
        def slow_publish(event_db, payload):
            taken.set()
            assert release.wait(15)
            publicar_evento(event_db, payload)
        def first_worker():
            with factory() as db:
                return enviar_pendientes(db, "a1", factory, now=now, publisher=slow_publish)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(first_worker)
            try:
                assert taken.wait(15)
                with factory() as db:
                    assert enviar_pendientes(db, "a1", factory, now=now) == 0
            finally:
                release.set()
            assert first.result(timeout=20) == 3
        with factory() as db:
            _set_postgres_tenant(db, "a1")
            rows = db.query(EventOutbox).all()
            assert all(r.delivered_at and r.attempts == 1 for r in rows)
            assert db.query(Event).count() == 3
            # Simular pérdida del ACK: EVENT ya confirmó, CORE vuelve a tener pendiente.
            rows[0].delivered_at = None
            db.commit()
        with factory() as restarted:
            assert enviar_pendientes(restarted, "a1", factory, now=now) == 1
            assert restarted.query(Event).count() == 3
    finally:
        release.set()
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
