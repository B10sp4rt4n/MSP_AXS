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
