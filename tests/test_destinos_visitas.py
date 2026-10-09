"""Destinos catalogados, excepciones y aislamiento del acceso."""
from datetime import datetime, timedelta
from backend.db.core import Casa, Visita, UserTenantScope, ScopeStatus, AccessLevel
from backend.db.gov import Policy, PolicyScope, GovStatus
import pytest
from backend.db.core import MSP, Condominio, Usuario, MSPMembership
from backend.core.auth.jwt import create_access_token

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




def test_catalogo_destino_y_excepcion(client, people, db_gov_session):
    people.add_all([
        Casa(casa_id="a_home", condominio_id="a1", numero="101", tipo="casa"),
        Casa(casa_id="b_home", condominio_id="b1", numero="201", tipo="casa"),
        Casa(casa_id="a_common", condominio_id="a1", numero="Administración", tipo="administracion"),
    ])
    people.commit()
    db_gov_session.add(Policy(policy_id="dest_create", nombre="Create", ambito=PolicyScope.GLOBAL,
                              accion_objetivo="crear_visita", limites={}, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    guard = headers("guard", "GUARDIA")
    body = {"condominio_id": "a1", "nombre_visitante": "Catalog visitor", "tipo_visita": "eventual",
            "vigencia": (datetime.utcnow()+timedelta(days=1)).isoformat(), "destino_id": "a_home",
            "casa_unidad": "Texto arbitrario"}
    url = "/visitas/entrada/a1"
    homes = client.get("/condominios/a1/destinos", headers=guard)
    assert homes.status_code == 200
    assert {d["destino_id"] for d in homes.json()} == {"a_home", "a_common"}
    assert client.get("/condominios/b1/destinos", headers=guard).status_code == 403
    created = client.post(url, headers=guard, json=body)
    assert created.status_code == 200, created.text
    assert created.json()["destino_id"] == "a_home" and created.json()["casa_unidad"] == "101"
    assert created.json()["destino_tipo"] == "vivienda"
    saved = people.query(Visita).filter_by(visita_id=created.json()["visita_id"]).one()
    assert saved.destino_id == "a_home"
    assert client.post(url, headers=guard, json={**body, "destino_id": "b_home"}).status_code == 400
    assert client.post(url, headers=guard, json={**body, "destino_id": None, "casa_unidad": "Casa inventada"}).status_code == 400
    assert client.post(url, headers=guard, json={**body, "destino_id": "OTRO"}).status_code == 400
    exception = client.post(url, headers=guard, json={**body, "destino_id": "OTRO", "destino_motivo": "Entrega en acceso principal"})
    assert exception.status_code == 200, exception.text
    assert exception.json()["destino_tipo"] == "otro" and exception.json()["destino_id"] is None
    assert exception.json()["destino_motivo"] == "Entrega en acceso principal"
    common = client.post(url, headers=guard, json={**body, "destino_id": "a_common"})
    assert common.status_code == 200 and common.json()["destino_tipo"] == "comun"
    resident = headers("resident", "RESIDENTE")
    assert client.get(f'/visitas/{common.json()["visita_id"]}?condominio_id=a1', headers=resident).status_code == 403
    assert client.post("/condominios/a1/casas/a_common/residente", headers=headers("msp", "MSP_ADMIN"),
                       json={"nombre": "No", "email": "no@test.local"}).status_code == 400


def test_preregistro_destino_asignado_y_rechazo_inexistente(client, people, db_gov_session):
    from backend.db.core import Usuario
    house = Casa(casa_id="resident_home", condominio_id="a1", numero="101", tipo="casa")
    people.add(house)
    people.flush()
    resident = people.query(Usuario).filter_by(usuario_id="resident").one()
    resident.casa_id = house.casa_id
    resident.casa_unidad = house.numero
    people.commit()
    db_gov_session.add(Policy(policy_id="dest_qr", nombre="QR", ambito=PolicyScope.GLOBAL,
                              accion_objetivo="generar_qr", limites={}, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    h = headers("resident", "RESIDENTE")
    result = client.post("/preregistro/crear", headers=h,
                         json={"nombre_visitante": "Auto home", "tipo_visita": "visita_personal"})
    assert result.status_code == 200, result.text
    visit = people.query(Visita).filter_by(visita_id=result.json()["visita_id"]).one()
    assert visit.destino_id == house.casa_id and visit.destino_tipo == "vivienda"
    resident.casa_id = None
    resident.casa_unidad = "Inexistente"
    people.commit()
    before = people.query(Visita).count()
    assert client.post("/preregistro/crear", headers=h,
                       json={"nombre_visitante": "Blocked", "tipo_visita": "visita_personal"}).status_code == 400
    assert people.query(Visita).count() == before


@pytest.fixture
def prereg_catalog(people, db_gov_session):
    people.add_all([
        Casa(casa_id="home", condominio_id="a1", numero="101", tipo="casa"),
        Casa(casa_id="common", condominio_id="a1", numero="Administración", tipo="administracion"),
        Casa(casa_id="foreign", condominio_id="b1", numero="201", tipo="casa"),
    ])
    people.flush()
    resident = people.query(Usuario).filter_by(usuario_id="resident").one()
    resident.casa_id, resident.casa_unidad = "home", "101"
    people.commit()
    db_gov_session.add(Policy(policy_id="admin_qr", nombre="QR", ambito=PolicyScope.GLOBAL,
                             accion_objetivo="generar_qr", limites={}, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    return people


@pytest.mark.parametrize("identity,role", [("admin", "ADMIN_CONDOMINIO"), ("msp", "MSP_ADMIN")])
@pytest.mark.parametrize("destination", ["home", "common"])
def test_admin_preregistro_without_house(client, prereg_catalog, identity, role, destination):
    from backend.db.core import EventOutbox
    db = prereg_catalog
    user = db.query(Usuario).filter_by(usuario_id=identity).one()
    assert user.casa_id is None and user.casa_unidad is None
    result = client.post("/preregistro/crear", headers=headers(identity, role), json={
        "nombre_visitante": "Synthetic visitor", "tipo_visita": "visita_personal",
        "condominio_id": "a1", "destino_id": destination,
    })
    assert result.status_code == 200, result.text
    visit = db.query(Visita).filter_by(visita_id=result.json()["visita_id"]).one()
    assert (visit.condominio_id, visit.destino_id, visit.autorizada_por) == ("a1", destination, identity)
    assert visit.qr_token and visit.autorizada_en and result.json()["qr_base64"]
    assert user.casa_id is None and user.casa_unidad is None
    events = db.query(EventOutbox).all()
    assert len(events) == 2
    assert {e.payload["entidad"] for e in events} == {"visita", "qr"}
    assert all(e.payload["tenant_id"] == "a1" and e.payload["identity_id"] == identity for e in events)


@pytest.mark.parametrize("identity,role,extra,status", [
    ("admin", "ADMIN_CONDOMINIO", {}, 400),
    ("admin", "ADMIN_CONDOMINIO", {"condominio_id": "a1"}, 400),
    ("admin", "ADMIN_CONDOMINIO", {"condominio_id": "b1", "destino_id": "foreign"}, 403),
    ("msp", "MSP_ADMIN", {"condominio_id": "b1", "destino_id": "foreign"}, 403),
    ("admin", "ADMIN_CONDOMINIO", {"condominio_id": "a1", "destino_id": "foreign"}, 400),
    ("admin", "ADMIN_CONDOMINIO", {"condominio_id": "a1", "destino_id": "OTRO"}, 400),
    ("resident", "RESIDENTE", {"condominio_id": "b1", "destino_id": "foreign"}, 403),
    ("resident", "RESIDENTE", {"condominio_id": "a1", "destino_id": "common"}, 403),
    ("guard", "GUARDIA", {"condominio_id": "a1", "destino_id": "home"}, 403),
])
def test_preregistro_rejects_unauthorized_destination(client, prereg_catalog, identity, role, extra, status):
    result = client.post("/preregistro/crear", headers=headers(identity, role), json={
        "nombre_visitante": "Rejected synthetic visitor", "tipo_visita": "visita_personal", **extra,
    })
    assert result.status_code == status, result.text
    assert prereg_catalog.query(Visita).count() == 0


def test_admin_preregistro_qr_failure_rolls_back(client, prereg_catalog, monkeypatch):
    from backend.services import qr_service
    from backend.db.core import EventOutbox
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic QR failure")
    monkeypatch.setattr(qr_service, "generar_qr_para_visita", fail)
    result = client.post("/preregistro/crear", headers=headers("admin", "ADMIN_CONDOMINIO"), json={
        "nombre_visitante": "Rollback", "tipo_visita": "visita_personal", "condominio_id": "a1", "destino_id": "home",
    })
    assert result.status_code == 500
    assert prereg_catalog.query(Visita).count() == 0
    assert prereg_catalog.query(EventOutbox).count() == 0


def test_admin_without_scope_cannot_preregister(client, prereg_catalog):
    prereg_catalog.query(UserTenantScope).filter_by(usuario_id="admin").delete()
    prereg_catalog.commit()
    result = client.post("/preregistro/crear", headers=headers("admin", "ADMIN_CONDOMINIO"), json={
        "nombre_visitante": "Denied", "tipo_visita": "visita_personal",
        "condominio_id": "a1", "destino_id": "home",
    })
    assert result.status_code == 403
    assert prereg_catalog.query(Visita).count() == 0


def test_admin_government_denial_creates_no_visit(client, prereg_catalog, monkeypatch):
    from backend.routers import preregistro_router
    monkeypatch.setattr(preregistro_router, "puede_ejecutar_accion", lambda **kwargs: (False, "synthetic denial"))
    result = client.post("/preregistro/crear", headers=headers("admin", "ADMIN_CONDOMINIO"), json={
        "nombre_visitante": "Denied", "tipo_visita": "visita_personal",
        "condominio_id": "a1", "destino_id": "home",
    })
    assert result.status_code == 403
    assert prereg_catalog.query(Visita).count() == 0
