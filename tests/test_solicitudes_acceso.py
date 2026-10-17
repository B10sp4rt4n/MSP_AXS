"""Synthetic HTTP integration; no production users, messages or databases."""
from datetime import datetime, timedelta
import uuid
import pytest
from backend.db.core import SolicitudAcceso, Visita, Usuario, UserTenantScope, ScopeStatus, AccessLevel, EventOutbox
from tests.test_reglas_acceso import db_engine, setup, headers, pending, rules


def body(**changes):
    return {"solicitud_id": str(uuid.uuid4()), "destino_id": "home", "nombre_visitante": "Ana Pérez",
            "tipo_visita": "proveedor", "proposito": "Reparación", **changes}


def create(client, **changes):
    r = client.post('/solicitudes-acceso/a', json=body(**changes), headers=headers('guard', 'GUARDIA'))
    assert r.status_code == 200, r.text
    return r.json()


def reply(client, row, decision='permitida', user='resident', **changes):
    return client.post(f'/solicitudes-acceso/a/{row["solicitud_id"]}/respuesta',
        json={"decision": decision, "consentimiento": True, **changes}, headers=headers(user, 'RESIDENTE'))


def entry(client, row):
    return client.patch(f'/visitas/{row["visita_id"]}/entrada', headers=headers('guard', 'GUARDIA'))


def test_approve_is_not_entry_and_guard_confirms_once(client, setup):
    rules(client, exigir_autorizacion=True, exigir_proposito=True)
    row = create(client)
    assert entry(client, row).status_code == 403
    assert reply(client, row).status_code == 200
    visit = setup.query(Visita).one()
    assert visit.entrada_registrada_en is None and visit.qr_token is None
    assert visit.autorizada_por == 'resident'
    assert entry(client, row).status_code == 200
    assert entry(client, row).status_code == 400
    assert setup.query(SolicitudAcceso).one().estado == 'consumida'
    actions = [e.payload['accion'] for e in setup.query(EventOutbox).all() if e.payload['entidad'] == 'solicitud_acceso']
    assert actions == ['solicitar', 'responder', 'consumir']


def test_rejection_blocks_entry_even_without_optional_rules(client, setup):
    row = create(client)
    assert reply(client, row, 'rechazada').status_code == 200
    assert entry(client, row).status_code == 403
    assert reply(client, row).status_code == 409
    assert client.post('/solicitudes-acceso/a', json=body(), headers=headers('guard', 'GUARDIA')).status_code == 409
    assert setup.query(Visita).one().entrada_registrada_en is None


@pytest.mark.parametrize('approve', [False, True])
def test_no_response_or_expired_approval_never_admits(client, setup, approve):
    row = create(client)
    if approve:
        assert reply(client, row).status_code == 200
    r = setup.query(SolicitudAcceso).one()
    r.expira_en = datetime.utcnow() - timedelta(seconds=1)
    setup.commit()
    assert entry(client, row).status_code == 403
    assert reply(client, row).status_code == 409
    assert setup.query(SolicitudAcceso).one().estado == 'expirada'
    assert setup.query(Visita).one().entrada_registrada_en is None
    # Explicit new request reuses the same visit; old decision cannot affect it.
    renewed = create(client)
    assert renewed['visita_id'] == row['visita_id']
    assert renewed['solicitud_id'] != row['solicitud_id']
    assert entry(client, renewed).status_code == 403
    assert reply(client, row).status_code == 409


def test_lost_create_and_reply_responses_recover_without_duplicates(client, setup):
    payload = body()
    url = '/solicitudes-acceso/a'
    first = client.post(url, json=payload, headers=headers('guard', 'GUARDIA')).json()
    # The HTTP caller discards the committed response, then retries exact ID/body.
    retry = client.post(url, json=payload, headers=headers('guard', 'GUARDIA'))
    assert retry.status_code == 200 and retry.json() == first
    assert reply(client, first).status_code == 200
    assert reply(client, first).status_code == 200
    assert reply(client, first, 'rechazada').status_code == 409
    assert setup.query(Visita).count() == 1 and setup.query(SolicitudAcceso).count() == 1
    assert setup.query(EventOutbox).count() == 2
    assert client.get(url, headers=headers('guard', 'GUARDIA')).json()[0]['estado'] == 'permitida'
    assert setup.query(Visita).one().entrada_registrada_en is None


