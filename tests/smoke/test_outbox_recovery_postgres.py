"""Recuperación con conexión TCP fallida y muerte real del worker antes del ACK.

Sólo AXS_TEST_POSTGRES_URL desechable; jamás utiliza las conexiones de producción.
CORE y EVENT ocupan esquemas distintos y conexiones independientes.
"""
import os
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import Base_CORE, MSP, Condominio, Casa, Usuario, Visita, EventOutbox, SecurityOutbox
from backend.db.event import Base_EVENT, Event
from backend.core.event.registry import verificar_integridad_evento
from backend.services.event_outbox import contexto_evento, encolar_visita
from backend.services.security_outbox import guardar_intento


# Cada invocación reconstruye engines y sesiones en un proceso nuevo.
WORKER = """
import json, os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from backend.services.event_outbox import enviar_pendientes, publicar_evento
from backend.services.security_outbox import enviar_seguridad

url = os.environ["AXS_TEST_POSTGRES_URL"]
core = create_engine(url).execution_options(
    schema_translate_map={None: os.environ["AXS_RECOVERY_CORE"]})
event_url = make_url(url)
mode = os.environ["AXS_RECOVERY_MODE"]
if mode == "outage":
    event_url = event_url.set(host="127.0.0.1", port=int(os.environ["AXS_RECOVERY_PORT"]))
event = create_engine(event_url, connect_args={"connect_timeout": 2}).execution_options(
    schema_translate_map={None: os.environ["AXS_RECOVERY_EVENT"]})
factory = sessionmaker(bind=event)
def publish(db, payload):
    publicar_evento(db, payload)
    if mode == "crash":
        os._exit(86)  # EVENT commit confirmado; CORE sigue sin commit.
with sessionmaker(bind=core)() as db:
    now = datetime.utcnow() + timedelta(minutes={"outage": 10, "crash": 20, "recover": 30}[mode])
    if os.environ["AXS_RECOVERY_KIND"] == "visita":
        result = enviar_pendientes(db, "a1", factory, now=now, publisher=publish)
    else:
        result = enviar_seguridad(db, factory, now=now, publisher=publish)
print(json.dumps({"delivered": result}))
core.dispose()
event.dispose()
"""


