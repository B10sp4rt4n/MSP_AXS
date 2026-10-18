"""Synthetic identity lifecycle and real scope authorization; no external calls."""
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.db.core import Usuario, Condominio, get_core_db
from backend.db.core.models import ExternalIdentity, UserTenantScope, AccessLevel, ScopeStatus
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.validator import validar_scope
from backend.routers.identity_router import router


@pytest.fixture
def identity_api(db_core_session):
    db = db_core_session
    owner = Usuario(usuario_id="person", clerk_id="clerk-one", email="one@example.test", rol="RESIDENTE")
    other = Usuario(usuario_id="other", email="other@example.test", rol="RESIDENTE")
    db.add_all([owner, other, *[Condominio(condominio_id=t, nombre=t) for t in ("a", "b", "c")]])
    db.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_core_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    with TestClient(app) as client:
        yield client, db, owner, other, app


def put(client, provider="facebook", reference="https://facebook.com/person"):
    return client.put(f"/auth/me/identity/external/{provider}", json={"reference": reference, "consent": True})


def test_optional_existing_identity_and_private_response(identity_api):
    client, db, owner, other, app = identity_api
    response = client.get("/auth/me/identity")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["celular"] is None
    assert response.json()["identities"] == []
    assert "clerk_id" not in response.json()
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/auth/me/identity").status_code == 401
    assert put(client).status_code == 401
    assert client.delete("/auth/me/identity/external/facebook").status_code == 401
    assert client.patch("/auth/me/identity", json={"celular": None}).status_code == 401


def test_multiple_communities_same_identity_no_added_permissions(identity_api):
    client, db, owner, *_ = identity_api
    for tenant in ("a", "b"):
        db.add(UserTenantScope(usuario_id=owner.usuario_id, tenant_id=tenant,
                               access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO))
    db.commit()
    assert put(client).status_code == 200
    assert db.query(Usuario).filter_by(usuario_id="person").count() == 1
    assert db.query(UserTenantScope).count() == 2
    for tenant in ("a", "b"):
        assert validar_scope(db, owner, tenant, AccessLevel.RESIDENTE)
        assert not validar_scope(db, owner, tenant, AccessLevel.ADMIN_CONDOMINIO)
    assert not validar_scope(db, owner, "c", AccessLevel.RESIDENTE)
    scope = db.query(UserTenantScope).filter_by(tenant_id="a").one()
    scope.estado = ScopeStatus.REVOCADO
    db.commit()
    assert put(client, "instagram", "https://instagram.com/person").status_code == 200
    assert not validar_scope(db, owner, "a", AccessLevel.RESIDENTE)
    assert validar_scope(db, owner, "b", AccessLevel.RESIDENTE)
    assert owner.rol == "RESIDENTE" and owner.clerk_id == "clerk-one"


def test_change_revocation_reconsent_and_idempotence(identity_api):
    client, db, owner, *_ = identity_api
    assert put(client).status_code == 200
    row = db.query(ExternalIdentity).one()
    identity_id, consent_at = row.identity_id, row.consent_at
    put(client)
    assert row.consent_at == consent_at
    row.verified_at = datetime.utcnow()
    row.verification_method = "synthetic-proof"
    db.commit()
    result = put(client, reference="https://www.facebook.com/changed/")
    assert result.json()["identities"][0]["verified_at"] is None
    assert row.reference == "https://facebook.com/changed"
    assert row.verification_method is None
    response = client.delete("/auth/me/identity/external/facebook")
    assert response.status_code == 200
    assert row.revoked_at and row.reference is None
    revoked_at = row.revoked_at
    client.delete("/auth/me/identity/external/facebook")
    assert row.revoked_at == revoked_at
    put(client)
    assert row.revoked_at is None and row.verified_at is None
    assert row.identity_id == identity_id
    assert db.query(ExternalIdentity).count() == 1


def test_phone_verification_independent_from_whatsapp(identity_api):
    client, db, owner, *_ = identity_api
    assert client.patch("/auth/me/identity", json={"celular": "+525512345678"}).status_code == 422
    assert client.patch("/auth/me/identity", json={"celular": "+525512345678", "consent": True}).status_code == 200
    owner.celular_verified_at = datetime.utcnow()
    db.commit()
    assert put(client, "whatsapp", "+525587654321").status_code == 200
    row = db.query(ExternalIdentity).one()
    assert row.verified_at is None
    row.verified_at = datetime.utcnow(); row.verification_method = "synthetic-proof"
    db.commit()
    client.patch("/auth/me/identity", json={"celular": "+525511111111", "consent": True})
    assert owner.celular_verified_at is None and row.verified_at is not None
    client.patch("/auth/me/identity", json={"celular": None})
    assert owner.celular is None and owner.celular_consent_at is None
    assert row.reference == "+525587654321"


def test_self_service_cannot_read_or_modify_other_identity(identity_api):
    client, db, owner, other, app = identity_api
    put(client)
    app.dependency_overrides[get_current_user] = lambda: other
    assert client.get("/auth/me/identity").json()["identities"] == []
    client.delete("/auth/me/identity/external/facebook")
    assert db.query(ExternalIdentity).one().revoked_at is None
    # A public, unverified reference cannot reserve another person's account.
    assert put(client).status_code == 200
    assert db.query(ExternalIdentity).count() == 2
    assert db.query(UserTenantScope).count() == 0


@pytest.mark.parametrize("extra", [{"verified_at": "2026-01-01"}, {"usuario_id": "other"}, {"rol": "MSP_ADMIN"}, {"tenant_id": "c"}])
def test_reject_privilege_and_verification_injection(identity_api, extra):
    client, *_ = identity_api
    assert client.put("/auth/me/identity/external/facebook", json={"reference": "https://facebook.com/person", "consent": True, **extra}).status_code == 422
    assert client.patch("/auth/me/identity", json={"celular": "+525512345678", "consent": True, **extra}).status_code == 422


@pytest.mark.parametrize("reference", ["https://facebook.com.evil.test/person", "javascript:alert(1)", "https://facebook.com/person?token=secret", "https://facebook.com@evil.test/person", "https://facebook.com/", "https://facebook.com/person#token", "https://facebook.com:bad/person"])
def test_reject_invalid_references(identity_api, reference):
    assert put(identity_api[0], reference=reference).status_code == 422


def test_missing_consent_and_provider_validation(identity_api):
    client, *_ = identity_api
    for consent in (False, None):
        assert client.put("/auth/me/identity/external/instagram", json={"reference": "https://instagram.com/person", "consent": consent}).status_code == 422
    assert put(client, "amazon").status_code == 422
    assert put(client, "whatsapp", "5512345678").status_code == 422