def test_lost_entry_response_readback_no_duplicate(client, setup):
    row = create(client)
    reply(client, row)
    assert entry(client, row).status_code == 200
    readback = client.get(f'/visitas/{row["visita_id"]}', headers=headers('guard', 'GUARDIA')).json()
    assert readback['entrada_registrada_en'] is not None
    assert entry(client, row).status_code == 400
    assert setup.query(SolicitudAcceso).one().estado == 'consumida'


def test_same_key_cannot_change_destination_or_person(client, setup):
    payload = body()
    r = client.post('/solicitudes-acceso/a', json=payload, headers=headers('guard', 'GUARDIA'))
    assert r.status_code == 200
    for changes in [{'destino_id':'other'}, {'nombre_visitante':'Otra Persona'}, {'proposito':'Otro motivo'}]:
        assert client.post('/solicitudes-acceso/a', json={**payload, **changes}, headers=headers('guard', 'GUARDIA')).status_code == 409
    assert setup.query(Visita).one().destino_id == 'home'


@pytest.mark.parametrize('qr_state', ['pendiente', 'activa'])
def test_no_qr_replacement_even_if_expired_or_spelling_case_changes(client, setup, qr_state):
    pending(setup, nombre_visitante='ANA PEREZ', proposito='Reparación', qr_token='required',
            qr_vigencia=datetime.utcnow()-timedelta(hours=1), estado=qr_state)
    r = client.post('/solicitudes-acceso/a', json=body(), headers=headers('guard', 'GUARDIA'))
    assert r.status_code == 409
    assert setup.query(SolicitudAcceso).count() == 0
    assert setup.query(Visita).count() == 1


def test_existing_non_qr_reuses_destination_and_visit(client, setup):
    pending(setup, nombre_visitante='Ana Pérez', proposito='Reparación')
    row = create(client, visita_id='old')
    assert row['visita_id'] == 'old' and setup.query(Visita).count() == 1
    assert row['destino_id'] == 'home'


def test_other_destination_and_tenant_denied(client, setup):
    row = create(client)
    assert client.get('/solicitudes-acceso/b', headers=headers('guard', 'GUARDIA')).status_code == 403
    assert client.post('/solicitudes-acceso/b', json=body(), headers=headers('guard', 'GUARDIA')).status_code == 403
    for destination in ['OTRO', 'unknown', 'other']:
        assert client.post('/solicitudes-acceso/a', json=body(destino_id=destination), headers=headers('guard', 'GUARDIA')).status_code in [400,409]
    resident = setup.query(Usuario).filter_by(usuario_id='resident').one()
    resident.casa_id = 'other'; resident.casa_unidad = '102'; setup.commit()
    assert client.get('/solicitudes-acceso/a', headers=headers('resident','RESIDENTE')).json() == []
    assert client.get(f'/solicitudes-acceso/a/{row["solicitud_id"]}', headers=headers('resident','RESIDENTE')).status_code == 404
    assert reply(client,row).status_code == 403


@pytest.mark.parametrize('change', ['scope','home','role','contract'])
def test_permission_revocation_after_approval_blocks_entry(client, setup, change):
    row = create(client)
    assert reply(client, row).status_code == 200
    user = setup.query(Usuario).filter_by(usuario_id='resident').one()
    scope = setup.query(UserTenantScope).filter_by(usuario_id='resident').one()
    if change == 'scope': scope.estado = ScopeStatus.REVOCADO
    if change == 'home': user.casa_id = 'other'
    if change == 'role': user.rol = 'GUARDIA'
    if change == 'contract': scope.metadata_json = {'grant_origin': {'kind':'msp','msp_id':'stale','contract_id':'old'}}
    setup.commit()
    assert entry(client, row).status_code == 403
    assert setup.query(Visita).one().entrada_registrada_en is None


def test_only_initial_authorized_recipients_can_respond(client, setup):
    row = create(client)
    setup.add(Usuario(usuario_id='new', rol='RESIDENTE', email='new@test', condominio_id='a', casa_id='home', casa_unidad='101'))
    setup.flush()
    setup.add(UserTenantScope(usuario_id='new', tenant_id='a', access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO))
    setup.commit()
    assert reply(client, row, user='new').status_code == 403
    assert client.get('/solicitudes-acceso/a', headers=headers('new','RESIDENTE')).json() == []