@pytest.mark.integration
@pytest.mark.parametrize("kind", ["visita", "seguridad"])
def test_caida_tcp_muerte_worker_y_recuperacion_sin_duplicados(kind):
    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere PostgreSQL desechable con rol sin bypass")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    suffix = uuid.uuid4().hex[:12]
    core_schema, event_schema = "axs_rc_" + suffix, "axs_re_" + suffix
    core = engine.execution_options(schema_translate_map={None: core_schema})
    event = engine.execution_options(schema_translate_map={None: event_schema})
    core_factory, event_factory = sessionmaker(bind=core), sessionmaker(bind=event)
    # Reservar puerto sin listen: el kernel rechaza la conexión, sin servidor ficticio.
    closed_port = socket.socket()
    closed_port.bind(("127.0.0.1", 0))
    try:
        with engine.begin() as conn:
            assert not conn.execute(text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )).scalar_one()
            conn.execute(text(f"CREATE SCHEMA {core_schema}"))
            conn.execute(text(f"CREATE SCHEMA {event_schema}"))
        Base_CORE.metadata.create_all(core, tables=[
            MSP.__table__, Condominio.__table__, Casa.__table__, Usuario.__table__, Visita.__table__,
            EventOutbox.__table__, SecurityOutbox.__table__,
        ])
        Base_EVENT.metadata.create_all(event)
        with core_factory() as db:
            db.add(MSP(msp_id="a", nombre="A"))
            db.flush()
            db.add_all([Condominio(condominio_id=t, msp_id="a", nombre=t) for t in ("a1", "a2")])
            db.commit()
        with engine.begin() as conn:
            for table in ("visitas", "event_outbox"):
                conn.execute(text(f"ALTER TABLE {core_schema}.{table} ENABLE ROW LEVEL SECURITY"))
                conn.execute(text(f"ALTER TABLE {core_schema}.{table} FORCE ROW LEVEL SECURITY"))
                conn.execute(text(f"CREATE POLICY tenant ON {core_schema}.{table} "
                    "USING (condominio_id=current_setting('app.tenant_id',true)) "
                    "WITH CHECK (condominio_id=current_setting('app.tenant_id',true))"))
            conn.execute(text(f"ALTER TABLE {core_schema}.security_outbox ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"ALTER TABLE {core_schema}.security_outbox FORCE ROW LEVEL SECURITY"))
            conn.execute(text(f"CREATE POLICY security ON {core_schema}.security_outbox USING (true) "
                "WITH CHECK (payload->>'tenant_id'='PLATFORM_SECURITY' "
                "AND payload->>'event_uid'=event_uid AND payload->>'accion'='denegar' "
                "AND payload->>'resultado'='denegado')"))
        entered_at = datetime.utcnow()
        with core_factory() as db:
            _set_postgres_tenant(db, "a1")
            visit = Visita(visita_id="recovery", condominio_id="a1",
                nombre_visitante="Synthetic", estado="entrada_registrada",
                entrada_registrada_en=entered_at)
            db.add(visit)
            if kind == "visita":
                uid = encolar_visita(db, visit,
                    contexto_evento(SimpleNamespace(usuario_id="guard-test"), "test-only"))
            db.commit()
        if kind == "seguridad":
            app = FastAPI()
            @app.get("/protected/{entity}")
            def protected(entity):
                return {}
            request = Request({"type": "http", "method": "GET",
                "path": "/protected/private-value", "headers": [], "app": app})
            uid = guardar_intento(request, "NO_SESSION", factory=core_factory)
        model = EventOutbox if kind == "visita" else SecurityOutbox
        with core_factory() as db:
            _set_postgres_tenant(db, "a1")
            original = db.query(model).filter_by(event_uid=uid).one().payload
        child_env = {**os.environ, "AXS_RECOVERY_CORE": core_schema,
            "AXS_RECOVERY_EVENT": event_schema, "AXS_RECOVERY_KIND": kind,
            "AXS_RECOVERY_PORT": str(closed_port.getsockname()[1])}
        def run_worker(mode):
            result = subprocess.run([sys.executable, "-c", WORKER],
                env={**child_env, "AXS_RECOVERY_MODE": mode},
                capture_output=True, text=True, timeout=30)
            # No imprimir stderr ni URLs: pueden contener credenciales de conexión.
            assert result.returncode == (86 if mode == "crash" else 0), (
                mode, result.returncode)
            if mode != "crash":
                import json
                return json.loads(result.stdout.splitlines()[-1])["delivered"]
        def queue():
            with core_factory() as db:
                _set_postgres_tenant(db, "a1")
                row = db.query(model).filter_by(event_uid=uid).one()
                assert row.payload == original
                assert db.query(Visita).one().entrada_registrada_en == entered_at
                return row.attempts, row.delivered_at, row.last_error
        assert run_worker("outage") == 0
        attempts, delivered, error = queue()
        assert attempts == 1 and delivered is None and error == "OperationalError"
        with event_factory() as db:
            assert db.query(Event).count() == 0
        run_worker("crash")
        # CORE conserva el intento anterior: el proceso murió antes de su commit.
        assert queue() == (1, None, "OperationalError")
        with event_factory() as db:
            saved = db.query(Event).one()
            assert saved.event_uid == uid and verificar_integridad_evento(saved)
            assert saved.timestamp == datetime.fromisoformat(original["timestamp"])
        assert run_worker("recover") == 1
        attempts, delivered, error = queue()
        assert attempts == 2 and delivered is not None and error is None
        assert run_worker("recover") == 0
        with event_factory() as db:
            saved = db.query(Event).one()
            assert saved.event_uid == uid and verificar_integridad_evento(saved)
            assert all(getattr(saved, key) == (
                datetime.fromisoformat(value) if key == "timestamp" else value
            ) for key, value in original.items())
        with core_factory() as db:
            _set_postgres_tenant(db, "a2")
            assert db.query(Visita).count() == 0
            assert db.query(EventOutbox).count() == 0
    finally:
        closed_port.close()
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {core_schema} CASCADE"))
            conn.execute(text(f"DROP SCHEMA IF EXISTS {event_schema} CASCADE"))
        engine.dispose()
