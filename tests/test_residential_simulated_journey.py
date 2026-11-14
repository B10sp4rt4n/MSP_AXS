"""Synthetic HTTP lifecycle on the integrated candidate; no Clerk or live Blob.

Use the same token before and after scope revocation. Storage is an in-memory
adapter; requests still use the application routes, auth, services and database.
"""
from uuid import uuid4

import pytest

from backend.db.core import (
    AccessLevel, Evidencia, ScopeStatus, UserTenantScope, Usuario, Visita,
)
from tests.test_destinos_visitas import headers, people, prereg_catalog  # noqa: F401
from tests.test_identificaciones import setup, send as identification  # noqa: F401
from tests.test_evidencias_salida import send as exit_photo


@pytest.mark.parametrize("photo_mode", ["omit", "capture", "storage-failure-retry"])
def test_residential_lifecycle_with_tenant_boundaries_and_revocation(
    client, prereg_catalog, setup, monkeypatch, photo_mode,
):
    db, store = setup
    db.add(Usuario(usuario_id="guard_b", email="guard-b@example.test", rol="GUARDIA",
                   condominio_id="b1"))
    db.flush()
    db.add(UserTenantScope(usuario_id="guard_b", tenant_id="b1",
                           access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO))
    db.commit()
    guard = headers("guard", "GUARDIA")
    guard_b = headers("guard_b", "GUARDIA")

    created = client.post("/preregistro/crear", headers=headers("resident", "RESIDENTE"),
                          json={"nombre_visitante": "Visita sintética integrada",
                                "tipo_visita": "visita_personal"})
    assert created.status_code == 200, created.text
    visit_id = created.json()["visita_id"]
    visit = db.query(Visita).filter_by(visita_id=visit_id).one()
    assert visit.destino_id == "home" and visit.casa_unidad == "101"
    assert visit.autorizada_por == "resident" and visit.entrada_registrada_en is None
    qr_path = f"/qr/validar/{visit_id}/{visit.qr_token}"
    visit_path = f"/visitas/{visit_id}?condominio_id=a1"

    # The correct QR is insufficient outside the guard's tenant. Check both ways.
    assert client.get(qr_path + "?condominio_id=a1", headers=guard_b).status_code == 403
    assert client.get(qr_path + "?condominio_id=b1", headers=guard_b).status_code in (403, 404)
    assert client.get("/visitas/vb?condominio_id=b1", headers=guard).status_code == 403
    assert client.get(qr_path.rsplit("/", 1)[0] + "/invalid", headers=guard).status_code == 400
    db.refresh(visit)
    assert visit.entrada_registrada_en is None
    assert client.patch(f"/visitas/{visit_id}/entrada", headers=guard).status_code == 400

    assert client.get(qr_path, headers=guard).status_code == 200
    db.refresh(visit)
    entered_at = visit.entrada_registrada_en
    assert visit.estado == "entrada_registrada" and entered_at is not None
    assert client.get(qr_path, headers=guard).status_code == 400
    db.refresh(visit)
    assert visit.entrada_registrada_en == entered_at

    capture = str(uuid4())
    identity = identification(client, visita=visit_id, capture=capture)
    assert identity.status_code == 200, identity.text
    assert identification(client, visita=visit_id, capture=capture).json() == identity.json()
    assert store.calls == 2
    assert exit_photo(client, visita=visit_id).status_code == 409

    left = client.patch(f"/visitas/{visit_id}/salida", headers=guard)
    assert left.status_code == 200, left.text
    db.refresh(visit)
    left_at = visit.salida_registrada_en
    assert visit.estado == "salida_registrada" and left_at >= entered_at
    assert client.patch(f"/visitas/{visit_id}/salida", headers=guard).status_code == 400
    db.refresh(visit)
    assert visit.salida_registrada_en == left_at

    if photo_mode != "omit":
        photo_capture = str(uuid4())
        if photo_mode == "storage-failure-retry":
            def fail(*args):
                raise RuntimeError("Synthetic storage outage")
            with monkeypatch.context() as patch:
                patch.setattr(store, "put", fail)
                assert exit_photo(client, visita=visit_id, capture=photo_capture).status_code == 503
            db.refresh(visit)
            assert visit.estado == "salida_registrada" and visit.salida_registrada_en == left_at
            assert db.query(Evidencia).filter_by(visita_id=visit_id).count() == 2
        photo = exit_photo(client, visita=visit_id, capture=photo_capture)
        assert photo.status_code == 200, photo.text
        assert exit_photo(client, visita=visit_id, capture=photo_capture).json() == photo.json()
        assert store.calls == 3

    evidence = db.query(Evidencia).filter_by(visita_id=visit_id).all()
    assert len(evidence) == (2 if photo_mode == "omit" else 3)
    assert db.query(Visita).filter_by(visita_id=visit_id).count() == 1
    assert db.query(Evidencia).filter_by(visita_id="vb").count() == 0
    identity_id = identity.json()["evidencias"][0]["evidencia_id"]
    photo_path = f"/identificaciones/{visit_id}/{identity_id}?condominio_id=a1"
    private = client.get(photo_path, headers=guard)
    assert private.status_code == 200 and "no-store" in private.headers["cache-control"]
    assert client.get(photo_path, headers=guard_b).status_code == 403
    assert client.get(photo_path, headers=headers("resident", "RESIDENTE")).status_code == 403
    assert client.get(visit_path, headers=guard).status_code == 200

    # Reuse the already issued JWT: scope must be read again for each request.
    scope = db.query(UserTenantScope).filter_by(usuario_id="guard", tenant_id="a1").one()
    scope.estado = ScopeStatus.REVOCADO
    db.commit()
    assert client.get(visit_path, headers=guard).status_code == 403
    assert client.get(photo_path, headers=guard).status_code == 403
    assert client.get(qr_path, headers=guard).status_code == 403
    db.refresh(visit)
    assert visit.entrada_registrada_en == entered_at and visit.salida_registrada_en == left_at