def test_two_residents_first_decision_wins(client, setup):
    setup.add(Usuario(usuario_id='second', rol='RESIDENTE', email='second@test', condominio_id='a', casa_id='home', casa_unidad='101'))
    setup.flush()
    setup.add(UserTenantScope(usuario_id='second', tenant_id='a', access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO))
    setup.commit()
    row = create(client)
    assert len(setup.query(SolicitudAcceso).one().destinatarios) == 2
    assert reply(client, row, 'rechazada', user='second').status_code == 200
    assert reply(client, row).status_code == 409
    assert entry(client,row).status_code == 403


@pytest.mark.parametrize('consent', [False, 'true', 1, None])
def test_explicit_consent_required(client, setup, consent):
    row = create(client)
    assert reply(client, row, consentimiento=consent).status_code == 422
    assert setup.query(SolicitudAcceso).one().estado == 'pendiente'


def test_guard_cannot_decide_and_legacy_approval_cannot_bypass(client, setup):
    row = create(client)
    assert reply(client, row, user='guard').status_code == 403
    for user, role in [('resident','RESIDENTE'),('admin','ADMIN_CONDOMINIO')]:
        assert client.patch(f'/visitas/{row["visita_id"]}/autorizar', json={}, headers=headers(user,role)).status_code == 409
    assert entry(client,row).status_code == 403


def test_audit_failure_rolls_back_business(client, setup, monkeypatch):
    from backend.services import solicitudes_acceso as service
    from fastapi import HTTPException
    def fail(*args, **kwargs): raise HTTPException(503, 'Synthetic audit outage')
    monkeypatch.setattr(service, 'auditar', fail)
    result = client.post('/solicitudes-acceso/a', json=body(), headers=headers('guard','GUARDIA'))
    assert result.status_code == 503
    setup.rollback()  # request session close would rollback in production
    assert setup.query(Visita).count() == 0
    assert setup.query(SolicitudAcceso).count() == 0


def test_inbox_recovered_after_app_reload(client, setup):
    row = create(client)
    r = client.get('/solicitudes-acceso/a', headers=headers('resident','RESIDENTE'))
    assert r.status_code == 200 and r.headers['cache-control'] == 'private, no-store'
    assert r.json()[0]['solicitud_id'] == row['solicitud_id']
    assert 'destinatarios' not in r.json()[0]
    assert client.get('/solicitudes-acceso/a').status_code == 401


def test_postgres_two_residents_cannot_overwrite_decision(setup):
    if setup.get_bind().dialect.name != 'postgresql':
        pytest.skip('PostgreSQL required for independent concurrent sessions')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    from fastapi import HTTPException
    from backend.services import solicitudes_acceso as service
    from backend.services.reglas_acceso import obtener_reglas
    from backend.services.event_outbox import contexto_evento
    from backend.schemas.solicitud_acceso import SolicitarAcceso, ResponderAcceso
    setup.add(Usuario(usuario_id='second', rol='RESIDENTE', email='second@test', condominio_id='a', casa_id='home', casa_unidad='101'))
    setup.flush()
    setup.add(UserTenantScope(usuario_id='second', tenant_id='a', access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO))
    setup.commit()
    guard = setup.query(Usuario).filter_by(usuario_id='guard').one()
    obtener_reglas(setup, 'a', bloquear=True)
    row = service.crear(setup, 'a', SolicitarAcceso(**body()), guard, contexto_evento(guard,'test'))
    barrier = Barrier(2)
    def answer(args):
        user_id, decision = args
        with Session(setup.get_bind()) as db:
            user = db.query(Usuario).filter_by(usuario_id=user_id).one()
            barrier.wait(timeout=10)
            obtener_reglas(db,'a',bloquear=True)
            request = service.obtener(db,'a',row['solicitud_id'])
            try:
                service.responder(db,request,ResponderAcceso(decision=decision,consentimiento=True),user,contexto_evento(user,'test'))
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(answer,[('resident','permitida'),('second','rechazada')]))
    assert sorted(results) == [200,409]
    setup.expire_all()
    assert setup.query(Visita).one().entrada_registrada_en is None
    assert setup.query(EventOutbox).count() == 2
