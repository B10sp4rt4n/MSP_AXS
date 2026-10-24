"""C0 endpoint matrix, using synthetic databases and no external transports.

These HTTP tests exercise the published application, including durable denial
audit. SQLite does not prove PostgreSQL RLS; that has a separate CI gate.
"""
from datetime import datetime, timedelta
from urllib.parse import urlsplit

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select
from starlette.routing import Match

from backend.core.auth.jwt import create_access_token
from backend.db.core import (
    AccessLevel, Base_CORE, Casa, Condominio, Evidencia, MSP, MSPMembership,
    ScopeStatus, SecurityOutbox, UserTenantScope, Usuario, Visita,
)
from backend.db.gov import Authority, AuthorityType, GovStatus


UUID = "00000000-0000-4000-8000-000000000001"
TENANT = "corp-matrix"
VISIT = "visit-matrix"
HOUSE = "house-matrix"
MODE_DENIED = "Operacion no disponible para esta modalidad"


def case(method, path, *, role="ADMIN_CONDOMINIO", **kwargs):
    return pytest.param(method, path, role, kwargs, id=method + " " + path)


VISIT_BODY = {"condominio_id": TENANT, "nombre_visitante": "Synthetic visitor",
              "tipo_visita": "eventual", "vigencia": "2099-01-01T12:00:00Z",
              "destino_id": HOUSE}
FILES = {"frente": ("front.jpg", b"synthetic", "image/jpeg"),
         "reverso": ("back.jpg", b"synthetic", "image/jpeg")}
CASES = [
    case("GET", "/condominios/{tenant}/reglas-acceso"),
    case("PUT", "/condominios/{tenant}/reglas-acceso", json={}),
    case("POST", "/condominios/{tenant}/casas", json={"numero": "101"}),
    case("POST", "/condominios/{tenant}/casas/house-matrix/residente",
         json={"nombre": "Synthetic", "email": "new@example.test"}),
    case("GET", "/condominios/{tenant}/casas"),
    case("GET", "/condominios/{tenant}/usuarios"),
    case("POST", "/condominios/{tenant}/usuarios",
         json={"nombre": "Synthetic", "email": "new@example.test", "rol": "GUARDIA"}),
    case("PATCH", "/condominios/{tenant}/usuarios/local",
         json={"nombre": "Synthetic", "email": "local@example.test", "rol": "GUARDIA"}),
    case("GET", "/condominios/{tenant}/destinos"),
    case("POST", "/condominios/{tenant}/usuarios/local/invitacion",
         json={"expected_email": "local@example.test"}),
    case("GET", "/condominios/{tenant}/residentes/plantilla"),
    case("POST", "/condominios/{tenant}/residentes/importar", json={"archivo": "AA=="}),
    case("GET", "/condominios/{tenant}/permisos/procedencia"),
    case("PUT", "/condominios/{tenant}/permisos/1/procedencia",
         json={"kind": "condominio", "evidence_ref": "SYNTHETIC"}),
    case("POST", "/condominios/{tenant}/proveedor/baja",
         json={"msp_id": "provider-matrix", "reason": "Synthetic test"}),
    case("GET", "/condominios/{tenant}/proveedor/contratos"),
    case("POST", "/condominios/{tenant}/proveedor/contratos",
         json={"contract_id": UUID, "msp_id": "provider-matrix", "evidence_ref": "SYNTHETIC"}),
    case("POST", "/condominios/{tenant}/proveedor/contratos/" + UUID + "/personal/local",
         json={"evidence_ref": "SYNTHETIC"}),
    case("POST", "/visitas/entrada/{tenant}", role="GUARDIA", json=VISIT_BODY),
    case("POST", "/visitas/{tenant}", role="GUARDIA", json=VISIT_BODY),
    case("POST", "/visitas/", json=VISIT_BODY),
    case("GET", "/visitas/mis-visitas/{tenant}", role="RESIDENTE"),
    case("GET", "/visitas/condominio/{tenant}"),
    case("PATCH", "/visitas/{visit}/entrada", role="GUARDIA"),
    case("PATCH", "/visitas/{visit}/salida", role="GUARDIA"),
    case("PATCH", "/visitas/{visit}/cancelar"),
    case("GET", "/visitas/{visit}"),
    case("PATCH", "/visitas/{visit}/autorizar", json={}),
    case("GET", "/visitas/resumen-turno/{tenant}",
         params={"inicio": "2026-01-01T00:00:00Z", "fin": "2026-01-02T00:00:00Z"}),
    case("POST", "/qr/generar/{visit}"),
    case("GET", "/qr/validar/{visit}/synthetic-token", role="GUARDIA"),
    case("POST", "/preregistro/crear", json={"condominio_id": TENANT,
         "destino_id": HOUSE, "nombre_visitante": "Synthetic", "tipo_visita": "eventual"}),
    case("GET", "/preregistro/qr/{visit}"),
    case("POST", "/evidencias/entrada/{visit}", role="GUARDIA",
         files={"foto_visitante": ("photo.jpg", b"synthetic", "image/jpeg")}),
    case("POST", "/identificaciones/{visit}",
         data={"nombre": "Synthetic", "captura_id": UUID}, files=FILES),
    case("GET", "/identificaciones/{visit}"),
    case("POST", "/identificaciones/{visit}/conservacion/ciclo-prueba"),
    case("PUT", "/identificaciones/{visit}/conservacion/excepcion", json={
         "hasta": "2099-01-01T00:00:00Z", "responsable": "Synthetic",
         "incidencia": "SYNTHETIC", "motivo": "Synthetic test"}),
    case("DELETE", "/identificaciones/{visit}/conservacion/excepcion"),
    case("DELETE", "/identificaciones/{visit}/borrado-prueba"),
    case("GET", "/identificaciones/{visit}/photo-matrix"),
    case("POST", "/evidencias-salida/{visit}", data={"captura_id": UUID},
         files={"foto": ("photo.jpg", b"synthetic", "image/jpeg")}),
    case("GET", "/evidencias-salida/{visit}"),
    case("GET", "/evidencias-salida/{visit}/exit-photo-matrix"),
    case("GET", "/bitacora/{tenant}"),
    case("GET", "/reportes/{tenant}/identificaciones-vencimiento"),
    *[case("GET", "/reportes/{tenant}/operacion", params={
        "desde": "2026-01-01", "hasta": "2026-01-02", "formato": fmt})
      for fmt in ("json", "xlsx", "pdf")],
    case("POST", "/solicitudes-acceso/{tenant}", json={"solicitud_id": UUID,
         "destino_id": HOUSE, "nombre_visitante": "Synthetic", "tipo_visita": "eventual",
         "proposito": "Synthetic test"}),
    case("GET", "/solicitudes-acceso/{tenant}"),
    case("GET", "/solicitudes-acceso/{tenant}/" + UUID),
    case("POST", "/solicitudes-acceso/{tenant}/" + UUID + "/respuesta", role="RESIDENTE",
         json={"decision": "permitida", "consentimiento": True}),
]


