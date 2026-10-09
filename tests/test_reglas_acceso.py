"""Reglas optativas, autorización local y bloqueo de todas las rutas de entrada."""
from datetime import datetime, timedelta
import pytest
from backend.db.core import (MSP, Condominio, Usuario, Casa, UserTenantScope,
    AccessLevel, ScopeStatus, Visita, EventOutbox)
from backend.db.gov import Policy, PolicyScope, GovStatus
from backend.core.auth.jwt import create_access_token
import os
import uuid


@pytest.fixture
def db_engine(db_engine):
    """Optional PostgreSQL run uses only a uniquely named disposable schema."""
    url = os.environ.get("AXS_RULES_TEST_POSTGRES_URL")
    if not url:
        yield db_engine
        return
    from sqlalchemy import create_engine, text
    from backend.db.core import Base_CORE
    schema = "axs_rules_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base_CORE.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def headers(user, role):
    return {"Authorization": f"Bearer {create_access_token(user, role)}"}


@pytest.fixture
def setup(db_session, db_gov_session):
    db_session.add(MSP(msp_id="m", nombre="m"))
    db_session.flush()
    db_session.add_all([Condominio(condominio_id=t, msp_id="m", nombre=t) for t in ["a", "b"]])
    db_session.flush()
    db_session.add_all([Casa(casa_id="home", condominio_id="a", numero="101", tipo="casa"),
                        Casa(casa_id="other", condominio_id="a", numero="102", tipo="casa")])
    db_session.flush()
    for user, role, level in [("admin", "ADMIN_CONDOMINIO", AccessLevel.ADMIN_CONDOMINIO),
                             ("guard", "GUARDIA", AccessLevel.GUARDIA),
                             ("resident", "RESIDENTE", AccessLevel.RESIDENTE)]:
        db_session.add(Usuario(usuario_id=user, email=f"{user}@test.local", rol=role,
            condominio_id="a", casa_id="home" if user == "resident" else None,
            casa_unidad="101" if user == "resident" else None))
        db_session.flush()
        db_session.add(UserTenantScope(usuario_id=user, tenant_id="a", access_level=level,
                                       estado=ScopeStatus.ACTIVO))
    db_session.commit()
    for action in ["crear_visita", "generar_qr"]:
        db_gov_session.add(Policy(policy_id=action, nombre=action, ambito=PolicyScope.GLOBAL,
            accion_objetivo=action, limites={}, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    return db_session


def rules(client, **changes):
    payload = {"exigir_proposito": False, "exigir_autorizacion": False,
               "tipos_visita": ["eventual", "frecuente", "visita_personal", "proveedor", "entrega"], **changes}
    result = client.put("/condominios/a/reglas-acceso", json=payload, headers=headers("admin", "ADMIN_CONDOMINIO"))
    assert result.status_code == 200, result.text
    return payload


def body(**changes):
    return {"condominio_id": "a", "nombre_visitante": "Test", "tipo_visita": "proveedor",
            "vigencia": datetime.utcnow().isoformat(), "destino_id": "home", **changes}


def pending(db, **changes):
    data = {"visita_id": "old", "condominio_id": "a", "nombre_visitante": "Old",
            "tipo_visita": "proveedor", "vigencia": datetime.utcnow(), "estado": "pendiente",
            "destino_id": "home", "destino_tipo": "vivienda", "casa_unidad": "101", **changes}
    visita = Visita(**data)
    db.add(visita); db.commit()
    return visita


def test_defaults_and_local_configuration(client, setup):
    h = headers("guard", "GUARDIA")
    assert client.get("/condominios/a/reglas-acceso", headers=h).json()["exigir_autorizacion"] is False
    config = rules(client, exigir_proposito=True)
    for user, role in [("guard", "GUARDIA"), ("resident", "RESIDENTE")]:
        assert client.put("/condominios/a/reglas-acceso", json=config, headers=headers(user, role)).status_code == 403
    assert client.put("/condominios/b/reglas-acceso", json=config, headers=headers("admin", "ADMIN_CONDOMINIO")).status_code == 403
    assert setup.query(Condominio).filter_by(condominio_id="b").one().reglas_acceso is None
    audit = setup.query(EventOutbox).filter_by(condominio_id="a").first().payload
    assert audit["identity_id"] == "admin" and audit["metadata_json"]["despues"]["exigir_proposito"] is True
    assert client.put("/condominios/a/reglas-acceso", json={**config, "tipos_visita": []}, headers=headers("admin", "ADMIN_CONDOMINIO")).status_code == 422


def test_purpose_alone_does_not_wait_for_resident(client, setup):
    rules(client, exigir_proposito=True)
    h = headers("guard", "GUARDIA")
    for purpose in [None, "   "]:
        rejected = client.post("/visitas/entrada/a", json=body(proposito=purpose), headers=h)
        assert rejected.status_code == 403
    assert setup.query(Visita).count() == 0
    accepted = client.post("/visitas/entrada/a", json=body(proposito=" Reparación "), headers=h)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["proposito"] == "Reparación" and accepted.json()["autorizada_por"] is None
    assert accepted.json()["estado"] == "entrada_registrada"


def test_no_immediate_or_forged_authorization_or_other_destination(client, setup):
    rules(client, exigir_autorizacion=True)
    h = headers("guard", "GUARDIA")
    for payload in [body(), body(autorizada_por="admin", autorizada_en=datetime.utcnow().isoformat()),
                    body(destino_id="OTRO", destino_motivo="Entrada en otro lugar")]:
        result = client.post("/visitas/entrada/a", json=payload, headers=h)
        assert result.status_code == 403, result.text
    assert setup.query(Visita).count() == 0
    # Un rechazo no mantiene ninguna solicitud esperando ni impide atender otra.
    rules(client)
    assert client.post("/visitas/entrada/a", json=body(), headers=h).status_code == 200


def test_manual_entry_requires_approval_and_guard_cannot_approve(client, setup):
    pending(setup)
    rules(client, exigir_autorizacion=True, exigir_proposito=True)
    h = headers("guard", "GUARDIA")
    assert client.patch("/visitas/old/entrada", headers=h).status_code == 403
    assert client.patch("/visitas/old/autorizar", json={"proposito": "Servicio"}, headers=h).status_code == 403
    approved = client.patch("/visitas/old/autorizar", json={"proposito": "Servicio"}, headers=headers("resident", "RESIDENTE"))
    assert approved.status_code == 200, approved.text
    assert approved.json()["autorizada_por"] == "resident"
    entered = client.patch("/visitas/old/entrada", headers=h)
    assert entered.status_code == 200, entered.text
    assert client.patch("/visitas/old/entrada", headers=h).status_code == 400
    assert client.patch("/visitas/old/salida", headers=h).status_code == 200


def test_approval_scoped_to_home_and_tenant(client, setup):
    pending(setup, destino_id="other", casa_unidad="102")
    assert client.patch("/visitas/old/autorizar", json={}, headers=headers("resident", "RESIDENTE")).status_code == 403
    assert client.patch("/visitas/old/autorizar?condominio_id=b", json={}, headers=headers("admin", "ADMIN_CONDOMINIO")).status_code == 403
    assert setup.query(Visita).one().autorizada_por is None
    approved = client.patch("/visitas/old/autorizar", json={}, headers=headers("admin", "ADMIN_CONDOMINIO"))
    assert approved.status_code == 200, approved.text


def test_old_qr_rechecked_against_current_rules(client, setup):
    from backend.services.qr_service import generar_qr_para_visita
    now = datetime.utcnow()
    qr = generar_qr_para_visita("old", fecha_visita=now)
    pending(setup, vigencia=now, qr_token=qr["token"], qr_vigencia=qr["qr_vigencia"])
    rules(client, exigir_autorizacion=True)
    h = headers("guard", "GUARDIA")
    url = f'/qr/validar/old/{qr["token"]}'
    assert client.get(url, headers=h).status_code == 403
    assert client.patch("/visitas/old/entrada", headers=h).status_code == 400
    assert client.patch("/visitas/old/autorizar", json={}, headers=headers("admin", "ADMIN_CONDOMINIO")).status_code == 200
    assert client.get(url, headers=h).status_code == 200


def test_resident_preregistro_is_prior_authorization(client, setup):
    rules(client, exigir_autorizacion=True, exigir_proposito=True)
    h = headers("resident", "RESIDENTE")
    payload = {"nombre_visitante": "Tech", "tipo_visita": "proveedor"}
    assert client.post("/preregistro/crear", json=payload, headers=h).status_code == 403
    result = client.post("/preregistro/crear", json={**payload, "proposito": "Mantenimiento"}, headers=h)
    assert result.status_code == 200, result.text
    visit = setup.query(Visita).filter_by(visita_id=result.json()["visita_id"]).one()
    assert visit.autorizada_por == "resident" and visit.autorizada_en
    url = f'/qr/validar/{visit.visita_id}/{visit.qr_token}'
    assert client.get(url, headers=headers("guard", "GUARDIA")).status_code == 200


def test_subset_and_unknown_type(client, setup):
    rules(client, exigir_autorizacion=True, tipos_visita=["proveedor"])
    h = headers("guard", "GUARDIA")
    assert client.post("/visitas/entrada/a", json=body(tipo_visita="eventual"), headers=h).status_code == 200
    assert client.post("/visitas/entrada/a", json=body(tipo_visita="inventado"), headers=h).status_code == 400
    assert client.post("/visitas/entrada/a", json=body(), headers=h).status_code == 403


def test_expired_manual_authorization_denied(client, setup):
    pending(setup, autorizada_por="resident", autorizada_en=datetime.utcnow()-timedelta(days=1),
            vigencia=datetime.utcnow()-timedelta(hours=2))
    rules(client, exigir_autorizacion=True)
    result = client.patch("/visitas/old/entrada", headers=headers("guard", "GUARDIA"))
    assert result.status_code == 403 and "horario" in result.json()["detail"]


def test_admin_creation_authorizes_only_pending_visit(client, setup):
    rules(client, exigir_autorizacion=True)
    h = headers("admin", "ADMIN_CONDOMINIO")
    result = client.post("/visitas/a", json=body(), headers=h)
    assert result.status_code == 200, result.text
    assert result.json()["autorizada_por"] == "admin"
    assert client.patch(f'/visitas/{result.json()["visita_id"]}/entrada', headers=headers("guard", "GUARDIA")).status_code == 200
    assert client.post("/visitas/a?entrada_inmediata=true", json=body(), headers=h).status_code == 403


def test_rule_change_and_entry_serialized_in_postgres(setup):
    if setup.get_bind().dialect.name != "postgresql":
        pytest.skip("Requiere PostgreSQL para comprobar bloqueos concurrentes")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy.orm import Session
    from fastapi import HTTPException
    from backend.services.reglas_acceso import obtener_reglas
    from backend.services.visita_service import registrar_entrada
    pending(setup)
    started = Event()
    def attempt():
        with Session(setup.get_bind()) as other:
            started.set()
            try:
                registrar_entrada(other, "old")
            except HTTPException as exc:
                return exc.status_code
            return 200
    with Session(setup.get_bind()) as admin:
        condo, _ = obtener_reglas(admin, "a", bloquear=True)
        condo.reglas_acceso = {"exigir_autorizacion": True}
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(attempt)
            assert started.wait(timeout=5)
            admin.commit()
            assert future.result(timeout=10) == 403
    setup.expire_all()
    assert setup.query(Visita).one().entrada_registrada_en is None


def test_dos_guardias_mismo_qr_postgres(setup):
    """Dos sesiones independientes compiten por el mismo QR: sólo una gana."""
    if setup.get_bind().dialect.name != 'postgresql':
        pytest.skip('Requiere PostgreSQL para competencia real entre sesiones')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    from types import SimpleNamespace
    from fastapi import HTTPException
    from backend.services.visita_service import registrar_entrada
    from backend.services.event_outbox import contexto_evento, rechazar_operacion
    now = datetime.utcnow()
    pending(setup, qr_token='same-qr', qr_vigencia=now+timedelta(minutes=60), vigencia=now)
    barrier = Barrier(2)
    def scan(actor):
        with Session(setup.get_bind()) as db:
            user = SimpleNamespace(usuario_id=actor)
            barrier.wait(timeout=10)
            try:
                registrar_entrada(db, 'old', qr_token='same-qr',
                    auditoria=contexto_evento(user, 'test-session', entidad='qr', accion='validar'))
                return 200
            except HTTPException as exc:
                # Misma conservación de rechazo que la ruta HTTP tras scope.
                try:
                    rechazar_operacion(db, user, 'test-session', 'a', 'old',
                        detail=exc.detail, entidad='qr', accion='validar', status_code=exc.status_code)
                except HTTPException as denied:
                    return denied.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(scan, ['guard-1','guard-2']))
    assert sorted(results) == [200,400]
    setup.expire_all()
    assert setup.query(Visita).one().entrada_registrada_en is not None
    events = setup.query(EventOutbox).all()
    assert sorted(e.payload['resultado'] for e in events) == ['denegado','exito']
    assert {e.payload['identity_id'] for e in events} == {'guard-1','guard-2'}
