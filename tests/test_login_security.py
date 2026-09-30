"""Login local: rechazos anónimos, durables y sin credenciales."""
import logging
from datetime import datetime, timedelta
import pytest
from sqlalchemy.orm import sessionmaker
from backend.db.core import SecurityOutbox
from backend.db.event import Event
from backend.services import security_outbox

@pytest.mark.parametrize("email", ["test@example.com", "absent@example.com"])
def test_login_rechazado_sin_secretos(client, usuario_base, db_session, db_event_session, email, caplog):
    caplog.set_level(logging.DEBUG, logger="axs.auth")
    response = client.post("/auth/login", json={"email": email, "password": "private-password"},
                           headers={"Authorization": "Bearer private-token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Email o contraseña incorrectos"}
    assert response.headers["www-authenticate"] == "Bearer"
    payload = db_session.query(SecurityOutbox).one().payload
    assert payload["motivo"] == "INVALID_CREDENTIALS"
    assert payload["identity_id"] == "NONE"
    assert payload["metadata_json"] == {"route": "/auth/login", "method": "POST",
        "reason": "INVALID_CREDENTIALS", "identity_verified": False}
    for secret in (email, "private-password", "private-token", usuario_base.usuario_id):
        assert secret not in str(payload)
        assert secret not in caplog.text
        assert secret not in response.text
    assert db_event_session.query(Event).count() == 0

def test_login_audit_core_caido_no_da_token(client, usuario_base, monkeypatch, db_session, caplog):
    def unavailable(): raise ConnectionError("private-db-secret")
    monkeypatch.setattr(security_outbox, "SessionFactory", unavailable)
    response = client.post("/auth/login", json={"email": usuario_base.email, "password": "wrong"})
    assert response.status_code == 503
    assert "access_token" not in response.json()
    assert "private-db-secret" not in response.text + caplog.text
    assert db_session.query(SecurityOutbox).count() == 0

def test_login_rechazado_event_caido_reintentos_sin_duplicado(client, db_session, db_event_engine):
    for _ in range(2):
        assert client.post("/auth/login", json={"email": "absent@example.com", "password": "wrong"}).status_code == 401
    assert db_session.query(SecurityOutbox).count() == 2
    def unavailable(): raise ConnectionError("EVENT down")
    now = datetime.utcnow() + timedelta(seconds=1)
    assert security_outbox.enviar_seguridad(db_session, unavailable, now=now) == 0
    factory = sessionmaker(bind=db_event_engine)
    def ack_lost(db, payload):
        from backend.services.event_outbox import publicar_evento
        publicar_evento(db, payload)
        raise ConnectionError("ACK lost")
    assert security_outbox.enviar_seguridad(db_session, factory, now=now + timedelta(minutes=5), publisher=ack_lost) == 0
    assert security_outbox.enviar_seguridad(db_session, factory, now=now + timedelta(minutes=10)) == 2
    with factory() as db:
        from backend.core.event.registry import verificar_integridad_evento
        events = db.query(Event).all()
        assert len(events) == 2
        assert all(e.motivo == "INVALID_CREDENTIALS" and verificar_integridad_evento(e) for e in events)

def test_login_valido_no_genera_rechazo(client, usuario_base, db_session):
    response = client.post("/auth/login", json={"email": usuario_base.email, "password": "password123"})
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert db_session.query(SecurityOutbox).count() == 0
