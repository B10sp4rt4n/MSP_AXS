"""Exit photos: independent movement, idempotency, tenant boundaries and privacy."""
import uuid
from datetime import datetime
import pytest
from backend.db.core import Visita, Condominio, Evidencia
from backend.schemas.reglas_acceso import ReglasAcceso
from tests.test_identificaciones import setup, jpeg
from tests.test_destinos_visitas import people, headers


def send(client, capture=None, tenant="a1", visita="va", user="guard", role="GUARDIA", data=None):
    return client.post(f"/evidencias-salida/{visita}?condominio_id={tenant}",
        headers=headers(user, role), data={"captura_id": capture or str(uuid.uuid4())},
        files={"foto": ("salida.jpg", jpeg() if data is None else data, "image/jpeg")})


def exit_visit(db):
    row = db.query(Visita).filter_by(visita_id="va").one()
    row.estado = "salida_registrada"
    row.entrada_registrada_en = datetime(2026, 10, 17, 10)
    row.salida_registrada_en = datetime(2026, 10, 17, 11)
    db.commit()


def test_optional_default_and_valid_modes():
    assert ReglasAcceso().foto_salida == "bajo_demanda"
    for mode in ("bajo_demanda", "siempre_visible", "deshabilitada"):
        assert ReglasAcceso(foto_salida=mode).foto_salida == mode
    with pytest.raises(ValueError):
        ReglasAcceso(foto_salida="obligatoria")


def test_exit_required_and_retry_private_read(client, setup):
    db, store = setup
    assert send(client).status_code == 409
    assert store.calls == 0
    exit_visit(db)
    capture = str(uuid.uuid4())
    first = send(client, capture)
    assert first.status_code == 200, first.text
    assert send(client, capture).json() == first.json()
    assert store.calls == 1
    assert send(client).status_code == 409
    row = db.query(Evidencia).one()
    assert row.categoria == "salida" and row.guardia_id == "guard"
    assert row.metadata_json["salida_registrada_en"] == "2026-10-17T11:00:00Z"
    assert "archivo_url" not in first.text
    path = f'/evidencias-salida/va/{first.json()["evidencia_id"]}?condominio_id=a1'
    photo = client.get(path, headers=headers("guard", "GUARDIA"))
    assert photo.status_code == 200
    assert photo.headers["cache-control"] == "private, no-store"
    assert client.get('/identificaciones/va?condominio_id=a1', headers=headers("guard", "GUARDIA")).json()["evidencias"] == []
    assert client.get(path, headers=headers("resident", "RESIDENTE")).status_code == 403
    assert client.get(path.replace('/va/', '/vb/'), headers=headers("guard", "GUARDIA")).status_code in (403, 404)


def test_disabled_capture_preserves_history(client, setup):
    db, store = setup
    exit_visit(db)
    assert send(client).status_code == 200
    condo = db.query(Condominio).filter_by(condominio_id="a1").one()
    condo.reglas_acceso = {"foto_salida": "deshabilitada"}
    db.commit()
    assert send(client).status_code == 403
    assert store.calls == 1
    result = client.get('/evidencias-salida/va?condominio_id=a1', headers=headers("guard", "GUARDIA"))
    assert result.status_code == 200 and len(result.json()) == 1


@pytest.mark.parametrize("tenant,visita,user,role", [("b1", "vb", "guard", "GUARDIA"), ("a1", "vb", "guard", "GUARDIA"), ("a1", "va", "resident", "RESIDENTE")])
def test_scope_before_storage(client, setup, tenant, visita, user, role):
    assert send(client, tenant=tenant, visita=visita, user=user, role=role).status_code in (403, 404)
    assert setup[1].calls == 0


def test_failure_does_not_undo_exit(client, setup, monkeypatch):
    db, store = setup
    exit_visit(db)
    def fail(*args): raise RuntimeError("Synthetic outage")
    monkeypatch.setattr(store, "put", fail)
    assert send(client).status_code == 503
    assert db.query(Evidencia).count() == 0
    assert db.query(Visita).filter_by(visita_id="va").one().salida_registrada_en == datetime(2026, 10, 17, 11)


@pytest.mark.parametrize("data,status", [(b"invalid", 422), (b"x" * (8 * 1024 * 1024 + 1), 413)], ids=["invalid-format", "over-8mb-limit"])
def test_invalid_image(client, setup, data, status):
    exit_visit(setup[0])
    assert send(client, data=data).status_code == status
    assert setup[1].calls == 0
