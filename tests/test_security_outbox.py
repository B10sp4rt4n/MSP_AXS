"""Sin sesión/alcance: registro global independiente, saneado y recuperable."""
import logging
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from backend.core.auth.jwt import create_access_token
from backend.db.core import SecurityOutbox, EventOutbox, Condominio, Usuario
from backend.db.event import Event
from backend.services import security_outbox


@pytest.mark.parametrize("authorization", [None, "Basic password-secret", "Bearer jwt-secret"])
def test_sesion_ausente_o_invalida_se_conserva(client, db_session, authorization, caplog):
    caplog.set_level(logging.DEBUG)
    headers = {} if authorization is None else {"Authorization": authorization}
    response = client.get("/qr/validar/private-visit/private-qr?email=private-email", headers=headers)
    assert response.status_code == 401
    row = db_session.query(SecurityOutbox).one()
    assert row.payload["tenant_id"] == security_outbox.DOMAIN
    assert row.payload["identity_id"] == "NONE"
    assert row.payload["metadata_json"]["route"] == "/qr/validar/{visita_id}/{token}"
    for secret in ("private-visit", "private-qr", "private-email", "password-secret", "jwt-secret"):
        assert secret not in str(row.payload)
        assert secret not in response.text
    assert "password-secret" not in caplog.text and "jwt-secret" not in caplog.text
    assert db_session.query(EventOutbox).count() == 0


def test_ruta_desconocida_no_guarda_uri_cliente(client, db_session):
    assert client.get("/private-email/private-secret?token=private-jwt").status_code == 401
    row = db_session.query(SecurityOutbox).one()
    assert row.payload["metadata_json"]["route"] == "unknown_route"
    assert "private" not in str(row.payload)


def test_no_atribuye_identidad_a_sub_sin_usuario(client, db_session):
    token = create_access_token("unverified-person", "ADMIN_CONDOMINIO")
    response = client.get("/auth/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
    row = db_session.query(SecurityOutbox).one()
    assert row.payload["motivo"] == "UNKNOWN_IDENTITY"
    assert row.payload["identity_id"] == "NONE"
    assert "unverified-person" not in str(row.payload)


def test_falta_de_alcance_no_escribe_en_condominio_ajeno(client, db_session, usuario_base, condominio_base):
    db_session.add(Condominio(condominio_id="foreign", msp_id=condominio_base.msp_id, nombre="Foreign"))
    db_session.commit()
    token = create_access_token(usuario_base.usuario_id, usuario_base.rol)
    response = client.get("/visitas/nonexistent?condominio_id=foreign", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 403
    row = db_session.query(SecurityOutbox).one()
    assert row.payload["motivo"] == "SCOPE_DENIED"
    assert row.payload["identity_id"] == usuario_base.usuario_id
    assert row.payload["metadata_json"]["identity_verified"]
    assert "foreign" not in str(row.payload) and token not in str(row.payload)
    assert db_session.query(EventOutbox).count() == 0


def test_rol_insuficiente_se_conserva(client, db_session, usuario_base):
    usuario_base.rol = "RESIDENTE"
    db_session.commit()
    token = create_access_token(usuario_base.usuario_id, usuario_base.rol)
    assert client.patch("/visitas/nonexistent/entrada", headers={"Authorization": "Bearer " + token}).status_code == 403
    assert db_session.query(SecurityOutbox).one().payload["motivo"] == "ROLE_DENIED"


def test_publicos_preflight_y_sesion_valida_no_generan_rechazo(client, db_session, usuario_base):
    assert client.get("/health").status_code == 200
    assert client.options("/auth/me", headers={"Origin": "https://frontend-next-psi-ashen.vercel.app",
        "Access-Control-Request-Method": "GET"}).status_code == 200
    token = create_access_token(usuario_base.usuario_id, usuario_base.rol)
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 200
    assert db_session.query(SecurityOutbox).count() == 0


def test_fallo_core_no_permite_operacion_ni_finge_registro(client, db_session, monkeypatch):
    def unavailable(): raise ConnectionError("private-connection-secret")
    monkeypatch.setattr(security_outbox, "SessionFactory", unavailable)
    response = client.get("/auth/me")
    assert response.status_code == 503
    assert "private-connection-secret" not in response.text
    assert db_session.query(SecurityOutbox).count() == 0


def test_event_caido_y_ack_perdido_se_recuperan(client, db_session, db_event_engine):
    assert client.get("/auth/me").status_code == 401
    def unavailable(): raise ConnectionError("EVENT down")
    now = datetime.utcnow() + timedelta(seconds=1)
    assert security_outbox.enviar_seguridad(db_session, unavailable, now=now) == 0
    row = db_session.query(SecurityOutbox).one()
    assert row.last_error == "ConnectionError" and row.delivered_at is None
    factory = sessionmaker(bind=db_event_engine)
    def ack_lost(db, payload):
        from backend.services.event_outbox import publicar_evento
        publicar_evento(db, payload)
        raise ConnectionError("ACK lost")
    now += timedelta(minutes=5)
    assert security_outbox.enviar_seguridad(db_session, factory, now=now, publisher=ack_lost) == 0
    assert security_outbox.enviar_seguridad(db_session, factory, now=now + timedelta(minutes=5)) == 1
    with factory() as db:
        from backend.core.event.registry import verificar_integridad_evento
        event = db.query(Event).one()
        assert event.tenant_id == security_outbox.DOMAIN
        assert verificar_integridad_evento(event)


def test_payload_ajeno_no_se_envia(client, db_session, db_event_engine):
    client.get("/auth/me")
    row = db_session.query(SecurityOutbox).one()
    row.payload = {**row.payload, "tenant_id": "foreign"}
    db_session.commit()
    factory = sessionmaker(bind=db_event_engine)
    assert security_outbox.enviar_seguridad(db_session, factory, now=datetime.utcnow() + timedelta(seconds=1)) == 0
    assert row.last_error == "ValueError" and row.delivered_at is None
    with factory() as db:
        assert db.query(Event).count() == 0
