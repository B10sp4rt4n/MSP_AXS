"""Dos proveedores: HTTP, revocación con el mismo JWT y auditoría PostgreSQL."""
import os
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.core.auth.jwt import create_access_token
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import (
    Base_CORE, MSP, Condominio, Casa, Usuario, MSPMembership, UserTenantScope,
    AccessLevel, ScopeStatus, Visita, EventOutbox, SecurityOutbox, get_core_db,
)
from backend.db.gov import Authority, AuthorityType, GovStatus, get_gov_db
from backend.db.event import Base_EVENT, Event, get_event_db
from backend.services import security_outbox


@pytest.mark.integration
def test_proveedores_http_cruces_revocacion_y_auditoria(db_gov_session, monkeypatch):
    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere PostgreSQL desechable sin bypass")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    suffix = uuid.uuid4().hex[:12]
    core_schema, event_schema = "axs_mp_" + suffix, "axs_me_" + suffix
    core = engine.execution_options(schema_translate_map={None: core_schema})
    event = engine.execution_options(schema_translate_map={None: event_schema})
    core_factory, event_factory = sessionmaker(bind=core), sessionmaker(bind=event)
    previous = app.dependency_overrides.copy()
    def core_db():
        with core_factory() as db:
            yield db
    def event_db():
        with event_factory() as db:
            yield db
    try:
        with engine.begin() as conn:
            assert not conn.execute(text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )).scalar_one()
            conn.execute(text(f"CREATE SCHEMA {core_schema}"))
            conn.execute(text(f"CREATE SCHEMA {event_schema}"))
        Base_CORE.metadata.create_all(core)
        Base_EVENT.metadata.create_all(event)
        with core_factory() as db:
            db.add_all([MSP(msp_id=m, nombre=m) for m in ("a", "b")])
            db.flush()
            db.add_all([Condominio(condominio_id=m + "1", msp_id=m, nombre=m) for m in ("a", "b")])
            db.flush()
            db.add(Usuario(usuario_id="operator", nombre="Operator",
                email="operator@test.local", rol="MSP_ADMIN"))
            for m in ("a", "b"):
                db.add(Usuario(usuario_id="admin_" + m, nombre="Admin " + m,
                    email=m + "@test.local", rol="MSP_ADMIN"))
                db.add(Usuario(usuario_id="target_" + m, nombre="Guard " + m,
                    email="target_" + m + "@test.local", rol="GUARDIA",
                    condominio_id=m + "1", msp_id=m))
            db.flush()
            for m in ("a", "b"):
                db.add(MSPMembership(usuario_id="admin_" + m, msp_id=m))
                db.add(UserTenantScope(usuario_id="target_" + m, tenant_id=m + "1",
                    access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO))
                db.add(Casa(casa_id="home_" + m, condominio_id=m + "1", numero="101", tipo="casa"))
                db.add(Visita(visita_id="v_" + m, condominio_id=m + "1",
                    nombre_visitante="Visitor " + m, estado="pendiente", tipo_visita="eventual", casa_unidad="101",
                    vigencia=datetime.utcnow() + timedelta(days=1)))
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
        db_gov_session.add(Authority(authority_id="test_operator", identity_id="operator",
            tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
        db_gov_session.commit()
        app.dependency_overrides[get_core_db] = core_db
        app.dependency_overrides[get_event_db] = event_db
        app.dependency_overrides[get_gov_db] = lambda: db_gov_session
        monkeypatch.setattr(security_outbox, "SessionFactory", core_factory)
        headers = {m: {"Authorization": "Bearer " + create_access_token(
            "admin_" + m, "MSP_ADMIN")} for m in ("a", "b")}
        operator = {"Authorization": "Bearer " + create_access_token("operator", "MSP_ADMIN")}
        def snapshot():
            # Todas las columnas de negocio, scopes, membresías y outbox operativo.
            result = {}
            with core_factory() as db:
                for model in (MSP, Condominio, Casa, Usuario, MSPMembership, UserTenantScope):
                    result[model.__tablename__] = [
                        tuple(getattr(row, c.name) for c in model.__table__.columns)
                        for row in db.query(model).order_by(*model.__table__.primary_key.columns).all()
                    ]
                for tenant in ("a1", "b1"):
                    _set_postgres_tenant(db, tenant)
                    for model in (Visita, EventOutbox):
                        result[(tenant, model.__tablename__)] = [
                            tuple(getattr(row, c.name) for c in model.__table__.columns)
                            for row in db.query(model).order_by(*model.__table__.primary_key.columns).all()
                        ]
            return result
        expected = []
        with TestClient(app) as client:
            def denied(caller, method, path, body=None, reason="SCOPE_DENIED"):
                before = snapshot()
                with core_factory() as db:
                    ids = {r.event_uid for r in db.query(SecurityOutbox).all()}
                response = client.request(method, path, json=body, headers=headers[caller])
                assert response.status_code == 403, response.text
                assert snapshot() == before, (method, path)
                with core_factory() as db:
                    rows = [r for r in db.query(SecurityOutbox).all() if r.event_uid not in ids]
                    assert len(rows) == 1
                    p = rows[0].payload
                    assert p["identity_id"] == "admin_" + caller
                    assert p["motivo"] == reason
                    assert p["metadata_json"]["identity_verified"]
                    assert p["metadata_json"]["method"] == method
                    assert p["metadata_json"]["route"].split("?")[0] != "unknown_route"
                    assert headers[caller]["Authorization"][7:] not in str(p)
                    assert "target_" not in str(p) and "Blocked" not in str(p)
                    expected.append(rows[0].event_uid)
            # Cada administrador ve y opera su proveedor.
            for m in ("a", "b"):
                assert {r["msp_id"] for r in client.get("/msps/", headers=headers[m]).json()} == {m}
                assert {r["condominio_id"] for r in client.get(
                    "/condominios/", headers=headers[m]).json()} == {m + "1"}
                own = client.get("/condominios/" + m + "1/usuarios", headers=headers[m])
                assert own.status_code == 200
                assert {r["usuario_id"] for r in own.json()} == {"target_" + m}
                assert client.patch("/visitas/v_" + m + "/entrada?condominio_id=" + m + "1",
                    headers=headers[m]).status_code == 200
            # IDs conocidos no conceden acceso. Ensayo simétrico A->B y B->A.
            for caller, target in (("a", "b"), ("b", "a")):
                tenant, visit = target + "1", "v_" + target
                denied(caller, "GET", "/condominios/" + tenant + "/usuarios")
                denied(caller, "GET", "/visitas/" + visit + "?condominio_id=" + tenant)
                denied(caller, "PATCH", "/visitas/" + visit + "/salida?condominio_id=" + tenant)
                denied(caller, "POST", "/condominios/" + tenant + "/casas",
                    {"numero": "Blocked", "tipo": "casa"})
                denied(caller, "PATCH", "/condominios/" + tenant + "/usuarios/target_" + target,
                    {"nombre": "Blocked", "email": "target_" + target + "@test.local", "rol": "GUARDIA"})
                denied(caller, "POST", "/condominios/",
                    {"nombre": "Blocked", "msp_id": target}, reason="MSP_DENIED")
                denied(caller, "PUT", "/msps/" + target + "/admins/admin_" + caller,
                    reason="PLATFORM_DENIED")
            # Revocación legítima por operador; se reutiliza exactamente el JWT.
            old_token = headers["a"].copy()
            response = client.delete("/msps/a/admins/admin_a", headers=operator)
            assert response.status_code == 200
            assert response.json()["estado"] == "revocado"
            assert headers["a"] == old_token
            assert client.get("/auth/me", headers=old_token).status_code == 200  # sesión aún válida
            assert client.get("/msps/", headers=old_token).json() == []
            assert client.get("/condominios/", headers=old_token).json() == []
            denied("a", "GET", "/condominios/a1/usuarios")
            denied("a", "PATCH", "/visitas/v_a/salida?condominio_id=a1")
            denied("a", "POST", "/condominios/a1/casas", {"numero": "Blocked", "tipo": "casa"})
            assert client.get("/condominios/b1/usuarios", headers=headers["b"]).status_code == 200
            # Rechazos en PostgreSQL independientes, entrega a EVENT y sin duplicados.
            with core_factory() as db:
                assert security_outbox.enviar_seguridad(db, event_factory,
                    now=datetime.utcnow() + timedelta(seconds=1)) == len(expected)
            with core_factory() as db:
                assert security_outbox.enviar_seguridad(db, event_factory) == 0
                assert all(r.delivered_at is not None for r in db.query(SecurityOutbox).all())
                assert db.query(Visita).count() == 0  # conexión nueva sin contexto
            with event_factory() as db:
                events = db.query(Event).all()
                assert {r.event_uid for r in events} == set(expected)
                assert len(events) == len(expected) == 17
                from backend.core.event.registry import verificar_integridad_evento
                assert all(verificar_integridad_evento(row) for row in events)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {core_schema} CASCADE"))
            conn.execute(text(f"DROP SCHEMA IF EXISTS {event_schema} CASCADE"))
        engine.dispose()
