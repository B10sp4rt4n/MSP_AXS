"""HTTP regression for the actual canary router; SQLite does not certify RLS.

Authentication and GOV/EVENT I/O are isolated deliberately. Scope and modality
authorization run against real synthetic ORM rows through the production guard.
"""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.auth.dependencies import get_current_user
from backend.db.core import (
    AccessLevel, Condominio, MSP, MSPMembership, ScopeStatus,
    UserTenantScope, Usuario, get_core_db,
)
from backend.db.event import get_event_db
from backend.db.gov import Authority, AuthorityType, GovStatus, get_gov_db
from backend.routers import canario_router


@pytest.fixture
def canary_http(db_core_session, db_gov_session, db_event_session, monkeypatch):
    db = db_core_session
    db.add(MSP(msp_id="canary_provider", nombre="Proveedor sintético"))
    db.add_all([
        Condominio(condominio_id="canary_res", msp_id="canary_provider", nombre="Residencial"),
        Condominio(condominio_id="canary_corp", msp_id="canary_provider", nombre="Empresa",
                   modalidad="corporativo", corporativo_habilitado=False),
    ])
    db.add_all([
        Usuario(usuario_id=kind, email=kind + "@example.test",
                rol="RESIDENTE" if kind == "worker" else "MSP_ADMIN")
        for kind in ("worker", "global", "msp")
    ])
    db.flush()
    db.add(MSPMembership(usuario_id="msp", msp_id="canary_provider", estado="activo"))
    db.add_all([
        UserTenantScope(usuario_id=kind, tenant_id=tenant,
                        estado=ScopeStatus.ACTIVO, access_level=AccessLevel.RESIDENTE)
        for kind in ("worker", "global", "msp")
        for tenant in ("canary_res", "canary_corp")
    ])
    db.commit()
    db_gov_session.add(Authority(
        authority_id="canary_global", identity_id="global",
        tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO,
    ))
    db_gov_session.commit()

    actors = {row.usuario_id: row for row in db.query(Usuario).all()}
    current = {"actor": actors["worker"]}
    calls = []

    def allow_policy(**kwargs):
        calls.append(("gov", kwargs))
        return True, "Política sintética permisiva"

    def record_event(**kwargs):
        calls.append(("event", kwargs))
        return SimpleNamespace(id="canary_synthetic_event")

    monkeypatch.setattr(canario_router, "puede_ejecutar_accion", allow_policy)
    monkeypatch.setattr(canario_router, "registrar_evento", record_event)
    app = FastAPI()
    app.include_router(canario_router.router)
    app.dependency_overrides[get_core_db] = lambda: db
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    app.dependency_overrides[get_current_user] = lambda: current["actor"]
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, db=db, actors=actors, current=current, calls=calls)


@pytest.mark.parametrize("actor", ["worker", "global", "msp"])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("api_enabled", ["false", "true"])
def test_canary_rejects_corporate_before_gov_or_operational_event(
    canary_http, monkeypatch, actor, enabled, api_enabled,
):
    case = canary_http
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", api_enabled)
    case.current["actor"] = case.actors[actor]
    company = case.db.query(Condominio).filter_by(condominio_id="canary_corp").one()
    company.corporativo_habilitado = enabled
    case.db.commit()
    response = case.client.post("/qr/generar_gobernado", json={
        "visitante_nombre": "Visitante sintético", "tenant_id": "canary_corp", "dias_vigencia": 2,
    })
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Operacion no disponible para esta modalidad"
    assert case.calls == []


@pytest.mark.parametrize("actor", ["worker", "global", "msp"])
@pytest.mark.parametrize("has_scope", [False, True])
@pytest.mark.parametrize("api_enabled", ["false", "true"])
def test_canary_preserves_residential_scope_requirement(
    canary_http, monkeypatch, actor, has_scope, api_enabled,
):
    case = canary_http
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", api_enabled)
    case.current["actor"] = case.actors[actor]
    if not has_scope:
        scope = case.db.query(UserTenantScope).filter_by(usuario_id=actor, tenant_id="canary_res").one()
        scope.estado = ScopeStatus.REVOCADO
        case.db.commit()
    response = case.client.post("/qr/generar_gobernado", json={
        "visitante_nombre": "Visitante sintético", "tenant_id": "canary_res", "dias_vigencia": 2,
    })
    if not has_scope:
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Sin alcance en este tenant"
        assert case.calls == []
    else:
        assert response.status_code == 200, response.text
        assert response.json()["tenant_id"] == "canary_res"
        assert [kind for kind, _ in case.calls] == ["gov", "event"]


def test_canary_corporate_denial_is_durably_audited_in_main_app(
    canary_http, db_gov_session, db_event_session, monkeypatch,
):
    """Real JWT/middleware path: reject corporate even when fully enabled."""
    from sqlalchemy.orm import sessionmaker
    from backend.core.auth.jwt import create_access_token
    from backend.db.core import EventOutbox, SecurityOutbox
    from backend.db.event.session import get_event_db as canonical_event_db
    from backend.main import app
    from backend.services import security_outbox

    case = canary_http
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    company = case.db.query(Condominio).filter_by(condominio_id="canary_corp").one()
    company.corporativo_habilitado = True
    case.db.commit()
    monkeypatch.setattr(security_outbox, "SessionFactory", sessionmaker(bind=case.db.bind))
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_core_db] = lambda: case.db
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    app.dependency_overrides[canonical_event_db] = lambda: db_event_session
    token = create_access_token("global", "MSP_ADMIN")
    try:
        with TestClient(app) as client:
            response = client.post("/qr/generar_gobernado", json={
                "visitante_nombre": "Visitante privado sintético",
                "tenant_id": "canary_corp", "dias_vigencia": 2,
            }, headers={"Authorization": "Bearer " + token})
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Operacion no disponible para esta modalidad"
        assert case.calls == []
        assert case.db.query(EventOutbox).count() == 0
        rejection = case.db.query(SecurityOutbox).one().payload
        assert rejection["motivo"] == "TENANT_MODE_DENIED"
        assert rejection["identity_id"] == "global"
        assert rejection["metadata_json"]["route"] == "/qr/generar_gobernado"
        for private in ("Visitante privado sintético", "canary_corp", token):
            assert private not in str(rejection)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
