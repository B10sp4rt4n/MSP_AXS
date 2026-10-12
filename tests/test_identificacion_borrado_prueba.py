import uuid
import pytest
from fastapi import HTTPException
from backend.db.core import Evidencia, Visita, EventOutbox
from backend.services import identificacion_borrado_prueba as purge_service
from tests.test_identificaciones import setup, send
from tests.test_destinos_visitas import people, headers


@pytest.fixture
def pilot(client, setup, monkeypatch):
    db, store = setup
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("NEON_DEV_ENDPOINT", "ep-withered-resonance-b59tusv3")
    monkeypatch.setenv("AXS_ID_PHOTOS_TEST_PURGE_ENABLED", "true")
    capture = str(uuid.uuid4())
    assert send(client, capture=capture, name=purge_service.LABEL).status_code == 200
    visit = db.query(Visita).filter_by(visita_id="va").one()
    visit.estado = "cancelada"
    db.commit()
    monkeypatch.setattr(purge_service, "FIXTURES", {"a1": {"visita_id": "va", "actor": "admin", "nombre": "Invitado", "captura_id": capture}})
    monkeypatch.setattr(purge_service, "EXPECTED_HASHES", {row.sub_tipo: row.hash_sha256 for row in db.query(Evidencia).all()})
    def read(self, key):
        if key not in self.assets:
            raise HTTPException(404, "missing synthetic object")
        return self.assets[key]
    store.read = read
    return db, store


def delete(client, user="admin", role="ADMIN_CONDOMINIO", tenant="a1", visit="va"):
    return client.delete(f"/identificaciones/{visit}/borrado-prueba?condominio_id={tenant}", headers=headers(user, role))


def test_pair_deleted_and_audited_without_reupload_or_duplicate_event(client, pilot):
    db, store = pilot
    ids = [row.evidencia_id for row in db.query(Evidencia).all()]
    first = delete(client)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["estado"] == "eliminada" and result["proveedor_verificado_ausente"] is True
    assert not store.assets
    assert delete(client).json() == result
    events = [row.payload for row in db.query(EventOutbox).all()]
    assert len(events) == 3
    assert sum(event["accion"] == "eliminar_identificacion_prueba" for event in events) == 1
    assert all("archivo_url" not in str(event) and purge_service.LABEL not in str(event) for event in events)
    for row in db.query(Evidencia).all():
        assert row.archivo_url is None and row.hash_sha256 is None
        assert "nombre" not in row.metadata_json and "captura_id" not in row.metadata_json
    access = headers("admin", "ADMIN_CONDOMINIO")
    listing = client.get("/identificaciones/va?condominio_id=a1", headers=access).json()
    assert listing["estado"] == "eliminada" and listing["evidencias"] == []
    for eid in ids:
        assert client.get(f"/identificaciones/va/{eid}?condominio_id=a1", headers=access).status_code == 410
    assert send(client).status_code == 409
    report = client.get("/reportes/a1/identificaciones-vencimiento", headers=access).json()
    assert report["total_identificaciones"] == 0
    assert db.query(Visita).filter_by(visita_id="va").one().estado == "cancelada"


@pytest.mark.parametrize("env,value", [("APP_ENV", "production"), ("NEON_DEV_ENDPOINT", "wrong"), ("AXS_ID_PHOTOS_TEST_PURGE_ENABLED", "false")])
def test_disabled_or_production_never_deletes(client, pilot, monkeypatch, env, value):
    db, store = pilot
    monkeypatch.setenv(env, value)
    assert delete(client).status_code == 404
    assert len(store.assets) == 2 and db.query(EventOutbox).count() == 1


