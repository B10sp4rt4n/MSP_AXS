"""Alta autorizada de personal y vinculación de cuentas Clerk."""
import pytest
from backend.core.auth.jwt import create_access_token
from backend.db.core import (MSP, Condominio, Usuario, UserTenantScope, MSPMembership,
                             AccessLevel, ScopeStatus)


def headers(identity, role):
    return {"Authorization": f"Bearer {create_access_token(identity, role)}"}


@pytest.fixture
def people(db_session):
    db_session.add_all([MSP(msp_id=m, nombre=m) for m in ("a", "b")])
    db_session.flush()
    db_session.add_all([Condominio(condominio_id=f"{m}1", msp_id=m, nombre=m) for m in ("a", "b")])
    db_session.flush()
    db_session.add_all([
        Usuario(usuario_id="msp", email="msp@test.local", rol="MSP_ADMIN"),
        Usuario(usuario_id="admin", email="admin@test.local", rol="ADMIN_CONDOMINIO", condominio_id="a1"),
        Usuario(usuario_id="resident", email="resident@test.local", rol="RESIDENTE", condominio_id="a1"),
        Usuario(usuario_id="guard", email="guard@test.local", rol="GUARDIA", condominio_id="a1"),
        Usuario(usuario_id="unassigned", email="waiting@test.local", rol="residente", clerk_id="clerk_wait"),
    ])
    db_session.flush()
    db_session.add(MSPMembership(usuario_id="msp", msp_id="a"))
    for user, level in [("admin", AccessLevel.ADMIN_CONDOMINIO), ("resident", AccessLevel.RESIDENTE),
                        ("guard", AccessLevel.GUARDIA)]:
        db_session.add(UserTenantScope(usuario_id=user, tenant_id="a1", access_level=level,
                                       estado=ScopeStatus.ACTIVO))
    db_session.commit()
    return db_session


def test_alta_personal_y_limites_http(client, people):
    db = people
    msp = headers("msp", "MSP_ADMIN")
    admin = headers("admin", "ADMIN_CONDOMINIO")
    body = {"nombre": " Nuevo guardia ", "email": " NEW@Test.Local ", "rol": "GUARDIA"}
    created = client.post("/condominios/a1/usuarios", headers=admin, json=body)
    assert created.status_code == 200, created.text
    saved = db.query(Usuario).filter_by(usuario_id=created.json()["usuario_id"]).one()
    assert saved.email == "new@test.local" and saved.rol == "GUARDIA"
    assert saved.condominio_id == "a1" and saved.msp_id == "a"
    assert saved.casa_id is None and saved.casa_unidad is None
    scope = db.query(UserTenantScope).filter_by(usuario_id=saved.usuario_id).one()
    assert scope.tenant_id == "a1" and scope.access_level == AccessLevel.GUARDIA
    assert client.post("/condominios/a1/usuarios", headers=admin, json=body).status_code == 409
    assert client.post("/condominios/b1/usuarios", headers=msp, json=body).status_code == 403
    for role, identity in [("RESIDENTE", "resident"), ("GUARDIA", "guard")]:
        h = headers(identity, role)
        assert client.post("/condominios/a1/usuarios", headers=h, json=body).status_code == 403
        assert client.get("/condominios/a1/usuarios", headers=h).status_code == 403
    admin_body = {**body, "email": "second_admin@test.local", "rol": "ADMIN_CONDOMINIO"}
    assert client.post("/condominios/a1/usuarios", headers=admin, json=admin_body).status_code == 403
    new_admin = client.post("/condominios/a1/usuarios", headers=msp, json=admin_body)
    assert new_admin.status_code == 200, new_admin.text
    assert client.post("/condominios/a1/usuarios", headers=msp, json={**body, "rol": "MSP_ADMIN"}).status_code == 422
    assert client.post("/condominios/a1/usuarios", headers=msp, json={**body, "email": "invalid"}).status_code == 422
    listing = client.get("/condominios/a1/usuarios", headers=msp)
    assert listing.status_code == 200
    assert {"GUARDIA", "ADMIN_CONDOMINIO", "RESIDENTE"} <= {u["rol"] for u in listing.json()}
    assert client.get("/condominios/b1/usuarios", headers=msp).status_code == 403
    staff_headers = headers(saved.usuario_id, "GUARDIA")
    assert client.get("/condominios/a1/casas", headers=staff_headers).status_code == 200
    assert client.get("/condominios/b1/casas", headers=staff_headers).status_code == 403


def test_no_reasigna_identidades_y_admite_autorregistro_sin_scope(client, people):
    msp = headers("msp", "MSP_ADMIN")
    for email in ("resident@test.local", "msp@test.local", "guard@test.local"):
        response = client.post("/condominios/a1/usuarios", headers=msp,
                               json={"nombre": "Change", "email": email, "rol": "GUARDIA"})
        assert response.status_code == 409
    assert people.query(Usuario).filter_by(usuario_id="resident").one().rol == "RESIDENTE"
    response = client.post("/condominios/a1/usuarios", headers=msp,
                           json={"nombre": "Waiting", "email": "waiting@test.local", "rol": "GUARDIA"})
    assert response.status_code == 200, response.text
    assert response.json()["usuario_id"] == "unassigned"
    assert response.json()["registro_pendiente"] is False
    assert people.query(UserTenantScope).filter_by(usuario_id="unassigned").count() == 1


