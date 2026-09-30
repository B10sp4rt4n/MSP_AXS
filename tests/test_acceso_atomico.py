"""Una transición ganadora conserva hora y estado frente a reintentos."""
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from backend.db.core import Visita, Usuario, UserTenantScope, AccessLevel, ScopeStatus
from backend.services import visita_service
from backend.core.auth.jwt import create_access_token


@pytest.fixture
def visita(db_session, condominio_base):
    row = Visita(visita_id="atomic", condominio_id=condominio_base.condominio_id,
                 nombre_visitante="Visitante", casa_unidad="101", estado="pendiente")
    db_session.add(row)
    db_session.commit()
    return row


def enable_qr(db, row, token="valid"):
    row.qr_token = token
    row.qr_vigencia = datetime.utcnow() + timedelta(minutes=30)
    row.vigencia = datetime.utcnow()
    db.commit()


def test_reintentos_no_reescriben_entrada_ni_salida(db_session, visita):
    saved = visita_service.registrar_entrada(db_session, visita.visita_id)
    entry = saved.entrada_registrada_en
    with pytest.raises(HTTPException):
        visita_service.registrar_entrada(db_session, visita.visita_id)
    assert db_session.get(Visita, visita.visita_id).entrada_registrada_en == entry
    saved = visita_service.registrar_salida(db_session, visita.visita_id)
    departure = saved.salida_registrada_en
    with pytest.raises(HTTPException):
        visita_service.registrar_salida(db_session, visita.visita_id)
    saved = db_session.get(Visita, visita.visita_id)
    assert saved.entrada_registrada_en == entry
    assert saved.salida_registrada_en == departure
    assert saved.estado == "salida_registrada"


@pytest.mark.parametrize("change", ["cancel", "replace", "expire", "future"])
def test_estado_actual_prevalece_sobre_qr_previamente_leido(db_session, visita, change):
    enable_qr(db_session, visita)
    if change == "cancel":
        visita_service.cancelar_visita(db_session, visita.visita_id, estado_esperado="pendiente")
    elif change == "replace":
        visita_service.actualizar_qr(db_session, visita.visita_id, "replacement", visita.qr_vigencia)
    elif change == "expire":
        visita.qr_vigencia = datetime.utcnow() - timedelta(seconds=1)
        db_session.commit()
    else:
        visita.vigencia = datetime.utcnow() + timedelta(hours=2)
        db_session.commit()
    with pytest.raises(HTTPException):
        visita_service.registrar_entrada(db_session, visita.visita_id, qr_token="valid")
    assert db_session.get(Visita, visita.visita_id).entrada_registrada_en is None


def test_qr_no_permite_entrada_manual_ni_regeneracion_tras_consumo(db_session, visita):
    enable_qr(db_session, visita)
    with pytest.raises(HTTPException):
        visita_service.registrar_entrada(db_session, visita.visita_id)
    saved = visita_service.registrar_entrada(db_session, visita.visita_id, qr_token="valid")
    entry = saved.entrada_registrada_en
    with pytest.raises(HTTPException):
        visita_service.actualizar_qr(db_session, visita.visita_id, "new", visita.qr_vigencia)
    with pytest.raises(HTTPException):
        visita_service.cancelar_visita(db_session, visita.visita_id, estado_esperado="pendiente")
    saved = db_session.get(Visita, visita.visita_id)
    assert saved.estado == "entrada_registrada" and saved.entrada_registrada_en == entry
    assert saved.qr_token == "valid"


def test_fallo_commit_revierte_entrada(db_session, visita, monkeypatch):
    def fail():
        raise RuntimeError("Simulated connection failure before commit")
    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError):
        visita_service.registrar_entrada(db_session, visita.visita_id)
    saved = db_session.get(Visita, visita.visita_id)
    assert saved.estado == "pendiente" and saved.entrada_registrada_en is None


def test_http_roles_tenant_y_un_solo_evento_de_exito(client, db_session, visita, monkeypatch):
    import backend.routers.qr_router as qr_router
    records = []
    monkeypatch.setattr(qr_router, "registrar_evento", lambda **kw: records.append(kw))
    condo = visita.condominio_id
    for identity, role, house in [("guard", "GUARDIA", None),
                                  ("resident", "RESIDENTE", "101"),
                                  ("neighbor", "RESIDENTE", "102")]:
        db_session.add(Usuario(usuario_id=identity, email=f"{identity}@test.local", rol=role,
                               condominio_id=condo, casa_unidad=house))
        db_session.flush()
        db_session.add(UserTenantScope(usuario_id=identity, tenant_id=condo,
            access_level=AccessLevel[role], estado=ScopeStatus.ACTIVO))
    db_session.commit()
    def headers(identity, role):
        return {"Authorization": "Bearer " + create_access_token(identity, role)}
    resident = headers("resident", "RESIDENTE")
    neighbor = headers("neighbor", "RESIDENTE")
    guard = headers("guard", "GUARDIA")
    assert client.patch("/visitas/atomic/entrada", headers=resident).status_code == 403
    assert client.patch("/visitas/atomic/salida", headers=resident).status_code == 403
    assert client.patch("/visitas/atomic/cancelar", headers=neighbor).status_code == 403
    assert client.patch("/visitas/atomic/cancelar", headers=guard).status_code == 403
    enable_qr(db_session, visita)
    url = "/qr/validar/atomic/valid"
    assert client.get(url, headers=resident).status_code == 403
    assert client.get(url + "?condominio_id=unknown", headers=guard).status_code == 404
    approved = client.get(url, headers=guard)
    assert approved.status_code == 200, approved.text
    entry = db_session.get(Visita, "atomic").entrada_registrada_en
    assert client.get(url, headers=guard).status_code == 400
    assert db_session.get(Visita, "atomic").entrada_registrada_en == entry
    assert len([r for r in records if r["resultado"] == "exito"]) == 1
