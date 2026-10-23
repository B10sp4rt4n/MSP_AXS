"""C2: operaciones reales de Superadmin con datos sintéticos aislados en SQLite.

La identidad GLOBAL viene de AUP_GOV, no del texto Usuario.rol. El runtime
de CI PostgreSQL se prueba por separado; no hay altas en Neon productivo.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.core.auth.jwt import create_access_token
from backend.db.core import (
    Casa, Condominio, CorporateMembership, CorporateOrganization,
    EventOutbox, MSP, Usuario, get_core_db,
)
from backend.db.gov import Authority, AuthorityType, GovStatus, Policy, PolicyScope, get_gov_db
from backend.db.event import get_event_db
from backend.services import security_outbox
from backend.services.corporate_provisioner_db import get_provisioning_db


@pytest.fixture
def company_setup(db_core_session, db_gov_session, db_event_session, monkeypatch):
    core, gov = db_core_session, db_gov_session
    core.add(MSP(msp_id="msp_synthetic", nombre="Proveedor sintético"))
    core.add_all([
        Usuario(usuario_id="super", email="super@example.test", rol="MSP_ADMIN"),
        Usuario(usuario_id="provider", email="provider@example.test", rol="MSP_ADMIN"),
        Usuario(usuario_id="owner", email="owner@example.test", rol="RESIDENTE"),
    ])
    core.commit()
    gov.add(Authority(authority_id="authority_super", identity_id="super",
                      tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
    gov.commit()
    prev = app.dependency_overrides.copy()
    app.dependency_overrides[get_core_db] = lambda: core
    app.dependency_overrides[get_gov_db] = lambda: gov
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    app.dependency_overrides[get_provisioning_db] = lambda: core
    monkeypatch.setattr(security_outbox, "SessionFactory", sessionmaker(bind=core.bind))
    body = {
        "request_id": str(uuid.uuid4()),
        "nombre": "Empresa Sintética Uno",
        "msp_id": "msp_synthetic",
        "owner_user_id": "owner",
        "privacy_contact": "privacidad@example.test",
        "privacy_notice_url": "https://example.test/aviso",
        "privacy_notice_version": "2026-10",
    }
    def auth(identity):
        return {"Authorization": "Bearer " + create_access_token(identity, "MSP_ADMIN")}
    try:
        with TestClient(app) as client:
            yield client, core, gov, body, auth
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prev)


def test_off_by_default_returns_404(company_setup, monkeypatch):
    client, core, gov, body, auth = company_setup
    monkeypatch.delenv("AXS_CORPORATE_PROVISIONING_ENABLED", raising=False)
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    resp = client.post("/plataforma/corporativo/empresas", headers=auth("super"), json=body)
    assert resp.status_code == 404
    assert core.query(CorporateOrganization).count() == 0


def test_global_only_idempotent_bootstrap_and_staged_activation(company_setup, monkeypatch):
    client, core, gov, body, auth = company_setup
    monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "true")
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    path = "/plataforma/corporativo/empresas"

    denied = client.post(path, headers=auth("provider"), json=body)
    assert denied.status_code == 403
    assert core.query(Condominio).count() == 0
    bad_email = client.post(path, headers=auth("super"), json={**body, "privacy_contact": "not_an_email"})
    assert bad_email.status_code == 422
    bad_notice = client.post(path, headers=auth("super"),
                             json={**body, "privacy_notice_url": "http://example.test/aviso"})
    assert bad_notice.status_code == 422
    self_grant = client.post(path, headers=auth("super"), json={**body, "owner_user_id": "super"})
    assert self_grant.status_code == 400
    assert core.query(Condominio).count() == 0

    assert client.get("/plataforma/corporativo/usuarios/owner", headers=auth("provider")).status_code == 403
    verified_owner = client.get("/plataforma/corporativo/usuarios/owner", headers=auth("super"))
    assert verified_owner.status_code == 200
    assert verified_owner.headers["cache-control"] == "private, no-store"
    assert verified_owner.json()["usuario_id"] == "owner"
    assert client.get("/plataforma/corporativo/usuarios/missing", headers=auth("super")).status_code == 404

    first = client.post(path, headers=auth("super"), json=body)
    assert first.status_code == 201, first.text
    company = first.json()
    tenant = company["tenant_id"]
    assert tenant.startswith("corp_")
    assert client.get(path + "/" + tenant, headers=auth("provider")).status_code == 403
    assert client.get(path + "/corp_invalid", headers=auth("super")).status_code == 404
    initial = client.get(path + "/" + tenant, headers=auth("super"))
    assert initial.status_code == 200
    assert initial.headers["cache-control"] == "private, no-store"
    assert initial.json()["capacidades"] == {"max_sedes": None, "max_destinos_por_sede": None}
    assert client.get(path + "/" + tenant, headers=auth("super")).json()["owner_user_id"] == "owner"
    assert company["directorio_habilitado"] is False
    assert company["owner_user_id"] == "owner"
    assert core.query(Casa).count() == 0
    assert core.query(CorporateMembership).filter_by(tenant_id=tenant, rol="owner").count() == 1
    replay = client.post(path, headers=auth("super"), json=body)
    assert replay.status_code == 201, replay.text
    assert replay.json()["tenant_id"] == tenant
    assert core.query(EventOutbox).count() == 1
    conflict = client.post(path, headers=auth("super"), json={**body, "nombre": "Otra empresa"})
    assert conflict.status_code == 409

    activate_path = f"{path}/{tenant}/habilitar-directorio"
    premature = client.post(activate_path, headers=auth("super"), json={"confirmacion": True})
    assert premature.status_code == 409
    assert core.query(Condominio).filter_by(condominio_id=tenant).one().corporativo_habilitado is False
    denied_activation = client.post(activate_path, headers=auth("provider"), json={"confirmacion": True})
    assert denied_activation.status_code == 403
    assert client.post(activate_path, headers=auth("super"), json={"confirmacion": False}).status_code == 422

    limits_path = f"{path}/{tenant}/capacidades"
    limits = {"max_sedes": 2, "max_destinos_por_sede": 10}
    assert client.put(limits_path, headers=auth("provider"), json=limits).status_code == 403
    assert client.put(limits_path, headers=auth("super"),
                      json={"max_sedes": 0, "max_destinos_por_sede": 10}).status_code == 422
    config = client.put(limits_path, headers=auth("super"), json=limits)
    assert config.status_code == 200, config.text
    assert config.json()["max_sedes"] == 2
    assert client.put(limits_path, headers=auth("super"), json=limits).status_code == 200
    assert gov.query(Policy).filter_by(target_tenant_id=tenant).count() == 2
    refreshed = client.get(path + "/" + tenant, headers=auth("super"))
    assert refreshed.status_code == 200
    assert refreshed.json()["capacidades"] == limits
    active = client.post(activate_path, headers=auth("super"), json={"confirmacion": True})
    assert active.status_code == 200, active.text
    assert active.json()["directorio_habilitado"] is True
    same = client.post(activate_path, headers=auth("super"), json={"confirmacion": True})
    assert same.status_code == 200
    # 1 alta, 2 eventos de capacidades (solicitud/confirmación), 1 activación.
    assert core.query(EventOutbox).count() == 4
    # AXS residencial sigue separado, sin falsificar viviendas.
    assert client.get("/condominios/", headers=auth("super")).json() == []


def test_privileged_connection_is_fail_closed_without_url(monkeypatch):
    from backend.services.corporate_provisioner_db import get_provisioning_db
    from fastapi import HTTPException
    monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "true")
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    monkeypatch.delenv("DATABASE_CORPORATE_PROVISIONING_URL", raising=False)
    with pytest.raises(HTTPException) as error:
        next(get_provisioning_db())
    assert error.value.status_code == 503


def test_global_access_probe_does_not_depend_on_msp_role(company_setup, monkeypatch):
    """La consola solo se muestra con autoridad GLOBAL vigente, no por rol."""
    client, core, gov, body, auth = company_setup
    monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "true")
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    route = "/plataforma/corporativo/acceso"
    assert client.get(route, headers=auth("provider")).status_code == 403
    granted = client.get(route, headers=auth("super"))
    assert granted.status_code == 200
    assert granted.json()["authorized"] is True
    assert granted.json()["provisioning_enabled"] is True
    assert granted.json()["credencial_configurada"] is False
    assert granted.headers["cache-control"] == "private, no-store"
    monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "false")
    assert client.get(route, headers=auth("super")).status_code == 404

def _audit_corporate_quota_setup(company_setup, monkeypatch):
    client, core, gov, body, auth = company_setup
    monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "true")
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    created = client.post("/plataforma/corporativo/empresas", headers=auth("super"), json=body)
    assert created.status_code == 201, created.text
    tenant = created.json()["tenant_id"]
    base = "/plataforma/corporativo/empresas/" + tenant
    limits = {"max_sedes": 2, "max_destinos_por_sede": 10}
    return client, core, gov, auth, tenant, base, limits


@pytest.mark.parametrize("invalid_window", ["expired", "future"])
def test_quota_same_values_repair_invalid_validity_window(company_setup, monkeypatch, invalid_window):
    from datetime import datetime, timedelta

    client, core, gov, auth, tenant, base, limits = _audit_corporate_quota_setup(company_setup, monkeypatch)
    assert client.put(base + "/capacidades", headers=auth("super"), json=limits).status_code == 200
    now = datetime.utcnow()
    for policy in gov.query(Policy).filter_by(target_tenant_id=tenant).all():
        if invalid_window == "expired":
            policy.valida_hasta = now - timedelta(days=1)
        else:
            policy.valida_desde = now + timedelta(days=1)
    gov.commit()

    result = client.put(base + "/capacidades", headers=auth("super"), json=limits)
    assert result.status_code == 200, result.text
    for policy in gov.query(Policy).filter_by(target_tenant_id=tenant).all():
        assert policy.valida_desde <= datetime.utcnow()
        assert policy.valida_hasta is None or policy.valida_hasta >= datetime.utcnow()
    enabled = client.post(base + "/habilitar-directorio", headers=auth("super"), json={"confirmacion": True})
    assert enabled.status_code == 200, enabled.text


@pytest.mark.parametrize("invalid_window", ["expired", "future"])
def test_quota_status_does_not_present_ineffective_policy_as_current(company_setup, monkeypatch, invalid_window):
    from datetime import datetime, timedelta

    client, core, gov, auth, tenant, base, limits = _audit_corporate_quota_setup(company_setup, monkeypatch)
    assert client.put(base + "/capacidades", headers=auth("super"), json=limits).status_code == 200
    now = datetime.utcnow()
    for policy in gov.query(Policy).filter_by(target_tenant_id=tenant).all():
        if invalid_window == "expired":
            policy.valida_hasta = now - timedelta(days=1)
        else:
            policy.valida_desde = now + timedelta(days=1)
    gov.commit()

    status = client.get(base, headers=auth("super"))
    assert status.status_code == 200, status.text
    assert status.json()["capacidades"] == {"max_sedes": None, "max_destinos_por_sede": None}
