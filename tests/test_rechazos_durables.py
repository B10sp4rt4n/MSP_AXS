"""Rechazo HTTP persistente, sin autorización implícita ni secretos."""
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from backend.core.auth.jwt import create_access_token
from backend.db.core import EventOutbox, Visita, Usuario, UserTenantScope, AccessLevel, ScopeStatus
from backend.db.event import Event
from backend.services import event_outbox


@pytest.fixture
def access(db_session, condominio_base):
    condo = condominio_base.condominio_id
    users = {}
    for identity, role in [("guard", "GUARDIA"), ("admin", "ADMIN_CONDOMINIO")]:
        user = Usuario(usuario_id=identity, email=f"{identity}@test.local", rol=role, condominio_id=condo)
        db_session.add(user)
        db_session.flush()
        db_session.add(UserTenantScope(usuario_id=identity, tenant_id=condo,
            access_level=AccessLevel[role], estado=ScopeStatus.ACTIVO))
        users[identity] = user
    row = Visita(visita_id="reject", condominio_id=condo, nombre_visitante="Test",
                 estado="pendiente", qr_token="secret-qr", qr_vigencia=datetime.utcnow() + timedelta(hours=1),
                 vigencia=datetime.utcnow())
    db_session.add(row)
    db_session.commit()
    return row, users


def headers(user):
    return {"Authorization": "Bearer " + create_access_token(user.usuario_id, user.rol)}


@pytest.mark.parametrize("condition", ["cancelled", "final", "invalid", "expired", "used", "early", "missing"])
def test_qr_denegado_sin_event_disponible(client, db_session, access, monkeypatch, condition):
    from backend.core.event import registry
    row, users = access
    token, visit_id = row.qr_token, row.visita_id
    if condition == "cancelled": row.estado = "cancelada"
    if condition == "final": row.estado = "finalizada"
    if condition == "invalid": token = "other-secret-qr"
    if condition == "expired": row.qr_vigencia = datetime.utcnow() - timedelta(seconds=1)
    if condition == "used":
        row.estado = "entrada_registrada"
        row.entrada_registrada_en = datetime.utcnow()
    if condition == "early": row.vigencia = datetime.utcnow() + timedelta(hours=2)
    if condition == "missing": visit_id = "nonexistent"
    db_session.commit()
    state, entry = row.estado, row.entrada_registrada_en
    def event_down(*args, **kwargs):
        raise ConnectionError("EVENT unavailable")
    monkeypatch.setattr(registry, "registrar_evento", event_down)
    response = client.get(f"/qr/validar/{visit_id}/{token}", headers=headers(users["guard"]))
    assert response.status_code == (404 if condition == "missing" else 400), response.text
    event = db_session.query(EventOutbox).one()
    assert event.condominio_id == row.condominio_id
    assert event.payload["entidad_id"] == visit_id
    assert event.payload["resultado"] in ("denegado", "fallo")
    assert event.delivered_at is None
    assert token not in str(event.payload)
    assert "secret-qr" not in str(event.payload)
    assert "Bearer" not in str(event.payload)
    db_session.refresh(row)
    assert row.estado == state and row.entrada_registrada_en == entry


def test_condominio_inexistente_o_ajeno_no_elige_bandeja(client, db_session, access):
    from backend.db.core import Condominio
    row, users = access
    db_session.add(Condominio(condominio_id="other", msp_id=db_session.query(Condominio).first().msp_id, nombre="Other"))
    db_session.commit()
    for tenant, expected in [("unknown", 404), ("other", 403)]:
        response = client.get(f"/qr/validar/nonexistent/secret?condominio_id={tenant}", headers=headers(users["guard"]))
        assert response.status_code == expected
    assert db_session.query(EventOutbox).count() == 0
    assert client.get("/qr/validar/nonexistent/secret", headers=headers(users["guard"])).status_code == 404
    assert db_session.query(EventOutbox).one().condominio_id == row.condominio_id


@pytest.mark.parametrize("route", ["entrada", "salida", "cancelar"])
def test_rechazo_manual_no_modifica_visita(client, db_session, access, route):
    row, users = access
    if route == "cancelar": row.estado = "cancelada"
    db_session.commit()
    response = client.patch(f"/visitas/{row.visita_id}/{route}", headers=headers(users["admin"]))
    assert response.status_code == 400
    assert db_session.query(EventOutbox).one().payload["resultado"] == "denegado"
    db_session.refresh(row)
    assert row.entrada_registrada_en is None and row.salida_registrada_en is None
    assert row.estado == ("cancelada" if route == "cancelar" else "pendiente")