def test_webhook_vincula_sin_perder_rol(client, people, monkeypatch):
    import backend.routers.webhooks_router as webhook
    monkeypatch.setattr(webhook, "CLERK_WEBHOOK_SECRET", "")
    msp = headers("msp", "MSP_ADMIN")
    result = client.post("/condominios/a1/usuarios", headers=msp,
                         json={"nombre": "Admin", "email": "link@test.local", "rol": "ADMIN_CONDOMINIO"})
    assert result.status_code == 200
    payload = {"type": "user.created", "data": {
        "id": "clerk_admin", "primary_email_address_id": "primary",
        "email_addresses": [{"id": "other", "email_address": "other@test.local"},
                            {"id": "primary", "email_address": "LINK@Test.Local"}],
    }}
    response = client.post("/webhooks/clerk", json=payload)
    assert response.status_code == 200, response.text
    saved = people.query(Usuario).filter_by(usuario_id=result.json()["usuario_id"]).one()
    assert saved.clerk_id == "clerk_admin" and saved.rol == "ADMIN_CONDOMINIO"
    assert people.query(UserTenantScope).filter_by(usuario_id=saved.usuario_id).one().access_level == AccessLevel.ADMIN_CONDOMINIO
    payload["data"]["id"] = "clerk_new"
    payload["data"]["email_addresses"][1]["email_address"] = "unscoped@test.local"
    assert client.post("/webhooks/clerk", json=payload).status_code == 200
    new = people.query(Usuario).filter_by(clerk_id="clerk_new").one()
    assert new.rol == "RESIDENTE"
    assert people.query(UserTenantScope).filter_by(usuario_id=new.usuario_id).count() == 0


def test_editar_cuenta_permisos_correo_y_scope(client, people):
    msp = headers("msp", "MSP_ADMIN")
    admin = headers("admin", "ADMIN_CONDOMINIO")
    guard = headers("guard", "GUARDIA")
    url = "/condominios/a1/usuarios/guard"
    body = {"nombre": "Guardia corregido", "email": "corrected@test.local", "rol": "GUARDIA"}
    assert client.patch(url, headers=guard, json=body).status_code == 403
    assert client.patch("/condominios/b1/usuarios/guard", headers=msp, json=body).status_code == 403
    assert client.patch("/condominios/a1/usuarios/missing", headers=msp, json=body).status_code == 404
    saved = client.patch(url, headers=admin, json=body)
    assert saved.status_code == 200, saved.text
    identity = people.query(Usuario).filter_by(usuario_id="guard").one()
    assert identity.nombre == "Guardia corregido" and identity.email == "corrected@test.local"
    assert client.patch(url, headers=admin, json={**body, "rol": "ADMIN_CONDOMINIO"}).status_code == 403
    promoted = client.patch(url, headers=msp, json={**body, "rol": "ADMIN_CONDOMINIO"})
    assert promoted.status_code == 200, promoted.text
    assert identity.rol == "ADMIN_CONDOMINIO"
    scope = people.query(UserTenantScope).filter_by(usuario_id="guard").one()
    assert scope.access_level == AccessLevel.ADMIN_CONDOMINIO
    assert scope.metadata_json["last_edited_by"] == "msp"
    demoted = client.patch(url, headers=msp, json=body)
    assert demoted.status_code == 200
    assert client.post("/condominios/a1/usuarios", headers=headers("guard", "ADMIN_CONDOMINIO"),
                       json={"nombre": "No", "email": "forbidden@test.local", "rol": "GUARDIA"}).status_code == 403
    assert client.patch(url, headers=msp, json={**body, "email": "resident@test.local"}).status_code == 409
    identity.clerk_id = "clerk_guard"
    people.commit()
    assert client.patch(url, headers=msp, json={**body, "email": "another@test.local"}).status_code == 400
    assert identity.email == "corrected@test.local"
    assert client.patch(url, headers=msp, json={**body, "condominio_id": "b1"}).status_code == 422


def test_editar_residente_vivienda_valida_y_rol(client, people):
    from backend.db.core import Casa
    people.add_all([
        Casa(casa_id="home_a", condominio_id="a1", numero="102"),
        Casa(casa_id="home_b", condominio_id="b1", numero="201"),
    ])
    people.commit()
    msp = headers("msp", "MSP_ADMIN")
    admin = headers("admin", "ADMIN_CONDOMINIO")
    url = "/condominios/a1/usuarios/resident"
    body = {"nombre": "Resident updated", "email": "resident@test.local", "rol": "RESIDENTE", "casa_id": "home_a"}
    assert client.patch(url, headers=admin, json={**body, "casa_id": "home_b"}).status_code == 400
    changed = client.patch(url, headers=admin, json=body)
    assert changed.status_code == 200, changed.text
    resident = people.query(Usuario).filter_by(usuario_id="resident").one()
    assert resident.casa_id == "home_a" and resident.casa_unidad == "102"
    guard_url = "/condominios/a1/usuarios/guard"
    guard_body = {**body, "email": "guard@test.local"}
    assert client.patch(guard_url, headers=msp, json=guard_body).status_code == 409
    staff = {**body, "rol": "GUARDIA", "casa_id": None}
    assert client.patch(url, headers=admin, json=staff).status_code == 403
    assert client.patch(url, headers=msp, json=staff).status_code == 200
    assert resident.casa_id is None and resident.casa_unidad is None
    assert people.query(UserTenantScope).filter_by(usuario_id="resident").one().access_level == AccessLevel.GUARDIA
