from tests.test_reglas_acceso import setup, headers, pending, body
from backend.db.core import Evidencia


def test_recovery_plate_is_scoped_and_does_not_expose_metadata(client, setup):
    db = setup
    pending(db, visita_id="plate-a")
    pending(db, visita_id="plate-b", condominio_id="b")
    db.add_all([
        Evidencia(evidencia_id="ea", visita_id="plate-a", categoria="preregistro",
                  metadata_json={"placa": "ABC123", "documento": "private", "notas": "private"}),
        Evidencia(evidencia_id="eb", visita_id="plate-b", categoria="preregistro",
                  metadata_json={"placa": "OTHER"}),
    ])
    db.commit()
    auth = headers("guard", "GUARDIA")
    res = client.get("/visitas/condominio/a", headers=auth)
    assert res.status_code == 200, res.text
    assert [(v["visita_id"], v["placa"]) for v in res.json()] == [("plate-a", "ABC123")]
    assert "private" not in res.text and "OTHER" not in res.text
    res = client.get("/visitas/plate-a?condominio_id=a", headers=auth)
    assert res.status_code == 200 and res.json()["placa"] == "ABC123"
    assert client.get("/visitas/plate-b?condominio_id=a", headers=auth).status_code in (403, 404)


def test_plate_recorded_at_caseta_can_be_recovered(client, setup):
    auth = headers("guard", "GUARDIA")
    result = client.post("/visitas/entrada/a", json=body(placa="NEW123"), headers=auth)
    assert result.status_code == 200, result.text
    visita_id = result.json()["visita_id"]
    result = client.get(f"/visitas/{visita_id}?condominio_id=a", headers=auth)
    assert result.status_code == 200 and result.json()["placa"] == "NEW123"
