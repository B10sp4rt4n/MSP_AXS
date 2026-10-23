"""Regresión C0 sintética: modo de tenant aislado. SQLite NO prueba RLS real."""
import pytest
from fastapi import HTTPException

from backend.core.scope.msp_boundary import (
    authorized_tenant_context, require_condominio,
)
from backend.db.core import (
    AccessLevel, Condominio, MSP, MSPMembership, ScopeStatus,
    UserTenantScope, Usuario,
)
from backend.db.gov import Authority, AuthorityType, GovStatus
from backend.routers.condominios_router import list_condominios


@pytest.fixture
def modes(db_core_session, db_gov_session):
    db = db_core_session
    db.add(MSP(msp_id="provider", nombre="Proveedor sintético"))
    db.add_all([
        Condominio(condominio_id="res", msp_id="provider", nombre="Residencial"),
        Condominio(condominio_id="corp", msp_id="provider", nombre="Empresa",
                   modalidad="corporativo", corporativo_habilitado=False),
    ])
    db.add_all([
        Usuario(usuario_id="global", email="global@example.test", rol="MSP_ADMIN"),
        Usuario(usuario_id="msp", email="msp@example.test", rol="MSP_ADMIN"),
        Usuario(usuario_id="worker", email="worker@example.test", rol="GUARDIA",
                condominio_id="corp"),
        Usuario(usuario_id="outsider", email="outsider@example.test", rol="GUARDIA"),
    ])
    db.flush()
    db.add(MSPMembership(usuario_id="msp", msp_id="provider"))
    db.add(UserTenantScope(usuario_id="worker", tenant_id="corp",
                           estado=ScopeStatus.ACTIVO, access_level=AccessLevel.GUARDIA))
    db.commit()
    db_gov_session.add(Authority(authority_id="global-c0", identity_id="global",
                                 tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    return {u.usuario_id: u for u in db.query(Usuario).all()}


def expect_denied(call):
    with pytest.raises(HTTPException) as exc:
        call()
    assert exc.value.status_code == 403


def test_existing_tenants_default_residential(modes, db_core_session):
    resident = db_core_session.query(Condominio).filter_by(condominio_id="res").one()
    assert resident.modalidad == "residencial"
    assert resident.corporativo_habilitado is False


@pytest.mark.parametrize("actor", ["global", "msp", "worker"])
def test_residential_boundary_rejects_corporate_even_with_valid_scope(
    modes, db_core_session, db_gov_session, actor,
):
    expect_denied(lambda: require_condominio(
        db_core_session, db_gov_session, modes[actor], "corp", AccessLevel.GUARDIA,
    ))
    require_condominio(db_core_session, db_gov_session, modes["global"],
                       "res", AccessLevel.GUARDIA)


def test_disabled_corporate_is_not_operable_even_for_global(
    modes, db_core_session, db_gov_session,
):
    expect_denied(lambda: require_condominio(
        db_core_session, db_gov_session, modes["global"], "corp",
        AccessLevel.ADMIN_CONDOMINIO, expected_mode="corporativo",
    ))
    # Una autorización transversal NO omite validación de identidad / scope.
    expect_denied(lambda: require_condominio(
        db_core_session, db_gov_session, modes["outsider"], "corp",
        AccessLevel.GUARDIA, expected_mode=None,
    ))
    # ARCO conserva un camino transversal únicamente para un actor autorizado;
    # el expediente además exige designación expresa en su router.
    assert require_condominio(
        db_core_session, db_gov_session, modes["worker"], "corp",
        AccessLevel.GUARDIA, expected_mode=None,
    ).condominio_id == "corp"


def test_explicit_corporate_enablement_does_not_grant_other_tenants(
    modes, db_core_session, db_gov_session,
):
    db = db_core_session
    corp = db.query(Condominio).filter_by(condominio_id="corp").one()
    corp.corporativo_habilitado = True
    db.commit()
    assert require_condominio(
        db, db_gov_session, modes["worker"], "corp", AccessLevel.GUARDIA,
        expected_mode="corporativo",
    ).modalidad == "corporativo"
    expect_denied(lambda: require_condominio(
        db, db_gov_session, modes["outsider"], "corp", AccessLevel.GUARDIA,
        expected_mode="corporativo",
    ))
    expect_denied(lambda: require_condominio(
        db, db_gov_session, modes["worker"], "res", AccessLevel.GUARDIA,
        expected_mode="residencial",
    ))


def test_residential_list_never_exposes_corporate(
    modes, db_core_session, db_gov_session,
):
    db = db_core_session
    gov = db_gov_session
    for actor in ("global", "msp"):
        ids = {c.condominio_id for c in list_condominios(None, db, gov, modes[actor])}
        assert ids == {"res"}
    assert list_condominios(None, db, gov, modes["worker"]) == []


def test_dependency_rejects_mode_before_setting_rls(
    modes, db_core_session, db_gov_session, monkeypatch,
):
    from backend.core.tenant import context
    calls = []
    monkeypatch.setattr(context, "_set_postgres_tenant", lambda *args: calls.append(args))
    residential = authorized_tenant_context(AccessLevel.GUARDIA)
    expect_denied(lambda: residential(
        "corp", db_core_session, db_gov_session, modes["worker"],
    ))
    assert calls == []
    corporate = authorized_tenant_context(AccessLevel.GUARDIA, expected_mode="corporativo")
    expect_denied(lambda: corporate(
        "corp", db_core_session, db_gov_session, modes["global"],
    ))
    assert calls == []


def test_http_residential_api_rejects_corporate(
    modes, db_core_session, db_gov_session, db_event_session,
):
    """Prueba de API con sesión real de test; no constituye prueba RLS PostgreSQL."""
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.db.core import get_core_db
    from backend.db.gov import get_gov_db
    from backend.db.event import get_event_db
    from backend.core.auth.jwt import create_access_token

    app.dependency_overrides[get_core_db] = lambda: db_core_session
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    headers = {"Authorization": f"Bearer {create_access_token('global', 'MSP_ADMIN')}"}
    try:
        with TestClient(app) as client:
            response = client.get("/visitas/condominio/corp", headers=headers)
            assert response.status_code == 403
            assert response.json()["detail"] == "Operacion no disponible para esta modalidad"
            visible = client.get("/condominios/", headers=headers)
            assert visible.status_code == 200, visible.text
            assert {row["condominio_id"] for row in visible.json()} == {"res"}
    finally:
        app.dependency_overrides.clear()
