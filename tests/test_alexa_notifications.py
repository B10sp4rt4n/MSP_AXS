from datetime import datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from fastapi import BackgroundTasks
from sqlalchemy.orm import sessionmaker

from backend.services import alexa_notifications as alexa
from backend.db.core import Usuario, UserTenantScope, AccessLevel, ScopeStatus, Visita, Casa
from backend.core.auth.jwt import create_access_token


@pytest.fixture
def pilot(monkeypatch):
    for key, value in {
        "AXS_ALEXA_ENABLED": "true", "AXS_ALEXA_PILOT_CONDOMINIO_ID": "condo_test_001",
        "AXS_ALEXA_PILOT_CASA_ID": "house1", "AXS_ALEXA_PILOT_USER_ID": "amzn1.ask.account.test",
        "AXS_ALEXA_CLIENT_ID": "test-client", "AXS_ALEXA_CLIENT_SECRET": "private-test-secret",
    }.items():
        monkeypatch.setenv(key, value)
    return SimpleNamespace(condominio_id="condo_test_001", destino_id="house1", destino_tipo="vivienda",
        estado="entrada_registrada", entrada_registrada_en=datetime.utcnow(), visita_id="visit1")


@pytest.mark.parametrize("field,value", [
    ("condominio_id", "another-tenant"), ("destino_id", "another-house"),
    ("destino_tipo", "comun"), ("estado", "pendiente"), ("entrada_registrada_en", None),
])
def test_aislamiento_y_solo_entradas(pilot, field, value):
    setattr(pilot, field, value)
    tasks = BackgroundTasks()
    alexa.programar_aviso(tasks, pilot)
    assert not tasks.tasks


def test_apagado_por_defecto(pilot, monkeypatch):
    monkeypatch.delenv("AXS_ALEXA_ENABLED")
    tasks = BackgroundTasks()
    alexa.programar_aviso(tasks, pilot)
    assert not tasks.tasks


def test_evento_unicast_sin_pii_y_referencia_estable(pilot, monkeypatch, db_session, condominio_base):
    import backend.db.core
    monkeypatch.setattr(backend.db.core, "SessionLocal_CORE", sessionmaker(bind=db_session.bind))
    requests = []
    def handler(request):
        requests.append(request)
        if request.url == alexa.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "private-test-token"})
        return httpx.Response(202)
    real_client = httpx.Client
    monkeypatch.setattr(alexa.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    tasks = BackgroundTasks()
    alexa.programar_aviso(tasks, pilot)
    second = BackgroundTasks()
    alexa.programar_aviso(second, pilot)
    assert tasks.tasks[0].args == second.tasks[0].args
    tasks.tasks[0].func(*tasks.tasks[0].args)
    import json
    payload = json.loads(requests[1].content)
    assert payload["relevantAudience"] == {"type": "Unicast", "payload": {"user": "amzn1.ask.account.test"}}
    assert payload["event"]["name"] == "AMAZON.MessageAlert.Activated"
    assert "visit1" not in str(payload) and "house1" not in str(payload)
    assert "alexa%3A%3Aproactive_events" in requests[0].content.decode()


@pytest.mark.parametrize("mode", ["timeout", "401", "403", "500"])
def test_fallo_no_propaga_ni_expone_secretos(pilot, monkeypatch, caplog, mode):
    def handler(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("private-test-secret", request=request)
        return httpx.Response(int(mode), json={"error": "private-test-secret"})
    real_client = httpx.Client
    monkeypatch.setattr(alexa.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    alexa.enviar_aviso("amzn1.ask.account.test", "AXStest")
    assert "private-test-secret" not in caplog.text
    assert "amzn1.ask.account.test" not in caplog.text


@pytest.mark.parametrize("mode", ["manual", "qr", "direct", "salida"])
def test_rutas_notifican_solo_entrada_confirmada(client, db_session, condominio_base, pilot, monkeypatch, mode):
    import backend.db.core
    monkeypatch.setattr(backend.db.core, "SessionLocal_CORE", sessionmaker(bind=db_session.bind))
    db_session.add(Casa(casa_id="house1", condominio_id=condominio_base.condominio_id, numero="101", tipo="casa"))
    db_session.add(Usuario(usuario_id="alexa-guard", email="guard@alexa.test", rol="GUARDIA",
                           condominio_id=condominio_base.condominio_id))
    db_session.flush()
    db_session.add(UserTenantScope(usuario_id="alexa-guard", tenant_id=condominio_base.condominio_id,
                                   access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO))
    row = Visita(visita_id="visit1", condominio_id=condominio_base.condominio_id, casa_unidad="101",
                 destino_id="house1", destino_tipo="vivienda", estado="pendiente",
                 nombre_visitante="Test", tipo_visita="eventual", vigencia=datetime.utcnow())
    if mode == "salida":
        row.estado = "entrada_registrada"
        row.entrada_registrada_en = datetime.utcnow() - timedelta(hours=2)
    if mode == "qr":
        row.qr_token = "testqr"
        row.qr_vigencia = datetime.utcnow() + timedelta(minutes=30)
    db_session.add(row)
    db_session.commit()
    sent = []
    def send(*args):
        # The response background task sees an already committed entrance.
        saved = db_session.query(Visita).filter_by(estado="salida_registrada" if mode == "salida" else "entrada_registrada").one()
        if mode == "salida":
            assert saved.salida_registrada_en is not None
        assert saved.entrada_registrada_en is not None
        sent.append(args)
    monkeypatch.setattr(alexa, "enviar_aviso", send)
    headers = {"Authorization": "Bearer " + create_access_token("alexa-guard", "GUARDIA")}
    if mode == "direct":
        from backend.routers import visitas_router
        monkeypatch.setattr(visitas_router, "puede_ejecutar_accion", lambda **kwargs: (True, "test policy"))
        response = client.post(f"/visitas/entrada/{condominio_base.condominio_id}", headers=headers,
            json={"condominio_id": condominio_base.condominio_id, "destino_id": "house1", "nombre_visitante": "Test",
                  "tipo_visita": "eventual", "vigencia": datetime.utcnow().isoformat()})
    elif mode == "salida":
        response = client.patch("/visitas/visit1/salida", headers=headers)
        assert client.patch("/visitas/visit1/salida", headers=headers).status_code == 400
    elif mode == "qr":
        response = client.get("/qr/validar/visit1/testqr", headers=headers)
        assert client.get("/qr/validar/visit1/testqr", headers=headers).status_code == 400
    else:
        response = client.patch("/visitas/visit1/entrada", headers=headers)
        assert client.patch("/visitas/visit1/entrada", headers=headers).status_code == 400
    assert response.status_code == 200, response.text
    assert len(sent) == 1


def test_salida_requiere_hora_y_referencia_distinta(pilot):
    entry = BackgroundTasks()
    alexa.programar_aviso(entry, pilot)
    pilot.estado = 'salida_registrada'
    missing = BackgroundTasks()
    alexa.programar_aviso(missing, pilot)
    assert not missing.tasks
    pilot.salida_registrada_en = datetime.utcnow()
    exit_tasks = BackgroundTasks()
    alexa.programar_aviso(exit_tasks, pilot)
    assert len(exit_tasks.tasks) == 1
    assert entry.tasks[0].args != exit_tasks.tasks[0].args
