"""Cola global bajo FORCE RLS sin ampliar el alcance de visitas."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Event as Signal

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DBAPIError

from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import Base_CORE, MSP, Condominio, Casa, Usuario, Visita, SecurityOutbox
from backend.db.event import Base_EVENT, Event
from backend.services.security_outbox import guardar_intento, enviar_seguridad


@pytest.mark.integration
def test_seguridad_independiente_con_rls_y_workers_concurrentes():
    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere PostgreSQL desechable con rol sin bypass")
    engine = create_engine(url)
    schema = "axs_security_" + uuid.uuid4().hex[:12]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    factory = sessionmaker(bind=scoped)
    taken, release = Signal(), Signal()
    try:
        with engine.begin() as conn:
            assert not conn.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")).scalar_one()
            conn.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(scoped, tables=[MSP.__table__, Condominio.__table__, Casa.__table__, Usuario.__table__, Visita.__table__, SecurityOutbox.__table__])
        Base_EVENT.metadata.create_all(scoped)
        with factory() as db:
            db.add(MSP(msp_id="a", nombre="A"))
            db.flush()
            db.add_all([Condominio(condominio_id=t, msp_id="a", nombre=t) for t in ("a1", "a2")])
            db.flush()
            db.add_all([Visita(visita_id=t, condominio_id=t, nombre_visitante=t, estado="pendiente") for t in ("a1", "a2")])
            db.commit()
        with engine.begin() as conn:
            for table in ("visitas", "security_outbox"):
                conn.execute(text(f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY"))
                conn.execute(text(f"ALTER TABLE {schema}.{table} FORCE ROW LEVEL SECURITY"))
            conn.execute(text(f"CREATE POLICY tenant ON {schema}.visitas USING (condominio_id = current_setting('app.tenant_id',true)) WITH CHECK (condominio_id = current_setting('app.tenant_id',true))"))
            conn.execute(text(f"CREATE POLICY backend ON {schema}.security_outbox USING (true) WITH CHECK (payload->>'tenant_id' = 'PLATFORM_SECURITY' AND payload->>'event_uid'=event_uid AND payload->>'accion'='denegar' AND payload->>'resultado'='denegado')"))
        app = FastAPI()
        @app.get("/protected/{entity}")
        def protected(entity): return {}
        request = Request({"type": "http", "path": "/protected/private-secret", "method": "GET", "headers": [], "app": app})
        with factory() as business:
            _set_postgres_tenant(business, "a1")
            row = business.query(Visita).filter_by(visita_id="a1").one()
            row.estado = "entrada_registrada"
            business.flush()
            guardar_intento(request, "NO_SESSION", factory=factory)
            assert business.query(Visita).filter_by(visita_id="a2").first() is None
            business.rollback()  # el commit de seguridad no confirmó este negocio
            assert business.query(Visita).filter_by(visita_id="a1").one().estado == "pendiente"
        with factory() as global_db:
            assert global_db.query(Visita).count() == 0
            row = global_db.query(SecurityOutbox).one()
            assert row.payload["metadata_json"]["route"] == "/protected/{entity}"
            assert "private-secret" not in str(row.payload)
            bad = {**row.payload, "event_uid": "sec_invalid", "tenant_id": "a2"}
            global_db.add(SecurityOutbox(event_uid="sec_invalid", payload=bad, created_at=datetime.utcnow(), next_attempt_at=datetime.utcnow()))
            with pytest.raises(DBAPIError): global_db.flush()
            global_db.rollback()
            assert global_db.query(SecurityOutbox).count() == 1
        now = datetime.utcnow() + timedelta(seconds=1)
        def slow_publish(event_db, payload):
            from backend.services.event_outbox import publicar_evento
            taken.set()
            assert release.wait(15)
            publicar_evento(event_db, payload)
        def worker():
            with factory() as db:
                return enviar_seguridad(db, factory, now=now, publisher=slow_publish)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker)
            try:
                assert taken.wait(15)
                with factory() as db: assert enviar_seguridad(db, factory, now=now) == 0
            finally: release.set()
            assert first.result(timeout=20) == 1
        with factory() as db:
            assert db.query(Event).count() == 1
            row = db.query(SecurityOutbox).one()
            row.delivered_at = None  # simular pérdida del ACK tras commit EVENT
            db.commit()
        with factory() as restarted:
            assert enviar_seguridad(restarted, factory, now=now) == 1
            assert restarted.query(Event).count() == 1
            _set_postgres_tenant(restarted, "a2")
            assert restarted.query(Visita).filter_by(visita_id="a2").one().estado == "pendiente"
    finally:
        release.set()
        with engine.begin() as conn: conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