@pytest.mark.parametrize("issue", ["name", "actor", "capture", "key", "metadata_hash", "content", "active_visit"])
def test_non_fixture_or_tampered_content_never_deleted(client, pilot, issue, monkeypatch):
    db, store = pilot
    row = db.query(Evidencia).first()
    visit = db.query(Visita).filter_by(visita_id="va").one()
    if issue == "name": row.metadata_json = {**row.metadata_json, "nombre": "Real document"}
    elif issue == "actor": monkeypatch.setitem(purge_service.FIXTURES["a1"], "actor", "someone_else")
    elif issue == "capture": row.metadata_json = {**row.metadata_json, "captura_id": str(uuid.uuid4())}
    elif issue == "key": row.archivo_url = "unrelated-object"
    elif issue == "metadata_hash": row.hash_sha256 = "wrong"
    elif issue == "content": store.assets[row.archivo_url] = b"unexpected actual content"
    else: visit.estado = "entrada_registrada"
    db.commit()
    before = dict(store.assets)
    assert delete(client).status_code == 409
    assert store.assets == before and db.query(EventOutbox).count() == 1


@pytest.mark.parametrize("user,role,tenant", [("guard", "GUARDIA", "a1"), ("resident", "RESIDENTE", "a1"), ("admin", "ADMIN_CONDOMINIO", "b1")])
def test_foreign_or_nonadmin_denied(client, pilot, user, role, tenant):
    assert delete(client, user=user, role=role, tenant=tenant).status_code == 403
    assert len(pilot[1].assets) == 2


def test_partial_provider_failure_remains_pending_and_retry_completes(client, pilot):
    db, store = pilot
    ids = [row.evidencia_id for row in db.query(Evidencia).all()]
    original = store.delete
    calls = []
    def fail_second(self, key):
        calls.append(key)
        if len(calls) == 2: raise RuntimeError("synthetic provider outage")
        original(self, key)
    store.delete = fail_second
    assert delete(client).status_code == 503
    assert len(store.assets) == 1
    assert all(row.metadata_json["purge_status"] == "pending" for row in db.query(Evidencia).all())
    for eid in ids:
        assert client.get(f"/identificaciones/va/{eid}?condominio_id=a1", headers=headers("admin", "ADMIN_CONDOMINIO")).status_code == 410
    assert client.get("/identificaciones/va?condominio_id=a1", headers=headers("admin", "ADMIN_CONDOMINIO")).json()["estado"] == "eliminando"
    store.delete = original
    assert delete(client).status_code == 200
    assert not store.assets and db.query(EventOutbox).count() == 3


def test_intent_audit_failure_prevents_physical_deletion(client, pilot, monkeypatch):
    db, store = pilot
    def fail(*args, **kwargs): raise RuntimeError("audit unavailable")
    monkeypatch.setattr(purge_service, "encolar_evento", fail)
    assert delete(client).status_code == 503
    assert len(store.assets) == 2
    assert all(not row.metadata_json.get("purge_status") for row in db.query(Evidencia).all())


def test_completion_audit_failure_preserves_retryable_intent(client, pilot, monkeypatch):
    db, store = pilot
    original = purge_service.encolar_evento
    def fail_completion(*args, **kwargs):
        if args[3]["accion"] == "eliminar_identificacion_prueba": raise RuntimeError("completion audit unavailable")
        return original(*args, **kwargs)
    monkeypatch.setattr(purge_service, "encolar_evento", fail_completion)
    assert delete(client).status_code == 503
    assert not store.assets and db.query(EventOutbox).count() == 2
    assert all(row.metadata_json["purge_status"] == "pending" for row in db.query(Evidencia).all())
    monkeypatch.setattr(purge_service, "encolar_evento", original)
    assert delete(client).status_code == 200
    assert db.query(EventOutbox).count() == 3


def test_sdk_missing_object_normalized_to_404(monkeypatch):
    from vercel import blob
    from backend.services.identificacion_service import PrivateIdentityStore
    monkeypatch.setenv("AXS_ID_PHOTOS_ENABLED", "true")
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "synthetic")
    def missing(*args, **kwargs): raise blob.BlobNotFoundError()
    monkeypatch.setattr(blob, "get", missing)
    with pytest.raises(HTTPException) as error: PrivateIdentityStore().read("synthetic-key")
    assert error.value.status_code == 404