def test_rechazo_revierte_negocio_no_confirmado(db_session, access):
    row, users = access
    tenant, visit_id = row.condominio_id, row.visita_id
    row.estado = "entrada_registrada"
    row.entrada_registrada_en = datetime.utcnow()
    db_session.flush()
    with pytest.raises(HTTPException) as exc:
        event_outbox.rechazar_operacion(db_session, users["guard"], "private-token", tenant, visit_id, detail="Denegado")
    assert exc.value.status_code == 400
    db_session.refresh(row)
    assert row.estado == "pendiente" and row.entrada_registrada_en is None
    assert db_session.query(EventOutbox).count() == 1


def test_core_caido_sigue_rechazando_sin_fingir_auditoria(client, db_session, access, monkeypatch):
    row, users = access
    row.estado = "cancelada"
    db_session.commit()
    def fail(*args, **kwargs): raise ConnectionError("private database detail")
    monkeypatch.setattr(event_outbox, "encolar_evento", fail)
    response = client.get("/qr/validar/reject/secret-qr", headers=headers(users["guard"]))
    assert response.status_code == 503
    assert "private database detail" not in response.text
    assert db_session.query(EventOutbox).count() == 0
    db_session.refresh(row)
    assert row.estado == "cancelada" and row.entrada_registrada_en is None


def test_carrera_rechazada_tambien_se_conserva(client, db_session, access, monkeypatch):
    import backend.routers.qr_router as router
    row, users = access
    def conflict(*args, **kwargs): raise HTTPException(400, "QR ya utilizado o sin autorización vigente")
    monkeypatch.setattr(router.visita_service, "registrar_entrada", conflict)
    assert client.get("/qr/validar/reject/secret-qr", headers=headers(users["guard"])).status_code == 400
    assert db_session.query(EventOutbox).one().payload["resultado"] == "denegado"
    assert row.entrada_registrada_en is None


def test_reintento_de_envio_no_duplica_intentos_rechazados(client, db_session, db_event_engine, access):
    row, users = access
    row.estado = "cancelada"
    db_session.commit()
    auth = headers(users["guard"])
    for _ in range(2):
        assert client.get("/qr/validar/reject/secret-qr", headers=auth).status_code == 400
    assert db_session.query(EventOutbox).count() == 2  # dos solicitudes distintas
    factory = sessionmaker(bind=db_event_engine)
    now = datetime.utcnow() + timedelta(minutes=1)
    def ack_lost(db, payload):
        event_outbox.publicar_evento(db, payload)
        raise ConnectionError("ACK lost")
    assert event_outbox.enviar_pendientes(db_session, row.condominio_id, factory, now=now, publisher=ack_lost) == 0
    assert event_outbox.enviar_pendientes(db_session, row.condominio_id, factory, now=now + timedelta(minutes=5)) == 2
    with factory() as db:
        events = db.query(Event).all()
        assert len(events) == 2 and all(e.resultado == "denegado" for e in events)


@pytest.mark.parametrize("cause", ["policy", "cancelled", "window", "race"])
def test_generacion_denegada_conserva_motivo_seguro(client, db_session, access, monkeypatch, cause):
    import backend.routers.qr_router as router
    row, users = access
    monkeypatch.setattr(router, "puede_ejecutar_accion", lambda **kw: (cause != "policy", "private connection error"))
    if cause == "cancelled": row.estado = "cancelada"
    if cause == "window": row.vigencia = datetime.utcnow() - timedelta(hours=2)
    if cause == "race":
        def conflict(*args, **kwargs): raise HTTPException(400, "La visita cambió de estado")
        monkeypatch.setattr(router.visita_service, "actualizar_qr", conflict)
    db_session.commit()
    response = client.post("/qr/generar/reject", headers=headers(users["admin"]))
    assert response.status_code == (403 if cause == "policy" else 400)
    event = db_session.query(EventOutbox).one()
    assert event.payload["resultado"] == "denegado" and event.payload["accion"] == "crear"
    assert "private connection error" not in str(event.payload)
    db_session.refresh(row)
    assert row.qr_token == "secret-qr" and row.entrada_registrada_en is None
