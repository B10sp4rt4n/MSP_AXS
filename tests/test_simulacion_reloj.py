"""Simulación HTTP del backend real; reloj local al test, sin sleep ni red externa."""
from datetime import datetime, timedelta, timezone
import pytest
from backend.db.core import Visita, EventOutbox, Usuario, UserTenantScope, AccessLevel, ScopeStatus
from backend.services import qr_service, visita_service, event_outbox
from tests.test_reglas_acceso import setup, headers, rules


@pytest.fixture
def reloj(monkeypatch):
    class Clock(datetime):
        instant = datetime(2030, 1, 15, 18, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz) if tz else cls.instant.replace(tzinfo=None)

        @classmethod
        def utcnow(cls):
            return cls.instant.replace(tzinfo=None)

        @classmethod
        def avanzar(cls, **delta):
            cls.instant += timedelta(**delta)

    from backend.schemas import preregistro
    monkeypatch.setattr(qr_service, "utc_now", lambda: Clock.instant)
    monkeypatch.setattr(visita_service, "datetime", Clock)
    monkeypatch.setattr(preregistro, "datetime", Clock)
    monkeypatch.setattr(event_outbox, "datetime", Clock)
    return Clock


def crear(client, db, reloj, tipo="visita_personal"):
    scheduled = reloj.instant + timedelta(hours=1)
    result = client.post("/preregistro/crear", headers=headers("resident", "RESIDENTE"), json={
        "nombre_visitante": "Simulación", "tipo_visita": tipo,
        "fecha_visita": scheduled.isoformat(), "proposito": "Prueba aislada"})
    assert result.status_code == 200, result.text
    row = db.query(Visita).filter_by(visita_id=result.json()["visita_id"]).one()
    return row, f"/qr/validar/{row.visita_id}/{row.qr_token}"


@pytest.mark.parametrize("tipo", ["visita_personal", "entrega", "proveedor"])
def test_recorrido_completo_sin_esperas(client, setup, reloj, tipo):
    rules(client, exigir_autorizacion=True, exigir_proposito=True)
    row, url = crear(client, setup, reloj, tipo)
    guard = headers("guard", "GUARDIA")
    assert row.autorizada_por == "resident"
    assert client.get(url, headers=guard).status_code == 400  # demasiado pronto
    reloj.avanzar(minutes=30)
    assert client.get(url, headers=guard).status_code == 200  # inicio inclusivo
    setup.refresh(row)
    entrada = row.entrada_registrada_en
    assert entrada == reloj.utcnow()
    assert client.get(url, headers=guard).status_code == 400
    reloj.avanzar(hours=4)  # puede salir aunque haya vencido la ventana de ingreso
    assert client.patch(f"/visitas/{row.visita_id}/salida", headers=guard).status_code == 200
    setup.refresh(row)
    salida = row.salida_registrada_en
    assert salida == reloj.utcnow() and salida > entrada
    assert row.estado == "salida_registrada"
    assert client.patch(f"/visitas/{row.visita_id}/salida", headers=guard).status_code == 400
    assert client.get(url, headers=guard).status_code == 400
    setup.refresh(row)
    assert (row.entrada_registrada_en, row.salida_registrada_en) == (entrada, salida)
    events = [e.payload for e in setup.query(EventOutbox).all()
              if e.payload.get("resultado") == "exito"]
    assert any(e.get("identity_id") == "guard" and e.get("accion") == "validar" for e in events)
    exits = [e for e in events if e.get("identity_id") == "guard"
             and e.get("metadata_json", {}).get("estado") == "salida_registrada"]
    assert len(exits) == 1
    assert exits[0]["metadata_json"]["salida_registrada_en"] == salida.isoformat()
    assert exits[0]["timestamp"] == salida.isoformat()


@pytest.mark.parametrize("seconds,expected", [(1799,400),(1800,200),(7199,200),(7200,400),(7201,400)])
def test_limites_exactos(client, setup, reloj, seconds, expected):
    row, url = crear(client, setup, reloj)
    reloj.avanzar(seconds=seconds)
    result = client.get(url, headers=headers("guard", "GUARDIA"))
    assert result.status_code == expected, result.text
    setup.refresh(row)
    assert (row.entrada_registrada_en is not None) == (expected == 200)


def test_cancelada_y_otro_condominio(client, setup, reloj):
    row, url = crear(client, setup, reloj)
    setup.add(Usuario(usuario_id="guard_b", email="b@test.local", rol="GUARDIA", condominio_id="b"))
    setup.flush()
    setup.add(UserTenantScope(usuario_id="guard_b", tenant_id="b", access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO))
    setup.commit()
    reloj.avanzar(minutes=30)
    assert client.get(url, headers=headers("guard_b", "GUARDIA")).status_code == 404
    assert client.get(url + "?condominio_id=a", headers=headers("guard_b", "GUARDIA")).status_code == 403
    assert client.patch(f"/visitas/{row.visita_id}/cancelar", headers=headers("resident", "RESIDENTE")).status_code == 200
    assert client.get(url, headers=headers("guard", "GUARDIA")).status_code == 400
    setup.refresh(row)
    assert row.estado == "cancelada" and row.entrada_registrada_en is None
