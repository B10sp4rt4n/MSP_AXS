"""Ensayo de RLS sobre el ORM real, en un esquema PostgreSQL desechable."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import Base_CORE, Condominio, MSP, Visita, Casa
from backend.services import visita_service


@pytest.mark.integration
def test_visitas_aisladas_tras_commit_y_refresh():
    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere AXS_TEST_POSTGRES_URL de una base PostgreSQL desechable")
    engine = create_engine(url)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.fail("AXS_TEST_POSTGRES_URL debe apuntar a PostgreSQL")

    with engine.connect() as connection:
        bypass = connection.execute(text(
            "SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname = current_user"
        )).scalar_one()
    if bypass:
        engine.dispose()
        pytest.fail("El rol de la prueba tiene BYPASSRLS o SUPERUSER; usar un rol sin bypass")

    schema = f"axs_rls_{uuid.uuid4().hex[:12]}"
    # Vincular cada Session al Engine permite que db.commit() cierre la
    # transacción real. Una Session ligada a Connection externa puede dejar
    # la transacción abierta y producir un falso positivo para set_config.
    tenant_engine = engine.execution_options(schema_translate_map={None: schema})
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(tenant_engine, tables=[
            MSP.__table__, Condominio.__table__, Casa.__table__, Visita.__table__,
        ])
        with Session(tenant_engine) as db:
            db.add_all([MSP(msp_id="a", nombre="A"), MSP(msp_id="b", nombre="B")])
            db.flush()
            db.add_all([
                Condominio(condominio_id="a1", msp_id="a", nombre="A1"),
                Condominio(condominio_id="b1", msp_id="b", nombre="B1"),
            ])
            db.flush()
            db.add(Visita(visita_id="vb", condominio_id="b1", nombre_visitante="B", estado="pendiente"))
            db.commit()

        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {schema}.visitas ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {schema}.visitas FORCE ROW LEVEL SECURITY"))
            connection.execute(text(
                f"CREATE POLICY tenant_visitas ON {schema}.visitas "
                "USING (condominio_id = current_setting('app.tenant_id', true)) "
                "WITH CHECK (condominio_id = current_setting('app.tenant_id', true))"
            ))

        with Session(tenant_engine) as db:
            _set_postgres_tenant(db, "a1")
            data = SimpleNamespace(nombre_visitante="A", tipo_visita="eventual", vigencia=None)
            visita = visita_service.crear_visita(db, data, condominio_id="a1", casa_unidad="101")
            assert visita.condominio_id == "a1"  # commit + refresh del servicio
            assert db.query(Visita).filter_by(visita_id="vb").first() is None
            assert db.query(Visita).filter_by(visita_id=visita.visita_id).one().estado == "pendiente"
            assert db.query(Visita).filter_by(visita_id="vb").update({"estado": "cancelada"}) == 0
            db.commit()
            assert db.query(Visita).filter_by(visita_id="vb").first() is None
        with Session(tenant_engine) as no_context:
            assert no_context.query(Visita).count() == 0

        with Session(tenant_engine) as other:
            _set_postgres_tenant(other, "b1")
            assert other.query(Visita).filter_by(visita_id="vb").one().estado == "pendiente"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()


@pytest.mark.integration
def test_http_visitas_con_rls_y_sesiones_por_request(db_gov_session, db_event_session):
    """JWT → membresía → contexto → lectura/mutación, con commits reales."""
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.core.auth.jwt import create_access_token
    from backend.db.core import get_core_db, Usuario, MSPMembership, UserTenantScope, AccessLevel, ScopeStatus, Evidencia
    from backend.db.gov import get_gov_db
    from backend.db.gov import Policy, PolicyScope, GovStatus
    from backend.db.event import get_event_db

    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere AXS_TEST_POSTGRES_URL de PostgreSQL desechable")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    with engine.connect() as connection:
        assert not connection.execute(text(
            "SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname = current_user"
        )).scalar_one(), "El rol HTTP debe carecer de bypass"
    schema = f"axs_http_{uuid.uuid4().hex[:12]}"
    scoped = engine.execution_options(schema_translate_map={None: schema})
    previous_overrides = app.dependency_overrides.copy()

    def core_db():
        with Session(scoped) as session:
            yield session

    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(scoped)
        with Session(scoped) as db:
            db.add_all([MSP(msp_id=m, nombre=m) for m in ("a", "b")])
            db.flush()
            db.add_all([Condominio(condominio_id=f"{m}1", msp_id=m, nombre=m) for m in ("a", "b")])
            db.flush()
            db.add_all([Casa(casa_id=f"home_{m}", condominio_id=f"{m}1", numero="101", tipo="casa") for m in ("a", "b")])
            db.flush()
            db.add_all([Usuario(usuario_id=f"admin_{m}", email=f"{m}@test.local", rol="MSP_ADMIN") for m in ("a", "b")])
            db.flush()
            db.add(Usuario(usuario_id="resident_a", email="resident@test.local", rol="RESIDENTE",
                           condominio_id="a1", casa_unidad="101"))
            db.add(Usuario(usuario_id="guard_a", email="guard@test.local", rol="GUARDIA", condominio_id="a1"))
            db.flush()
            db.add(UserTenantScope(usuario_id="guard_a", tenant_id="a1", access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO))
            db.add(UserTenantScope(usuario_id="resident_a", tenant_id="a1",
                                   access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO))
            db.add_all([MSPMembership(usuario_id=f"admin_{m}", msp_id=m) for m in ("a", "b")])
            db.add_all([Visita(visita_id=f"v_{m}", condominio_id=f"{m}1", casa_unidad="101", nombre_visitante=m,
                               tipo_visita="eventual", estado="pendiente",
                               vigencia=datetime.utcnow() + timedelta(days=1)) for m in ("a", "b")])
            db.commit()
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {schema}.visitas ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {schema}.visitas FORCE ROW LEVEL SECURITY"))
            connection.execute(text(
                f"CREATE POLICY tenant_visitas ON {schema}.visitas "
                "USING (condominio_id = current_setting('app.tenant_id', true)) "
                "WITH CHECK (condominio_id = current_setting('app.tenant_id', true))"
            ))
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {schema}.evidencias ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {schema}.evidencias FORCE ROW LEVEL SECURITY"))
            connection.execute(text(
                f"CREATE POLICY tenant_evidencias ON {schema}.evidencias "
                f"USING (EXISTS (SELECT 1 FROM {schema}.visitas v WHERE v.visita_id = evidencias.visita_id "
                "AND v.condominio_id = current_setting('app.tenant_id', true))) "
                f"WITH CHECK (EXISTS (SELECT 1 FROM {schema}.visitas v WHERE v.visita_id = evidencias.visita_id "
                "AND v.condominio_id = current_setting('app.tenant_id', true)))"
            ))
        app.dependency_overrides[get_core_db] = core_db
        app.dependency_overrides[get_gov_db] = lambda: db_gov_session
        app.dependency_overrides[get_event_db] = lambda: db_event_session
        db_gov_session.add(Policy(policy_id="http_create", nombre="Create visits", ambito=PolicyScope.GLOBAL,
                                  accion_objetivo="crear_visita", limites={}, estado=GovStatus.ACTIVO))
        db_gov_session.add(Policy(policy_id="http_qr", nombre="Generate QR", ambito=PolicyScope.GLOBAL,
                                  accion_objetivo="generar_qr", limites={}, estado=GovStatus.ACTIVO))
        db_gov_session.commit()
        headers = {m: {"Authorization": f"Bearer {create_access_token(f'admin_{m}', 'MSP_ADMIN')}"} for m in ("a", "b")}
        with TestClient(app) as client:
            resident_headers = {"Authorization": f"Bearer {create_access_token('resident_a', 'RESIDENTE')}"}
            prereg_data = {"nombre_visitante": "RLS resident visitor", "tipo_visita": "proveedor",
                          "fecha_visita": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                          "placa": "TEST-123", "notas": "RLS metadata"}
            prereg = client.post("/preregistro/crear", headers=resident_headers, json=prereg_data)
            assert prereg.status_code == 200, prereg.text
            prereg_id = prereg.json()["visita_id"]
            assert prereg.json()["qr_base64"]
            expiry = datetime.fromisoformat(prereg.json()["qr_vigencia"])
            scheduled = datetime.fromisoformat(prereg_data["fecha_visita"])
            assert expiry == scheduled + timedelta(minutes=60)
            assert datetime.fromisoformat(prereg.json()["qr_inicio"]) == scheduled - timedelta(minutes=30)
            replay = client.get(f"/preregistro/qr/{prereg_id}", headers=resident_headers)
            assert replay.status_code == 200, replay.text
            assert replay.json()["qr_base64"] == prereg.json()["qr_base64"]
            with Session(scoped) as db:
                _set_postgres_tenant(db, "a1")
                saved = db.query(Visita).filter_by(visita_id=prereg_id).one()
                assert saved.casa_unidad == "101"
                assert saved.qr_token and saved.qr_vigencia
                assert db.query(Evidencia).filter_by(visita_id=prereg_id).one().metadata_json["placa"] == "TEST-123"
            assert client.get(f"/visitas/{prereg_id}?condominio_id=b1", headers=headers["b"]).status_code == 404
            clock = client.get("/preregistro/reloj", headers=resident_headers)
            assert datetime.fromisoformat(clock.json()["utc"]).utcoffset() == timedelta(0)
            immediate = client.post("/preregistro/crear", headers=resident_headers,
                                    json={"nombre_visitante": "Immediate UTC", "tipo_visita": "visita_personal"})
            assert immediate.status_code == 200, immediate.text
            immediate_id = immediate.json()["visita_id"]
            early_data = {**prereg_data, "fecha_visita": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
            future = client.post("/preregistro/crear", headers=resident_headers, json=early_data)
            assert future.status_code == 200, future.text
            future_id = future.json()["visita_id"]
            with Session(scoped) as db:
                _set_postgres_tenant(db, "a1")
                token = db.query(Visita).filter_by(visita_id=prereg_id).one().qr_token
                immediate_token = db.query(Visita).filter_by(visita_id=immediate_id).one().qr_token
                future_token = db.query(Visita).filter_by(visita_id=future_id).one().qr_token
            def scan(visit_id, qr_token):
                return client.get(f"/qr/validar/{visit_id}/{qr_token}?condominio_id=a1", headers=headers["a"])
            early = scan(future_id, future_token)
            assert early.status_code == 400 and "aún no vigente" in early.text
            assert client.patch(f"/visitas/{prereg_id}/cancelar", headers=resident_headers).status_code == 200
            cancelled = scan(prereg_id, token)
            assert cancelled.status_code == 400 and "cancelada" in cancelled.text
            assert client.get(f"/preregistro/qr/{prereg_id}", headers=resident_headers).status_code == 400
            assert scan(immediate_id, immediate_token).status_code == 200
            assert scan(immediate_id, immediate_token).status_code == 400
            with Session(scoped) as db:
                _set_postgres_tenant(db, "a1")
                expired = db.query(Visita).filter_by(visita_id=future_id).one()
                expired.qr_vigencia = datetime.utcnow() - timedelta(seconds=1)
                db.commit()
            expired_scan = scan(future_id, future_token)
            assert expired_scan.status_code == 400 and "expirado" in expired_scan.text
            with Session(scoped) as db:
                _set_postgres_tenant(db, "a1")
                assert db.query(Visita).filter_by(visita_id=prereg_id).one().estado == "cancelada"
                assert db.query(Visita).filter_by(visita_id=future_id).one().estado == "pendiente"
                assert db.query(Visita).filter_by(visita_id=immediate_id).one().estado == "entrada_registrada"
            with Session(scoped) as db:
                scope = db.query(UserTenantScope).filter_by(usuario_id="resident_a").one()
                scope.estado = ScopeStatus.REVOCADO
                db.commit()
            assert client.post("/preregistro/crear", headers=resident_headers, json=prereg_data).status_code == 403
            assert client.get("/visitas/v_a?condominio_id=a1").status_code == 401
            assert client.get("/visitas/v_a", headers=headers["a"]).status_code == 400
            own = client.get("/visitas/v_a?condominio_id=a1", headers=headers["a"])
            assert own.status_code == 200, own.text
            assert own.json()["visita_id"] == "v_a"
            assert datetime.fromisoformat(own.json()["created_at"]).utcoffset() == timedelta(0)
            assert own.json()["entrada_registrada_en"] is None
            assert own.json()["salida_registrada_en"] is None
            listing = client.get("/visitas/condominio/a1", headers=headers["a"])
            assert listing.status_code == 200, listing.text
            assert {v["visita_id"] for v in listing.json()} == {"v_a", prereg_id, immediate_id, future_id}
            assert client.get("/visitas/condominio/b1", headers=headers["a"]).status_code == 403
            data = {"condominio_id": "a1", "casa_unidad": "101", "nombre_visitante": "Nuevo",
                    "tipo_visita": "eventual", "vigencia": (datetime.utcnow() + timedelta(days=1)).isoformat()}
            assert client.patch("/visitas/v_a/salida?condominio_id=a1", headers=headers["a"]).status_code == 400
            guard_headers = {"Authorization": f"Bearer {create_access_token('guard_a', 'GUARDIA')}"}
            manual = client.post("/visitas/entrada/a1", headers=guard_headers, json=data)
            assert manual.status_code == 200, manual.text
            manual_id = manual.json()["visita_id"]
            manual_time = manual.json()["entrada_registrada_en"]
            assert manual.json()["estado"] == "entrada_registrada"
            assert datetime.fromisoformat(manual_time).utcoffset() == timedelta(0)
            assert client.get(f"/visitas/{manual_id}?condominio_id=a1", headers=guard_headers).json()["entrada_registrada_en"] == manual_time
            assert client.patch(f"/visitas/{manual_id}/entrada?condominio_id=a1", headers=guard_headers).status_code == 400
            assert client.post("/visitas/entrada/b1", headers=guard_headers, json={**data, "condominio_id": "b1"}).status_code == 403
            assert client.post("/visitas/entrada/a1", headers=guard_headers, json={**data, "condominio_id": "b1"}).status_code == 400
            assert client.post("/visitas/entrada/a1", headers=resident_headers, json=data).status_code == 403
            assert client.patch(f"/visitas/{future_id}/entrada?condominio_id=a1", headers=guard_headers).status_code == 400
            assert client.patch(f"/visitas/{manual_id}/salida?condominio_id=a1", headers=guard_headers).status_code == 200
            assert client.patch(f"/visitas/{manual_id}/salida?condominio_id=a1", headers=guard_headers).status_code == 400
            created = client.post("/visitas/a1", headers=headers["a"], json=data)
            assert created.status_code == 200, created.text
            assert created.json()["condominio_id"] == "a1"
            assert client.post("/visitas/b1", headers=headers["a"], json={**data, "condominio_id": "b1"}).status_code == 403
            assert client.post("/visitas/a1", headers=headers["a"], json={**data, "condominio_id": "b1"}).status_code == 400
            legacy = client.post("/visitas/", headers=headers["a"], json=data)
            assert legacy.status_code == 200, legacy.text
            assert legacy.json()["condominio_id"] == "a1"
            assert client.post("/visitas/", headers=headers["a"], json={**data, "condominio_id": "b1"}).status_code == 403
            assert client.get("/visitas/v_b?condominio_id=b1", headers=headers["a"]).status_code == 403
            assert client.get("/visitas/v_b?condominio_id=a1", headers=headers["a"]).status_code == 404
            assert client.patch("/visitas/v_b/salida?condominio_id=b1", headers=headers["a"]).status_code == 403
            assert client.patch("/visitas/v_b/entrada?condominio_id=b1", headers=guard_headers).status_code == 403
            assert client.patch("/visitas/v_a/entrada?condominio_id=a1", headers=resident_headers).status_code == 403
            entered = client.patch("/visitas/v_a/entrada?condominio_id=a1", headers=guard_headers)
            assert entered.status_code == 200, entered.text
            assert entered.json()["entrada_registrada_en"]
            changed = client.patch("/visitas/v_a/salida?condominio_id=a1", headers=headers["a"])
            assert changed.status_code == 200, changed.text
            assert changed.json()["estado"] == "salida_registrada"
            reloaded = client.get("/visitas/v_a?condominio_id=a1", headers=headers["a"]).json()
            assert reloaded["estado"] == "salida_registrada"
            persisted_exit = datetime.fromisoformat(reloaded["salida_registrada_en"])
            assert persisted_exit.utcoffset() == timedelta(0)
            with Session(scoped) as db:
                _set_postgres_tenant(db, "a1")
                saved_exit = db.query(Visita).filter_by(visita_id="v_a").one().salida_registrada_en
                assert persisted_exit == saved_exit.replace(tzinfo=timezone.utc)
            other = client.get("/visitas/v_b?condominio_id=b1", headers=headers["b"])
            assert other.status_code == 200, other.text
            assert other.json()["estado"] == "pendiente"
            assert client.get("/visitas/v_a?condominio_id=a1", headers=headers["b"]).status_code == 403
            with Session(scoped) as db:
                membership = db.query(MSPMembership).filter_by(usuario_id="admin_a").one()
                membership.estado = "revocado"
                db.commit()
            assert client.get("/visitas/v_a?condominio_id=a1", headers=headers["a"]).status_code == 403
        with Session(scoped) as db:
            assert db.query(Visita).count() == 0  # conexiones recicladas sin contexto
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()


def test_qr_window_normalizes_offsets_to_utc():
    from backend.services import qr_service
    scheduled = datetime.fromisoformat("2026-10-01T12:00:00-06:00")
    start, end = qr_service.ventana_visita(scheduled)
    assert start == datetime(2026, 10, 1, 17, 30, tzinfo=timezone.utc)
    assert end == datetime(2026, 10, 1, 19, 0, tzinfo=timezone.utc)
    assert qr_service.as_utc(datetime(2026, 10, 1, 18)) == scheduled
    generated = qr_service.generar_qr_para_visita("test", fecha_visita=scheduled)
    assert qr_service.as_utc(generated["qr_vigencia"]) == end


@pytest.mark.integration
@pytest.mark.parametrize("race", ["qr", "manual", "salida", "cancelar", "regenerar"])
def test_transiciones_concurrentes_con_rls(race):
    """Dos sesiones leen pendiente: sólo un UPDATE puede consumir ese estado."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException

    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere AXS_TEST_POSTGRES_URL de PostgreSQL desechable")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    with engine.connect() as connection:
        assert not connection.execute(text(
            "SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname = current_user"
        )).scalar_one()
    schema = f"axs_race_{uuid.uuid4().hex[:12]}"
    scoped = engine.execution_options(schema_translate_map={None: schema})
    barrier = Barrier(2)
    original_entry = datetime.utcnow() if race == "salida" else None
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(scoped, tables=[
            MSP.__table__, Condominio.__table__, Casa.__table__, Visita.__table__,
        ])
        with Session(scoped) as db:
            db.add(MSP(msp_id="a", nombre="A"))
            db.flush()
            db.add_all([Condominio(condominio_id=c, msp_id="a", nombre=c) for c in ("a1", "a2")])
            db.flush()
            db.add(Visita(visita_id="race", condominio_id="a1", nombre_visitante="Concurrente",
                         estado="entrada_registrada" if race == "salida" else "pendiente",
                         entrada_registrada_en=original_entry,
                         qr_token=None if race in ("manual", "salida") else "valid",
                         qr_vigencia=datetime.utcnow() + timedelta(minutes=30),
                         vigencia=datetime.utcnow()))
            db.commit()
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {schema}.visitas ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {schema}.visitas FORCE ROW LEVEL SECURITY"))
            connection.execute(text(
                f"CREATE POLICY tenant_visitas ON {schema}.visitas "
                "USING (condominio_id = current_setting('app.tenant_id', true)) "
                "WITH CHECK (condominio_id = current_setting('app.tenant_id', true))"
            ))

        def worker(index):
            with Session(scoped) as db:
                _set_postgres_tenant(db, "a1")
                stale = db.query(Visita).filter_by(visita_id="race").one()
                expected = stale.estado
                barrier.wait(timeout=15)  # ambas solicitudes ya leyeron el mismo estado
                try:
                    if race == "salida":
                        saved = visita_service.registrar_salida(db, "race")
                    elif race == "cancelar" and index == 1:
                        saved = visita_service.cancelar_visita(db, "race", estado_esperado=expected)
                    elif race == "regenerar" and index == 1:
                        saved = visita_service.actualizar_qr(db, "race", "replacement",
                                                           datetime.utcnow() + timedelta(minutes=30))
                    else:
                        saved = visita_service.registrar_entrada(db, "race",
                            qr_token=None if race == "manual" else "valid")
                    return ("ok", saved.estado, saved.entrada_registrada_en, saved.salida_registrada_en)
                except HTTPException as exc:
                    assert exc.status_code == 400
                    return ("denied",)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [0, 1]))
        winners = [r for r in results if r[0] == "ok"]
        assert len(winners) == 1, results
        with Session(scoped) as db:
            _set_postgres_tenant(db, "a1")
            saved = db.query(Visita).filter_by(visita_id="race").one()
            assert (saved.estado, saved.entrada_registrada_en, saved.salida_registrada_en) == winners[0][1:]
            if race == "salida":
                assert saved.entrada_registrada_en == original_entry
            if saved.estado == "pendiente":
                assert saved.qr_token == "replacement" and saved.entrada_registrada_en is None
        # El servicio tampoco permite mutaciones desde otro tenant, aun con ID conocido.
        with Session(scoped) as other:
            _set_postgres_tenant(other, "a2")
            with pytest.raises(HTTPException):
                visita_service.registrar_entrada(other, "race", qr_token="valid")
        with Session(scoped) as no_context:
            assert no_context.query(Visita).count() == 0
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
