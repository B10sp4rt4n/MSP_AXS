from datetime import datetime
import pytest
from backend.db.core import Evidencia, Visita, EventOutbox
from tests.test_identificaciones import setup, send
from tests.test_destinos_visitas import people, headers


def prepared(client, setup, capture=datetime(2026, 10, 12, 21), exit_at=None, state="pendiente"):
    db, store = setup
    upload = send(client)
    assert upload.status_code == 200
    for evidence in db.query(Evidencia).all():
        evidence.created_at = capture
    visit = db.query(Visita).filter_by(visita_id="va").one()
    visit.estado = state
    visit.salida_registrada_en = exit_at
    db.commit()
    return db, store


def fetch(client, cutoff="2026-11-11", user="admin", role="ADMIN_CONDOMINIO", tenant="a1"):
    return client.get(f"/reportes/{tenant}/identificaciones-vencimiento?fecha_corte={cutoff}", headers=headers(user, role))


def test_read_only_no_storage_no_identity_details(client, setup):
    db, store = prepared(client, setup)
    before = [(row.evidencia_id, row.archivo_url, row.metadata_json.copy()) for row in db.query(Evidencia).all()]
    before_events = db.query(EventOutbox).count()
    def forbidden(*args):
        raise AssertionError("Simulation must not contact photo storage")
    store.put = store.read = store.delete = forbidden
    response = fetch(client)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["modo"] == "simulacion" and data["borrado_activado"] is False
    assert data["resumen"]["venceria"] == 1 and data["total_fotos"] == 2
    assert "private" in response.headers["cache-control"] and "no-store" in response.headers["cache-control"]
    assert all(secret not in response.text for secret in ["Nombre Sintético", "archivo_url", "captura_id", "axs-identificaciones/"])
    assert [(row.evidencia_id, row.archivo_url, row.metadata_json.copy()) for row in db.query(Evidencia).all()] == before
    assert db.query(EventOutbox).count() == before_events
    assert db.query(Visita).filter_by(visita_id="va").one().estado == "pendiente"


@pytest.mark.parametrize("cutoff,classification", [("2026-11-10", "vigente"), ("2026-11-11", "venceria"), ("2026-10-01", "posterior_al_corte")])
def test_capture_based_cutoff(client, setup, cutoff, classification):
    prepared(client, setup)
    item = fetch(client, cutoff).json()["items"][0]
    assert item["clasificacion"] == classification
    assert item["venceria_en"] == "2026-11-11T21:00:00+00:00"


def test_exit_is_base_instead_of_capture(client, setup):
    prepared(client, setup, exit_at=datetime(2026, 10, 15, 17), state="salida_registrada")
    item = fetch(client).json()["items"][0]
    assert item["clasificacion"] == "vigente"
    assert item["venceria_en"] == "2026-11-14T17:00:00+00:00"


def test_mexico_cutoff_does_not_include_next_midnight(client, setup):
    prepared(client, setup, capture=datetime(2026, 10, 13, 6))
    assert fetch(client, "2026-11-11").json()["items"][0]["clasificacion"] == "vigente"
    assert fetch(client, "2026-11-12").json()["items"][0]["clasificacion"] == "venceria"


@pytest.mark.parametrize("issue", ["missing_side", "wrong_tenant", "wrong_capture", "public_storage", "missing_exit", "capture_after_exit"])
def test_inconsistent_pairs_require_review(client, setup, issue):
    db, _ = prepared(client, setup)
    row = db.query(Evidencia).first()
    visit = db.query(Visita).filter_by(visita_id="va").one()
    if issue == "missing_side": db.delete(row)
    elif issue in ("wrong_tenant", "wrong_capture", "public_storage"):
        key, value = {"wrong_tenant": ("condominio_id", "b1"), "wrong_capture": ("captura_id", "other"), "public_storage": ("storage", "public")}[issue]
        row.metadata_json = {**row.metadata_json, key: value}
    elif issue == "missing_exit": visit.estado = "salida_registrada"
    else:
        visit.estado = "salida_registrada"
        visit.salida_registrada_en = datetime(2026, 10, 10)
    db.commit()
    item = fetch(client).json()["items"][0]
    assert item["clasificacion"] == "revision" and item["venceria_en"] is None


@pytest.mark.parametrize("user,role,tenant", [("guard", "GUARDIA", "a1"), ("resident", "RESIDENTE", "a1"), ("admin", "ADMIN_CONDOMINIO", "b1"), ("msp", "MSP_ADMIN", "b1")])
def test_report_denies_roles_and_foreign_tenant(client, setup, user, role, tenant):
    prepared(client, setup)
    assert fetch(client, user=user, role=role, tenant=tenant).status_code == 403


def test_anonymous_denied_and_authorized_msp_allowed(client, setup):
    prepared(client, setup)
    assert client.get("/reportes/a1/identificaciones-vencimiento").status_code == 401
    assert fetch(client, user="msp", role="MSP_ADMIN").status_code == 200


def test_invalid_date_and_size_limit_fail_without_partial_report(client, setup, monkeypatch):
    prepared(client, setup)
    assert fetch(client, "not-a-date").status_code == 422
    assert fetch(client, "9999-12-31").status_code == 422
    from backend.services import identificacion_retencion
    monkeypatch.setattr(identificacion_retencion, "MAX_ROWS", 1)
    assert fetch(client).status_code == 422


def test_empty_report(client, people):
    data = fetch(client).json()
    assert data["total_identificaciones"] == 0 and data["items"] == []