@pytest.fixture
def boundary(db_session, db_gov_session, monkeypatch):
    db = db_session
    db.add(MSP(msp_id="provider-matrix", nombre="Synthetic provider"))
    db.add_all([
        Condominio(condominio_id=TENANT, msp_id="provider-matrix", nombre="Synthetic company",
                   modalidad="corporativo", corporativo_habilitado=False),
        Condominio(condominio_id="res-matrix", msp_id="provider-matrix", nombre="Synthetic home"),
    ])
    db.flush()
    db.add(Casa(casa_id=HOUSE, condominio_id=TENANT, numero="101", tipo="casa"))
    db.flush()
    for uid in ("global-matrix", "msp-matrix", "local", "outsider-matrix"):
        db.add(Usuario(usuario_id=uid, email=uid + "@example.test", rol="ADMIN_CONDOMINIO",
                       condominio_id=TENANT, casa_id=HOUSE, casa_unidad="101"))
    db.flush()
    db.add(MSPMembership(usuario_id="msp-matrix", msp_id="provider-matrix"))
    for uid, tenant in (("local", TENANT), ("outsider-matrix", "res-matrix")):
        db.add(UserTenantScope(usuario_id=uid, tenant_id=tenant,
                              access_level=AccessLevel.ADMIN_CONDOMINIO, estado=ScopeStatus.ACTIVO))
    db.add(Visita(visita_id=VISIT, condominio_id=TENANT, nombre_visitante="PRIVATE_VISITOR_SENTINEL",
                 casa_unidad="101", destino_id=HOUSE, destino_tipo="vivienda", tipo_visita="eventual",
                 estado="pendiente", qr_token="synthetic-token", vigencia=datetime.utcnow(),
                 qr_vigencia=datetime.utcnow() + timedelta(hours=1)))
    db.flush()
    for eid, category in (("photo-matrix", "identificacion"), ("exit-photo-matrix", "salida")):
        db.add(Evidencia(evidencia_id=eid, visita_id=VISIT, guardia_id="local",
                         categoria=category, sub_tipo="general", archivo_url="PRIVATE_OBJECT_SENTINEL",
                         metadata_json={"storage": "vercel_blob_private"}))
    db.commit()
    db_gov_session.add(Authority(authority_id="matrix-global", identity_id="global-matrix",
                                 tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
    db_gov_session.commit()
    # Exercise the purge authorization too, without bypassing its feature gate.
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("NEON_DEV_ENDPOINT", "ep-withered-resonance-b59tusv3")
    monkeypatch.setenv("AXS_ID_PHOTOS_TEST_PURGE_ENABLED", "true")

    def forbidden(*args, **kwargs):
        pytest.fail("Denied request reached external storage or transport")

    from backend.services import identificacion_service, alexa_notifications, clerk_invitations
    import cloudinary.uploader
    for name in ("put", "read", "delete"):
        monkeypatch.setattr(identificacion_service.PrivateIdentityStore, name, forbidden)
    monkeypatch.setattr(cloudinary.uploader, "upload", forbidden)
    monkeypatch.setattr(alexa_notifications, "enviar_aviso", forbidden)
    monkeypatch.setattr(clerk_invitations, "send_invitation", forbidden)
    return db


def snapshot(db):
    return {table.name: [dict(row) for row in db.execute(select(table)).mappings()]
            for table in Base_CORE.metadata.sorted_tables if table is not SecurityOutbox.__table__}


@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
@pytest.mark.parametrize("actor", ["global-matrix", "msp-matrix", "local", "outsider-matrix"])
@pytest.mark.parametrize("method,path,role,kwargs", CASES)
def test_residential_endpoints_deny_corporate_without_effects(
    client, boundary, method, path, role, kwargs, actor, enabled,
):
    boundary.query(Condominio).filter_by(condominio_id=TENANT).one().corporativo_habilitado = enabled
    user = boundary.query(Usuario).filter_by(usuario_id=actor).one()
    user.rol = "MSP_ADMIN" if actor == "msp-matrix" else role
    boundary.commit()
    before = snapshot(boundary)
    opts = {**kwargs, "params": {"condominio_id": TENANT, **kwargs.get("params", {})}}
    response = client.request(method, path.format(tenant=TENANT, visit=VISIT),
                              headers={"Authorization": "Bearer " + create_access_token(actor, user.rol)},
                              **opts)
    assert response.status_code == 403, response.text
    # GLOBAL exercises each route with an admitted nominal role, so a generic
    # role rejection cannot masquerade as a modality check.
    if actor == "global-matrix":
        assert response.json()["detail"] == MODE_DENIED, response.text
    assert "PRIVATE_VISITOR_SENTINEL" not in response.text
    assert "PRIVATE_OBJECT_SENTINEL" not in response.text
    assert response.headers.get("content-type", "").startswith("application/json")
    assert "location" not in response.headers
    boundary.expire_all()
    assert snapshot(boundary) == before
    events = boundary.query(SecurityOutbox).all()
    assert len(events) == 1
    assert events[0].payload["motivo"] in {
        "TENANT_MODE_DENIED", "SCOPE_DENIED", "ROLE_DENIED", "PLATFORM_DENIED",
    }
    payload = str(events[0].payload)
    assert "PRIVATE_" not in payload and "synthetic-token" not in payload


def test_matrix_covers_every_published_residential_resource_route():
    """Fail when a new route is published without a negative modality test."""
    from backend.main import app
    modules = {"condominios_router", "resident_import_router", "provider_offboarding_router",
               "visitas_router", "qr_router", "preregistro_router", "evidencias_router",
               "identificaciones_router", "evidencias_salida_router", "bitacora_router",
               "reportes_router", "solicitudes_acceso_router"}
    exempt = {("GET", "/condominios/"), ("POST", "/condominios/"), ("GET", "/preregistro/reloj")}
    routes = [r for r in app.routes if isinstance(r, APIRoute)
              and r.endpoint.__module__.rsplit(".", 1)[-1] in modules]
    expected = {(m, r.path) for r in routes for m in r.methods} - exempt
    covered = set()
    for item in CASES:
        method, path, _, _ = item.values
        scope = {"type": "http", "method": method,
                 "path": urlsplit(path.format(tenant=TENANT, visit=VISIT)).path}
        matched = next(r for r in routes if r.matches(scope)[0] == Match.FULL)
        covered.add((method, matched.path))
    assert covered == expected
