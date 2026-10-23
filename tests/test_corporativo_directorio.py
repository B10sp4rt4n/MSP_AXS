"""C1: permisos y directorio corporativo; SQLite sintetico no sustituye PostgreSQL RLS."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from backend.db.core import (
    Condominio, CorporateOrganization, CorporateSite, CorporateDestination,
    CorporateMembership, CorporateSiteAssignment, EventOutbox, MSP, Usuario,
)
from backend.core.scope.corporate_boundary import require_corporate_member


@pytest.fixture
def corp(db_core_session):
    db = db_core_session
    db.add(MSP(msp_id="provider", nombre="MSP sintético"))
    db.add_all([
        Condominio(condominio_id="res", msp_id="provider", nombre="Residencial"),
        Condominio(condominio_id="ca", msp_id="provider", nombre="Corporativo A",
                   modalidad="corporativo", corporativo_habilitado=True),
        Condominio(condominio_id="cb", msp_id="provider", nombre="Corporativo B",
                   modalidad="corporativo", corporativo_habilitado=True),
    ])
    db.flush()
    db.add_all([CorporateOrganization(tenant_id=x) for x in ("ca", "cb")])
    db.add_all([
        Usuario(usuario_id=user, nombre=user, email=user + "@example.test", rol="RESIDENTE")
        for user in ("owner_a", "owner_b", "host_a", "reception_a", "outsider")
    ])
    db.flush()
    db.add_all([
        CorporateMembership(membership_id="m_" + user, tenant_id=tenant, user_id=user, rol=role)
        for user, tenant, role in (
            ("owner_a", "ca", "owner"), ("owner_b", "cb", "owner"),
            ("host_a", "ca", "host"), ("reception_a", "ca", "reception"),
        )
    ])
    db.add_all([
        CorporateSite(site_id="site_a", tenant_id="ca", nombre="Planta A",
                      zona_horaria="America/Mexico_City"),
        CorporateSite(site_id="site_b", tenant_id="ca", nombre="Planta B",
                      zona_horaria="America/Mexico_City"),
        CorporateSite(site_id="site_other", tenant_id="cb", nombre="Sede de otra empresa",
                      zona_horaria="America/Mexico_City"),
    ])
    db.flush()
    db.add_all([
        CorporateSiteAssignment(assignment_id="assign_host_a", tenant_id="ca",
                                site_id="site_a", user_id="host_a"),
        CorporateSiteAssignment(assignment_id="assign_rec_a", tenant_id="ca",
                                site_id="site_b", user_id="reception_a"),
    ])
    db.add_all([
        CorporateDestination(destination_id="area_a", tenant_id="ca",
                             site_id="site_a", nombre="Recepción A"),
        CorporateDestination(destination_id="area_other", tenant_id="cb",
                             site_id="site_other", nombre="Área B"),
    ])
    db.commit()
    return {u.usuario_id: u for u in db.query(Usuario).all()}


def denied(call, status=403):
    with pytest.raises(HTTPException) as exc:
        call()
    assert exc.value.status_code == status


def test_member_isolated_without_residential_role(corp, db_core_session):
    db = db_core_session
    assert require_corporate_member(db, corp["host_a"], "ca", site_id="site_a").rol == "host"
    denied(lambda: require_corporate_member(db, corp["host_a"], "ca", site_id="site_b"))
    denied(lambda: require_corporate_member(db, corp["owner_a"], "cb"))
    denied(lambda: require_corporate_member(db, corp["outsider"], "ca"))
    denied(lambda: require_corporate_member(db, corp["owner_a"], "res"))
    member = db.query(CorporateMembership).filter_by(user_id="host_a").one()
    member.estado = "revocado"
    db.commit()
    denied(lambda: require_corporate_member(db, corp["host_a"], "ca", site_id="site_a"))


def test_disabled_company_is_not_operable(corp, db_core_session):
    db = db_core_session
    target = db.query(Condominio).filter_by(condominio_id="ca").one()
    target.corporativo_habilitado = False
    db.commit()
    denied(lambda: require_corporate_member(db, corp["owner_a"], "ca"))


def test_http_corporate_directory_enforces_membership_and_site(
    corp, db_core_session, db_gov_session, db_event_session, monkeypatch,
):
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.db.core import get_core_db, SecurityOutbox
    from backend.db.gov import get_gov_db
    from backend.db.event import get_event_db
    from backend.core.auth.jwt import create_access_token
    from backend.services import security_outbox

    from backend.db.gov import Policy, PolicyScope, GovStatus
    db_gov_session.add_all([
        Policy(policy_id="corp_site_limit", nombre="Sedes corporativas",
               ambito=PolicyScope.TENANT, target_tenant_id="ca",
               accion_objetivo="crear_sede_corporativa", limites={"max_count": 3},
               estado=GovStatus.ACTIVO),
        Policy(policy_id="corp_destination_limit", nombre="Destinos corporativos",
               ambito=PolicyScope.TENANT, target_tenant_id="ca",
               accion_objetivo="crear_destino_corporativo", limites={"max_count": 5},
               estado=GovStatus.ACTIVO),
    ])
    db_gov_session.commit()
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    monkeypatch.setattr(security_outbox, "SessionFactory", sessionmaker(bind=db_core_session.bind))
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_core_db] = lambda: db_core_session
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    def auth(user):
        return {"Authorization": "Bearer " + create_access_token(user, "RESIDENTE")}
    try:
        with TestClient(app) as client:
            root = "/corporativo/ca"
            assert client.get(root + "/sedes", headers=auth("outsider")).status_code == 403
            host = client.get(root + "/sedes", headers=auth("host_a"))
            assert host.status_code == 200, host.text
            assert {r["site_id"] for r in host.json()} == {"site_a"}
            assert client.get(root + "/sedes", headers=auth("reception_a")).json()[0]["site_id"] == "site_b"
            assert client.get(root + "/sedes/site_b/destinos", headers=auth("host_a")).status_code == 403
            assert client.get(root + "/sedes/site_a/destinos", headers=auth("host_a")).json()[0]["destination_id"] == "area_a"
            assert client.post(root + "/sedes", headers=auth("host_a"),
                               json={"nombre": "Sede prohibida"}).status_code == 403
            assert client.post("/corporativo/cb/sedes", headers=auth("owner_a"),
                               json={"nombre": "Empresa ajena"}).status_code == 403
            assert client.get("/corporativo/cb/sedes/site_other/destinos",
                              headers=auth("owner_a")).status_code == 403
            assert client.post(root + "/sedes", headers=auth("owner_a"),
                               json={"nombre": "Inválido", "zona_horaria": "Mars/Olympus_Mons"}).status_code == 422
            created = client.post(root + "/sedes", headers=auth("owner_a"),
                                  json={"nombre": "Oficinas Norte", "zona_horaria": "America/Mexico_City"})
            assert created.status_code == 201, created.text
            site = created.json()["site_id"]
            assert created.json()["tenant_id"] == "ca"
            assert "casa_id" not in created.json()
            area = client.post(root + f"/sedes/{site}/destinos", headers=auth("owner_a"),
                               json={"nombre": "Sala de juntas"})
            assert area.status_code == 201, area.text
            assert area.json()["site_id"] == site
            # No se rebasan los límites comerciales: 2 sedes iniciales + 1 nueva.
            over_limit = client.post(root + "/sedes", headers=auth("owner_a"),
                                     json={"nombre": "Sede adicional"})
            assert over_limit.status_code == 403
            assert len(db_core_session.query(CorporateSite).filter_by(tenant_id="ca").all()) == 3
            assert len(db_core_session.query(EventOutbox).all()) == 2
            assert all(r.condominio_id == "ca" for r in db_core_session.query(EventOutbox).all())
            # Las denegaciones se auditan fuera de la transacción operativa.
            reasons = {r.payload["motivo"] for r in db_core_session.query(SecurityOutbox).all()}
            assert {"SCOPE_DENIED", "ROLE_DENIED", "CORPORATE_DISABLED"} <= reasons
            assert db_core_session.query(CorporateDestination).filter_by(tenant_id="cb").count() == 1
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_feature_flag_default_off(corp, db_core_session, db_gov_session, db_event_session, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.db.core import get_core_db
    from backend.db.gov import get_gov_db
    from backend.db.event import get_event_db
    from backend.core.auth.jwt import create_access_token
    monkeypatch.delenv("AXS_CORPORATE_API_ENABLED", raising=False)
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_core_db] = lambda: db_core_session
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    try:
        with TestClient(app) as client:
            response = client.get("/corporativo/ca/sedes", headers={
                "Authorization": "Bearer " + create_access_token("owner_a", "RESIDENTE")
            })
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_legacy_tenant_dependencies_do_not_operate_on_company(corp, db_core_session, monkeypatch):
    """Incluso con scope residencial accidental, no configura RLS hacia empresa."""
    from backend.db.core import UserTenantScope, AccessLevel, ScopeStatus
    from backend.core.tenant import context
    db = db_core_session
    db.add(UserTenantScope(usuario_id="host_a", tenant_id="ca",
                           access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO))
    db.commit()
    calls = []
    monkeypatch.setattr(context, "_set_postgres_tenant", lambda *args: calls.append(args))
    with pytest.raises(HTTPException) as a:
        context.set_tenant_context("ca", db, corp["host_a"])
    assert a.value.status_code == 403
    with pytest.raises(HTTPException) as b:
        context.require_tenant_context(AccessLevel.RESIDENTE)("ca", db, corp["host_a"])
    assert b.value.status_code == 403
    assert calls == []
