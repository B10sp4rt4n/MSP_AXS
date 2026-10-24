"""C0: signed Alexa requests and explicit privacy exceptions, synthetic only."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.orm import sessionmaker

from backend.core.auth.jwt import create_access_token
from backend.db.core import Condominio, EventOutbox, ScopeStatus, UserTenantScope
from backend.db.core.models import ArcoCase
from tests.test_alexa_voice import envelope, signer, pilot, invoke
from tests.test_alexa_linking import beta, grant, link
from tests.test_tenant_modalidad_http import boundary, TENANT, UUID


@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
def test_queued_pilot_notification_rechecks_modality(
    db_session, condominio_base, monkeypatch, enabled,
):
    """A residential movement can be queued before its tenant is reclassified."""
    from backend.services import alexa_notifications as notifications
    import backend.db.core
    for key, value in {"AXS_ALEXA_ENABLED": "true", "AXS_ALEXA_LINKING_ENABLED": "false",
                       "AXS_ALEXA_PILOT_CONDOMINIO_ID": condominio_base.condominio_id,
                       "AXS_ALEXA_PILOT_CASA_ID": "house", "AXS_ALEXA_PILOT_USER_ID": "amzn1.ask.account.test"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(backend.db.core, "SessionLocal_CORE", sessionmaker(bind=db_session.bind))
    sent = []
    monkeypatch.setattr(notifications, "enviar_aviso", lambda *args: sent.append(args))
    visit = SimpleNamespace(estado="entrada_registrada", entrada_registrada_en=datetime.utcnow(),
                            destino_tipo="vivienda", destino_id="house", visita_id="synthetic",
                            condominio_id=condominio_base.condominio_id)
    tasks = BackgroundTasks()
    notifications.programar_aviso(tasks, visit)
    assert len(tasks.tasks) == 1
    condominio_base.modalidad, condominio_base.corporativo_habilitado = "corporativo", enabled
    db_session.commit()
    asyncio.run(tasks())
    assert sent == []


@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
def test_pilot_voice_never_reads_corporate_visits(client, db_session, pilot, signer, envelope, enabled):
    condo = db_session.query(Condominio).filter_by(condominio_id=pilot.condominio_id).one()
    condo.modalidad, condo.corporativo_habilitado = "corporativo", enabled
    db_session.commit()
    response = invoke(client, signer, envelope)
    assert response.status_code == 403, response.text
    assert "Juan" not in response.text and "voice-house" not in response.text
    assert db_session.query(EventOutbox).count() == 0


@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
def test_beta_denies_link_voice_and_status_but_allows_disconnect(
    client, db_session, beta, pilot, signer, envelope, enabled,
):
    grant(client, signer, envelope)
    assert link(client, signer, envelope).status_code == 200
    before = db_session.query(EventOutbox).count()
    condo = db_session.query(Condominio).filter_by(condominio_id=pilot.condominio_id).one()
    condo.modalidad, condo.corporativo_habilitado = "corporativo", enabled
    db_session.commit()
    envelope["context"]["System"]["user"]["accessToken"] = "valid-access-token"
    response = invoke(client, signer, envelope)
    assert response.status_code == 403 and "Juan" not in response.text
    assert link(client, signer, envelope, minute=6).status_code == 403
    assert db_session.query(EventOutbox).count() == before
    headers = {"Authorization": "Bearer " + create_access_token(beta.usuario_id, "RESIDENTE")}
    response = client.get("/alexa/vinculacion", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"beta_habilitada": True, "vinculada": False, "notificaciones": False}
    db_session.query(UserTenantScope).filter_by(usuario_id=beta.usuario_id).update(
        {"estado": ScopeStatus.REVOCADO})
    db_session.commit()
    response = client.delete("/alexa/vinculacion", headers=headers)
    assert response.status_code == 200 and response.json()["vinculada"] is False
    assert db_session.query(EventOutbox).count() == before + 1


@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
def test_arco_keeps_designated_scoped_access_in_both_corporate_states(
    client, boundary, monkeypatch, enabled,
):
    db = boundary
    db.query(Condominio).filter_by(condominio_id=TENANT).one().corporativo_habilitado = enabled
    db.commit()
    monkeypatch.setenv("AXS_ARCO_CASES_ENABLED", "true")
    monkeypatch.setenv("AXS_ARCO_OPERATORS", "local:" + TENANT + ",outsider-matrix:" + TENANT)
    headers = {"Authorization": "Bearer " + create_access_token("local", "ADMIN_CONDOMINIO")}
    body = {"request_id": UUID, "received_at": (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),
            "determination_due": (datetime.now(timezone.utc)+timedelta(days=20)).isoformat(),
            "right": "cancelacion", "subject_ref": "PRIVATE_DOSSIER_SENTINEL", "owner_id": "privacy-owner"}
    response = client.post("/arco/" + TENANT, headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    response = client.get("/arco/" + TENANT, headers=headers)
    assert response.status_code == 200 and len(response.json()) == 1
    response = client.post("/arco/" + TENANT + "/" + UUID + "/estado", headers=headers,
                           json={"version": 1, "state": "verificada", "reference": "SYNTHETIC"})
    assert response.status_code == 200 and response.json()["state"] == "verificada"
    for actor in ("global-matrix", "outsider-matrix"):
        # GLOBAL still needs designation; designation never substitutes scope.
        denied = client.get("/arco/" + TENANT, headers={
            "Authorization": "Bearer " + create_access_token(actor, "ADMIN_CONDOMINIO")})
        assert denied.status_code == 403
        assert "PRIVATE_DOSSIER_SENTINEL" not in denied.text
    assert db.query(ArcoCase).count() == 1
    assert "PRIVATE_DOSSIER_SENTINEL" not in str([row.payload for row in db.query(EventOutbox)])
    monkeypatch.setenv("AXS_ARCO_CASES_ENABLED", "false")
    assert client.get("/arco/" + TENANT, headers=headers).status_code == 404
