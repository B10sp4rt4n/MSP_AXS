"""Integrated synthetic HTTP journey. SQLite/JWT fixtures, no Clerk or live RLS."""
from uuid import uuid4

from backend.db.core import (
    Casa, CorporateDestination, CorporateMembership, CorporateSite,
    CorporateSiteAssignment, EventOutbox, Usuario,
)
from tests.test_corporate_superadmin import company_setup  # noqa: F401


def test_two_companies_from_bootstrap_to_revocation(company_setup, monkeypatch):
    client, core, gov, template, auth = company_setup
    monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "true")
    monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
    core.add_all([
        Usuario(usuario_id="owner_b", email="owner-b@example.test", rol="RESIDENTE"),
        Usuario(usuario_id="host_a", email="host-a@example.test", rol="RESIDENTE"),
    ])
    core.commit()
    platform = "/plataforma/corporativo/empresas"
    companies = {}
    for label, owner in (("A", "owner"), ("B", "owner_b")):
        body = {**template, "request_id": str(uuid4()),
                "nombre": "Empresa Sintética " + label, "owner_user_id": owner}
        result = client.post(platform, headers=auth("super"), json=body)
        assert result.status_code == 201, result.text
        tenant = result.json()["tenant_id"]
        companies[label] = tenant
        # Same command after a lost acknowledgement must not create another company.
        assert client.post(platform, headers=auth("super"), json=body).json()["tenant_id"] == tenant
        root = f"/corporativo/{tenant}"
        assert client.get(root + "/sedes", headers=auth(owner)).status_code == 403
        command = {"request_id": str(uuid4()), "expected_revision": 0,
                   "max_sedes": 2, "max_destinos_por_sede": 1}
        limits = client.put(f"{platform}/{tenant}/capacidades", headers=auth("super"), json=command)
        assert limits.status_code == 200, limits.text
        enabled = client.post(f"{platform}/{tenant}/habilitar-directorio",
                              headers=auth("super"), json={"confirmacion": True})
        assert enabled.status_code == 200, enabled.text

    a, b = companies["A"], companies["B"]
    root = f"/corporativo/{a}"
    sites = []
    for name in ("Oficina sintética", "Planta sintética"):
        response = client.post(root + "/sedes", headers=auth("owner"), json={"nombre": name})
        assert response.status_code == 201, response.text
        sites.append(response.json()["site_id"])
    rejected = client.post(root + "/sedes", headers=auth("owner"), json={"nombre": "Excedente"})
    assert rejected.status_code == 403
    assert core.query(CorporateSite).filter_by(tenant_id=a).count() == 2
    destination_path = root + f"/sedes/{sites[0]}/destinos"
    assert client.post(destination_path, headers=auth("owner"), json={"nombre": "Recepción"}).status_code == 201
    assert client.post(destination_path, headers=auth("owner"), json={"nombre": "Excedente"}).status_code == 403
    assert client.get(root + f"/sedes/{sites[1]}/destinos", headers=auth("owner")).json() == []

    # Bidirectional tenant boundaries; GLOBAL cannot replace directory membership.
    for actor, tenant in (("owner", b), ("owner_b", a), ("super", a), ("provider", a)):
        assert client.get(f"/corporativo/{tenant}/sedes", headers=auth(actor)).status_code == 403
        assert client.post(f"/corporativo/{tenant}/sedes", headers=auth(actor),
                           json={"nombre": "Cruce prohibido"}).status_code == 403
    core.add(CorporateMembership(membership_id="sim_host_membership", tenant_id=a,
                                user_id="host_a", rol="host", estado="activo"))
    core.add(CorporateSiteAssignment(assignment_id="sim_host_site", tenant_id=a,
                                    site_id=sites[0], user_id="host_a"))
    core.commit()
    host_headers = auth("host_a")
    assert [s["site_id"] for s in client.get(root + "/sedes", headers=host_headers).json()] == [sites[0]]
    assert client.get(root + f"/sedes/{sites[1]}/destinos", headers=host_headers).status_code == 403
    assert client.post(destination_path, headers=host_headers, json={"nombre": "Sin permiso"}).status_code == 403
    core.query(CorporateMembership).filter_by(membership_id="sim_host_membership").one().estado = "revocado"
    core.commit()
    assert client.get(root + "/sedes", headers=host_headers).status_code == 403
    assert client.get(destination_path, headers=host_headers).status_code == 403
    assert core.query(Casa).count() == 0
    assert core.query(CorporateDestination).filter_by(tenant_id=b).count() == 0
    assert core.query(EventOutbox).filter_by(condominio_id=a).count() >= 7
