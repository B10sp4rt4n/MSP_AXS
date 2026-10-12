"""Synthetic images only. Storage mocked; real auth, tenant scope and transactions."""
import io
import uuid
import pytest
from PIL import Image
from backend.db.core import Visita, Evidencia, EventOutbox
from backend.services import identificacion_service as service
from tests.test_destinos_visitas import people, headers


def jpeg(size=(1200, 800), color="blue"):
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, "JPEG")
    return out.getvalue()


@pytest.fixture
def setup(people, monkeypatch):
    people.add_all([Visita(visita_id="va", condominio_id="a1", nombre_visitante="Invitado"),
                    Visita(visita_id="vb", condominio_id="b1", nombre_visitante="Otro")])
    people.commit()
    class Store:
        assets = {}
        calls = 0
        fail_second = False
        def put(self, key, data):
            self.__class__.calls += 1
            if self.fail_second and self.calls == 2:
                raise RuntimeError("Synthetic outage")
            self.assets[key] = data
        def delete(self, key): self.assets.pop(key, None)
        def read(self, key): return self.assets[key]
    monkeypatch.setattr(service, "PrivateIdentityStore", Store)
    return people, Store


def send(client, visita="va", tenant="a1", role="GUARDIA", user="guard", capture=None,
         front=None, back=True, name="Nombre Sintético"):
    files = {"frente": ("frente.jpg", jpeg() if front is None else front, "image/jpeg")}
    if back: files["reverso"] = ("reverso.jpg", jpeg(color="red"), "image/jpeg")
    return client.post(f"/identificaciones/{visita}?condominio_id={tenant}",
        headers=headers(user, role), data={"nombre": name, "captura_id": capture or str(uuid.uuid4())}, files=files)


def test_pair_retry_and_private_read(client, setup):
    db, store = setup
    capture = str(uuid.uuid4())
    first = send(client, capture=capture)
    assert first.status_code == 200, first.text
    assert "archivo_url" not in first.text and "cloudinary" not in first.text
    assert send(client, capture=capture).json() == first.json()
    assert store.calls == 2 and db.query(Evidencia).count() == 2
    assert db.query(Visita).filter_by(visita_id="va").one().nombre_visitante == "Invitado"
    assert db.query(EventOutbox).count() == 1
    assert send(client, capture=capture, name="Otro Nombre").status_code == 409
    eid = first.json()["evidencias"][0]["evidencia_id"]
    photo = client.get(f"/identificaciones/va/{eid}?condominio_id=a1", headers=headers("guard", "GUARDIA"))
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/jpeg"
    assert "no-store" in photo.headers["cache-control"]
    assert db.query(EventOutbox).count() == 2
    assert client.get(f"/identificaciones/vb/{eid}?condominio_id=a1", headers=headers("guard", "GUARDIA")).status_code in (403, 404)
    for user, role in [("resident", "RESIDENTE"), ("unassigned", "residente")]:
        assert client.get(f"/identificaciones/va/{eid}?condominio_id=a1", headers=headers(user, role)).status_code == 403


@pytest.mark.parametrize("visita,tenant,user,role", [
    ("vb", "b1", "guard", "GUARDIA"), ("vb", "a1", "guard", "GUARDIA"),
    ("va", "b1", "guard", "GUARDIA"), ("va", "a1", "resident", "RESIDENTE")])
def test_denials_before_storage(client, setup, visita, tenant, user, role):
    _, store = setup
    assert send(client, visita, tenant, role, user).status_code in (403, 404)
    assert store.calls == 0
    assert client.get(f"/identificaciones/{visita}?condominio_id={tenant}", headers=headers(user, role)).status_code in (403, 404)


@pytest.mark.parametrize("front,status", [(b"not an image", 422), (jpeg((400, 300)), 422), (b"x" * (service.MAX_BYTES + 1), 413)])
def test_invalid_images(client, setup, front, status):
    _, store = setup
    assert send(client, front=front).status_code == status
    assert store.calls == 0


def test_missing_side(client, setup):
    assert send(client, back=False).status_code == 422
    assert setup[1].calls == 0


def test_partial_upload_rolls_back(client, setup):
    db, store = setup
    store.fail_second = True
    assert send(client).status_code == 503
    assert not store.assets and db.query(Evidencia).count() == 0 and db.query(EventOutbox).count() == 0


def test_audit_failure_rolls_back(client, setup, monkeypatch):
    db, store = setup
    def fail(*args, **kwargs): raise RuntimeError("audit unavailable")
    monkeypatch.setattr(service, "encolar_evento", fail)
    assert send(client).status_code == 503
    assert not store.assets and db.query(Evidencia).count() == 0


def test_store_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AXS_ID_PHOTOS_ENABLED", raising=False)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        service.PrivateIdentityStore()
    assert error.value.status_code == 503


def test_adapter_uses_authenticated_storage(monkeypatch):
    import cloudinary.uploader
    import cloudinary.utils
    import requests
    from backend.utils import cloudinary_service
    monkeypatch.setenv("AXS_ID_PHOTOS_ENABLED", "true")
    monkeypatch.setattr(cloudinary_service, "get_cloudinary_service", lambda: None)
    calls = {}
    def upload(data, **options):
        calls["upload"] = options
        return {"type": options["type"], "public_id": options["public_id"]}
    def url(key, fmt, **options):
        calls["read"] = options
        return "https://example.invalid/synthetic"
    class Download:
        content = b"synthetic"
        def raise_for_status(self): pass
    monkeypatch.setattr(cloudinary.uploader, "upload", upload)
    monkeypatch.setattr(cloudinary.utils, "private_download_url", url)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Download())
    store = service.PrivateIdentityStore()
    store.put("synthetic", b"synthetic")
    assert store.read("synthetic") == b"synthetic"
    assert calls["upload"]["type"] == calls["read"]["type"] == "authenticated"
    assert calls["upload"]["overwrite"] is False
    assert "expires_at" in calls["read"]
