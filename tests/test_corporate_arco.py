"""Privacy authority is explicit and independent of residential/business roles."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from backend.core.auth.jwt import create_access_token
from backend.db.core import (
    AccessLevel, Condominio, CorporateMembership, CorporateOrganization, EventOutbox,
    MSP, MSPMembership, ScopeStatus, UserTenantScope, Usuario,
)
from backend.db.gov import Authority, AuthorityType, GovStatus

TENANT = "arco-corp"


def headers(actor):
    role = "MSP_ADMIN" if actor in {"msp", "global"} else "ADMIN_CONDOMINIO" if actor == "scoped" else "GUARDIA"
    return {"Authorization": "Bearer " + create_access_token("privacy-" + actor, role)}


def body():
    now = datetime.now(timezone.utc)
    return {"request_id": str(uuid4()), "received_at": (now-timedelta(minutes=1)).isoformat(),
            "determination_due": (now+timedelta(days=20)).isoformat(), "right": "acceso",
            "subject_ref": "PRIVATE_SUBJECT_SENTINEL", "owner_id": "PRIVATE_OWNER_SENTINEL"}


@pytest.fixture
def privacy_company(db_session, db_gov_session, monkeypatch):
    db = db_session
    if db.get_bind().dialect.name == "sqlite":
        db.execute(text("PRAGMA foreign_keys=ON"))
    db.add(MSP(msp_id="privacy-provider", nombre="Synthetic"))
    db.flush()
    db.add_all([Condominio(condominio_id=t, msp_id="privacy-provider", nombre="Synthetic",
                          modalidad="corporativo", corporativo_habilitado=False)
                for t in (TENANT, "arco-other")])
    db.flush()
    db.add_all([CorporateOrganization(tenant_id=t) for t in (TENANT, "arco-other")])
    db.flush()
    for actor in ("owner", "admin", "host", "reception", "scoped", "msp", "global", "outsider"):
        role = "MSP_ADMIN" if actor in {"msp", "global"} else "ADMIN_CONDOMINIO" if actor == "scoped" else "GUARDIA"
        db.add(Usuario(usuario_id="privacy-"+actor, email=actor+"@example.test", rol=role))
    db.flush()
    for actor in ("owner", "admin", "host", "reception"):
        db.add(CorporateMembership(membership_id="member-"+actor, tenant_id=TENANT,
                                  user_id="privacy-"+actor, rol=actor, estado="activo"))
    db.add(CorporateMembership(membership_id="member-other", tenant_id="arco-other",
                              user_id="privacy-outsider", rol="owner", estado="activo"))
    db.add(UserTenantScope(usuario_id="privacy-scoped", tenant_id=TENANT,
                           access_level=AccessLevel.ADMIN_CONDOMINIO, estado=ScopeStatus.ACTIVO))
    db.add(MSPMembership(usuario_id="privacy-msp", msp_id="privacy-provider"))
    db.commit()
    db_gov_session.add(Authority(authority_id="privacy-global", identity_id="privacy-global",
                                 tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    monkeypatch.setenv("AXS_ARCO_CASES_ENABLED", "true")
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "false")
    monkeypatch.setenv("AXS_ARCO_OPERATORS", ",".join("privacy-"+a+":"+TENANT
        for a in ("owner", "admin", "host", "reception", "scoped", "msp", "global", "outsider")))
    return db


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("actor", ["owner", "admin"])
def test_designated_corporate_operator_does_not_need_residential_scope(
    client, privacy_company, actor, enabled,
):
    db = privacy_company
    db.query(Condominio).filter_by(condominio_id=TENANT).one().corporativo_habilitado = enabled
    db.commit()
    payload = body()
    response = client.post("/arco/"+TENANT, headers=headers(actor), json=payload)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert client.get("/arco/"+TENANT, headers=headers(actor)).status_code == 200
    response = client.post("/arco/"+TENANT+"/"+payload["request_id"]+"/estado", headers=headers(actor),
                           json={"version": 1, "state": "verificada", "reference": "SYNTHETIC_VERIFICATION"})
    assert response.status_code == 200 and response.json()["state"] == "verificada"
    assert db.query(UserTenantScope).filter_by(usuario_id="privacy-"+actor).count() == 0
    assert "PRIVATE_" not in str([row.payload for row in db.query(EventOutbox)])


@pytest.mark.parametrize("actor", ["host", "reception", "scoped", "msp", "outsider"])
def test_designation_never_substitutes_corporate_membership_and_privacy_role(client, privacy_company, actor):
    response = client.get("/arco/"+TENANT, headers=headers(actor))
    assert response.status_code == 403, response.text
    response = client.post("/arco/"+TENANT, headers=headers(actor), json=body())
    assert response.status_code == 403, response.text
    assert privacy_company.query(EventOutbox).count() == 0


@pytest.mark.parametrize("actor", ["owner", "global"])
def test_designation_is_required_even_for_owner_or_global(client, privacy_company, monkeypatch, actor):
    monkeypatch.setenv("AXS_ARCO_OPERATORS", "")
    assert client.get("/arco/"+TENANT, headers=headers(actor)).status_code == 403


def test_revocation_is_effective_for_same_token_and_disabled_company(client, privacy_company):
    h = headers("owner")
    payload = body()
    assert client.post("/arco/"+TENANT, headers=h, json=payload).status_code == 200
    privacy_company.query(CorporateMembership).filter_by(membership_id="member-owner").one().estado = "revocado"
    privacy_company.commit()
    assert client.get("/arco/"+TENANT, headers=h).status_code == 403
    assert client.post("/arco/"+TENANT+"/"+payload["request_id"]+"/estado", headers=h,
                       json={"version": 1, "state": "verificada", "reference": "SYNTHETIC"}).status_code == 403


def test_designated_global_is_transversal_but_msp_alone_is_not(client, privacy_company):
    assert client.get("/arco/"+TENANT, headers=headers("global")).status_code == 200
    assert client.get("/arco/"+TENANT, headers=headers("msp")).status_code == 403


@pytest.mark.parametrize("actor", ["owner", "admin", "global"])
def test_selector_only_returns_designated_and_currently_authorized_clients(client, privacy_company, actor):
    response = client.get("/arco-clientes", headers=headers(actor))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json() == [{"tenant_id": TENANT, "nombre": "Synthetic", "modalidad": "corporativo"}]
    assert "privacy-" not in response.text and "example.test" not in response.text


@pytest.mark.parametrize("actor", ["host", "reception", "scoped", "msp", "outsider"])
def test_selector_does_not_reveal_clients_from_designation_alone(client, privacy_company, actor):
    assert client.get("/arco-clientes", headers=headers(actor)).json() == []


def test_selector_rechecks_designation_membership_and_exact_identity(client, privacy_company, monkeypatch):
    h = headers("owner")
    assert client.get("/arco-clientes", headers=h).json()
    privacy_company.query(CorporateMembership).filter_by(membership_id="member-owner").one().estado = "revocado"
    privacy_company.commit()
    assert client.get("/arco-clientes", headers=h).json() == []
    monkeypatch.setenv("AXS_ARCO_OPERATORS", "privacy-owner-other:"+TENANT)
    assert client.get("/arco-clientes", headers=h).json() == []
    assert client.get("/arco-clientes").status_code == 401
    monkeypatch.setenv("AXS_ARCO_CASES_ENABLED", "false")
    assert client.get("/arco-clientes", headers=h).status_code == 404
