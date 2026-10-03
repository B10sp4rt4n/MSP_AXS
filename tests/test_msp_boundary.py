"""Cruces de dos proveedores y dos condominios por proveedor."""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException, Request

from backend.core.scope.msp_boundary import (
    active_msp_ids, require_condominio, require_msp_admin, require_visita,
)
from backend.db.core import (
    AccessLevel, Condominio, MSP, MSPMembership, ScopeStatus, UserTenantScope,
    Usuario, Visita,
)
from backend.db.gov import Authority, AuthorityType, GovStatus
from backend.routers.condominios_router import list_condominios
from backend.routers.msp_router import list_msps
from backend.routers.msp_router import asignar_admin_msp, revocar_admin_msp
from backend.routers.visitas_router import registrar_salida, obtener_visita
from backend.routers.preregistro_router import reenviar_qr


@pytest.fixture
def tenants(db_core_session, db_gov_session):
    db = db_core_session
    db.add_all([MSP(msp_id=m, nombre=m) for m in ("a", "b")])
    db.add_all([
        Condominio(condominio_id=f"{m}{n}", msp_id=m, nombre=f"{m}{n}")
        for m in ("a", "b") for n in (1, 2)
    ])
    users = {
        key: Usuario(usuario_id=key, email=f"{key}@test.local", rol=role,
                     condominio_id=condo, casa_unidad=unit, nombre=key)
        for key, role, condo, unit in (
            ("operator", "MSP_ADMIN", None, None),
            ("admin_a", "MSP_ADMIN", None, None),
            ("admin_b", "MSP_ADMIN", None, None),
            ("guard_a1", "GUARDIA", "a1", None),
            ("resident_a1", "RESIDENTE", "a1", "101"),
            ("resident_a2", "RESIDENTE", "a2", "201"),
        )
    }
    db.add_all(users.values())
    db.flush()
    db.add_all([
        MSPMembership(usuario_id="admin_a", msp_id="a"),
        MSPMembership(usuario_id="admin_b", msp_id="b"),
        UserTenantScope(usuario_id="guard_a1", tenant_id="a1",
                        access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO),
        UserTenantScope(usuario_id="resident_a1", tenant_id="a1",
                        access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO),
        UserTenantScope(usuario_id="resident_a2", tenant_id="a2",
                        access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO),
        Visita(visita_id="v_a1_101", condominio_id="a1", casa_unidad="101", estado="pendiente",
               nombre_visitante="Visitante A", tipo_visita="eventual", vigencia=datetime.utcnow() + timedelta(days=1)),
        Visita(visita_id="v_a1_102", condominio_id="a1", casa_unidad="102", estado="pendiente",
               nombre_visitante="Visitante A2", tipo_visita="eventual", vigencia=datetime.utcnow() + timedelta(days=1)),
        Visita(visita_id="v_b1", condominio_id="b1", casa_unidad="101", estado="pendiente",
               nombre_visitante="Visitante B", tipo_visita="eventual", vigencia=datetime.utcnow() + timedelta(days=1)),
    ])
    db.commit()
    db_gov_session.add(Authority(authority_id="global_operator", identity_id="operator",
                                 tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    return users


def denied(call):
    with pytest.raises(HTTPException) as exc:
        call()
    assert exc.value.status_code == 403


def test_provider_lists_and_membership_revocation(tenants, db_core_session, db_gov_session):
    db, gov = db_core_session, db_gov_session
    assert [m.msp_id for m in list_msps(db, gov, tenants["admin_a"])] == ["a"]
    assert {c.condominio_id for c in list_condominios(None, db, gov, tenants["admin_a"])} == {"a1", "a2"}
    assert {m.msp_id for m in list_msps(db, gov, tenants["operator"])} == {"a", "b"}
    assert {c.condominio_id for c in list_condominios(None, db, gov, tenants["operator"])} == {"a1", "a2", "b1", "b2"}
    denied(lambda: require_msp_admin(db, gov, tenants["admin_a"], "b"))
    member = db.query(MSPMembership).filter_by(usuario_id="admin_a").one()
    member.estado = "revocado"
    db.commit()
    assert active_msp_ids(db, tenants["admin_a"]) == []
    assert list_msps(db, gov, tenants["admin_a"]) == []
    denied(lambda: require_condominio(db, gov, tenants["admin_a"], "a1", AccessLevel.GUARDIA))


def test_condominium_and_home_boundaries(tenants, db_core_session, db_gov_session):
    db, gov = db_core_session, db_gov_session
    require_condominio(db, gov, tenants["admin_a"], "a2", AccessLevel.ADMIN_CONDOMINIO)
    denied(lambda: require_condominio(db, gov, tenants["admin_a"], "b1", AccessLevel.LECTURA))
    denied(lambda: require_condominio(db, gov, tenants["guard_a1"], "a2", AccessLevel.GUARDIA))
    denied(lambda: require_condominio(db, gov, tenants["resident_a1"], "a1", AccessLevel.GUARDIA))
    require_visita(db, gov, tenants["resident_a1"], "v_a1_101", AccessLevel.RESIDENTE, own_unit=True)
    denied(lambda: require_visita(db, gov, tenants["resident_a1"], "v_a1_102", AccessLevel.RESIDENTE, own_unit=True))
    denied(lambda: require_visita(db, gov, tenants["resident_a1"], "v_b1", AccessLevel.RESIDENTE,
                                  own_unit=True, condominio_id="b1"))
    denied(lambda: require_visita(db, gov, tenants["admin_b"], "v_a1_101", AccessLevel.GUARDIA,
                                  condominio_id="a1"))
    require_visita(db, gov, tenants["guard_a1"], "v_a1_102", AccessLevel.GUARDIA)
    denied(lambda: require_visita(db, gov, tenants["guard_a1"], "v_b1", AccessLevel.GUARDIA,
                                  condominio_id="b1"))
    assert require_visita(db, gov, tenants["admin_a"], "v_a1_101", AccessLevel.GUARDIA,
                          condominio_id="a1").visita_id == "v_a1_101"
    with pytest.raises(HTTPException) as exc:
        require_visita(db, gov, tenants["admin_a"], "v_a1_101", AccessLevel.GUARDIA)
    assert exc.value.status_code == 400


def test_no_msp_grant_from_legacy_role_alone(tenants, db_core_session, db_gov_session):
    db, gov = db_core_session, db_gov_session
    db.add(Usuario(usuario_id="legacy", email="legacy@test.local", rol="MSP_ADMIN", msp_id="b"))
    db.commit()
    legacy = db.query(Usuario).filter_by(usuario_id="legacy").one()
    denied(lambda: require_msp_admin(db, gov, legacy, "b"))
    assert list_msps(db, gov, legacy) == []


def test_member_grant_and_revocation_only_by_operator(tenants, db_core_session, db_gov_session):
    db, gov = db_core_session, db_gov_session
    denied(lambda: asignar_admin_msp("b", "admin_a", db, gov, tenants["admin_a"]))
    assert asignar_admin_msp("b", "admin_a", db, gov, tenants["operator"])["estado"] == "activo"
    require_msp_admin(db, gov, tenants["admin_a"], "b")
    denied(lambda: revocar_admin_msp("b", "admin_a", db, gov, tenants["admin_a"]))
    assert revocar_admin_msp("b", "admin_a", db, gov, tenants["operator"])["estado"] == "revocado"
    denied(lambda: require_msp_admin(db, gov, tenants["admin_a"], "b"))


def test_visit_routes_apply_boundary_before_mutation(tenants, db_core_session, db_gov_session):
    db, gov = db_core_session, db_gov_session
    denied(lambda: registrar_salida("v_a1_101", Request({"type": "http", "headers": []}), db, gov, tenants["admin_b"], condominio_id="a1"))
    denied(lambda: obtener_visita("v_a1_102", db, gov, tenants["resident_a1"]))
    denied(lambda: reenviar_qr("v_a1_102", Request({"type": "http", "headers": []}), db, gov, tenants["resident_a1"]))
    assert db.query(Visita).filter_by(visita_id="v_a1_101").one().estado == "pendiente"


def test_http_visita_resuelve_tenant_antes_de_buscar(tenants, db_core_session, db_gov_session, db_event_session):
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.db.core import get_core_db
    from backend.db.event import get_event_db
    from backend.db.gov import get_gov_db
    from backend.core.auth.jwt import create_access_token

    app.dependency_overrides[get_core_db] = lambda: db_core_session
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    try:
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {create_access_token('admin_a', 'MSP_ADMIN')}"}
            assert client.get("/visitas/v_a1_101", headers=headers).status_code == 400
            own = client.get("/visitas/v_a1_101?condominio_id=a1", headers=headers)
            assert own.status_code == 200
            assert own.json()["visita_id"] == "v_a1_101"
            assert client.get("/visitas/v_b1?condominio_id=b1", headers=headers).status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("actor,own,other", [
    ("admin_a", "a1", "b1"), ("admin_b", "b1", "a1"),
])
def test_http_create_cancel_and_denial_audit_both_directions(
    tenants, db_core_session, db_gov_session, db_event_session, monkeypatch,
    actor, own, other,
):
    """Real HTTP handlers/auth, isolated SQLite stores; no deployed Clerk/RLS claim."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker
    from backend.main import app
    from backend.core.auth.jwt import create_access_token
    from backend.db.core import Casa, SecurityOutbox, get_core_db
    from backend.db.event import get_event_db
    from backend.db.gov import Policy, PolicyScope, get_gov_db
    from backend.services import security_outbox

    db = db_core_session
    db.add_all([Casa(casa_id=f"home_{tenant}", condominio_id=tenant,
                     numero="101", tipo="casa") for tenant in (own, other)])
    db.commit()
    db_gov_session.add(Policy(policy_id="allow_create_for_test", nombre="Create",
        ambito=PolicyScope.GLOBAL, accion_objetivo="crear_visita", limites={},
        estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    monkeypatch.setattr(security_outbox, "SessionFactory", sessionmaker(bind=db.bind))
    app.dependency_overrides[get_core_db] = lambda: db
    app.dependency_overrides[get_event_db] = lambda: db_event_session
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    headers = {"Authorization": f"Bearer {create_access_token(actor, 'MSP_ADMIN')}"}
    body = {"condominio_id": own, "nombre_visitante": "Automated isolation test",
            "tipo_visita": "eventual", "destino_id": f"home_{own}",
            "vigencia": (datetime.utcnow() + timedelta(days=1)).isoformat()}
    try:
        with TestClient(app) as client:
            before = db.query(Visita).count()
            created = client.post(f"/visitas/{own}", headers=headers, json=body)
            assert created.status_code == 200, created.text
            visit_id = created.json()["visita_id"]
            assert created.json()["condominio_id"] == own
            assert created.json()["estado"] == "pendiente"
            assert db.query(Visita).count() == before + 1

            cross = client.post(f"/visitas/{other}", headers=headers,
                json={**body, "condominio_id": other, "destino_id": f"home_{other}"})
            assert cross.status_code == 403
            assert db.query(Visita).count() == before + 1
            spoof = client.post(f"/visitas/{own}", headers=headers,
                                json={**body, "condominio_id": other})
            assert spoof.status_code == 400
            assert db.query(Visita).count() == before + 1

            owner = "admin_b" if actor == "admin_a" else "admin_a"
            other_headers = {"Authorization": f"Bearer {create_access_token(owner, 'MSP_ADMIN')}"}
            rejected = client.patch(f"/visitas/{visit_id}/cancelar?condominio_id={own}",
                                    headers=other_headers)
            assert rejected.status_code == 403
            db.expire_all()
            assert db.query(Visita).filter_by(visita_id=visit_id).one().estado == "pendiente"

            denials = db.query(SecurityOutbox).order_by(SecurityOutbox.created_at).all()
            assert len(denials) == 2
            assert [(row.payload["identity_id"], row.payload["metadata_json"]["route"],
                     row.payload["metadata_json"]["method"]) for row in denials] == [
                (actor, "/visitas/{condominio_id}", "POST"),
                (owner, "/visitas/{visita_id}/cancelar", "PATCH"),
            ]
            assert all(row.payload["motivo"] == "SCOPE_DENIED" and
                       row.payload["metadata_json"]["identity_verified"] for row in denials)

            cancelled = client.patch(f"/visitas/{visit_id}/cancelar?condominio_id={own}",
                                     headers=headers)
            assert cancelled.status_code == 200, cancelled.text
            own_read = client.get(f"/visitas/{visit_id}?condominio_id={own}", headers=headers)
            assert own_read.status_code == 200
            assert own_read.json()["estado"] == "cancelada"
    finally:
        app.dependency_overrides.clear()
