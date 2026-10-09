"""Contract succession, stale retries, least privilege and real concurrency."""
from uuid import uuid4
import pytest
from fastapi import HTTPException
from backend.db.core import ProviderContract, Condominio, UserTenantScope, ScopeStatus, Usuario, MSP, EventOutbox
from backend.services import provider_contracts as service
from tests.test_provider_offboarding import scenario, classify_all, leave
from tests.test_recovery_mode import db_engine, db_gov_engine, db_event_engine


@pytest.fixture
def detached(client, db_session, scenario):
    classify_all(client, db_session, scenario['operator'])
    assert leave(client, scenario['operator']).status_code == 200
    return scenario


def opening(client, headers, cid, msp='centinela', tenant='ensayo'):
    return client.post(f'/condominios/{tenant}/proveedor/contratos', headers=headers,
        json={'contract_id': cid, 'msp_id': msp, 'evidence_ref': 'synthetic-contract'})


def closing(client, headers, cid, msp='centinela'):
    return client.post('/condominios/ensayo/proveedor/baja', headers=headers,
        json={'contract_id': cid, 'msp_id': msp, 'reason': 'synthetic-exit'})


def grant(client, headers, cid, user='guard'):
    return client.post(f'/condominios/ensayo/proveedor/contratos/{cid}/personal/{user}',
        headers=headers, json={'evidence_ref': 'synthetic-assignment'})


def test_rehire_requires_new_grant_and_stale_close_cannot_close_new_contract(client, db_session, detached):
    h = detached; operator = h['operator']; first, second = str(uuid4()), str(uuid4())
    old = db_session.query(UserTenantScope).filter_by(usuario_id='guard', tenant_id='ensayo').one()
    assert opening(client, operator, first).json()['version'] == 1
    assert opening(client, operator, first).json()['unchanged'] is True
    assert opening(client, operator, second).status_code == 409
    assert client.get('/condominios/ensayo/casas', headers=h['director']).status_code == 200
    assert client.get('/condominios/ensayo/casas', headers=h['guard']).status_code == 403
    # Even a legacy reactivation cannot carry a prior contract's authority forward.
    old.estado = ScopeStatus.ACTIVO; db_session.commit()
    assert client.get('/condominios/ensayo/casas', headers=h['guard']).status_code == 403
    old.estado = ScopeStatus.REVOCADO; db_session.commit()
    assigned = grant(client, operator, first); assert assigned.status_code == 200, assigned.text
    assert assigned.json()['scope_id'] != old.id
    assert grant(client, operator, first).json()['scope_id'] == assigned.json()['scope_id']
    assert client.get('/condominios/ensayo/casas', headers=h['guard']).status_code == 200
    assert leave(client, operator).status_code == 409
    receipt = closing(client, operator, first); assert receipt.status_code == 200, receipt.text
    assert client.get('/condominios/ensayo/casas', headers=h['guard']).status_code == 403
    assert opening(client, operator, second).json()['version'] == 2
    assert closing(client, operator, first).json()['event_uid'] == receipt.json()['event_uid']
    assert db_session.query(Condominio).filter_by(condominio_id='ensayo').one().msp_id == 'centinela'
    assert grant(client, operator, first).status_code == 409
    assert grant(client, operator, second).status_code == 200
    assert closing(client, operator, second).status_code == 200
    assert opening(client, operator, first).json()['closed_at'] is not None
    assert db_session.query(Condominio).filter_by(condominio_id='ensayo').one().msp_id is None
    rows = client.get('/condominios/ensayo/proveedor/contratos', headers=operator).json()
    assert [r['version'] for r in rows] == [1, 2] and all(r['closed_at'] for r in rows)
    assert client.get('/condominios/ensayo/casas', headers=h['local']).status_code == 200
    assert client.get('/condominios/other/casas', headers=h['guard']).status_code == 200


def test_provider_change_authorization_isolation_and_immutable_keys(client, db_session, detached):
    h = detached; cid = str(uuid4())
    db_session.add(MSP(msp_id='new-provider', nombre='Synthetic new provider')); db_session.commit()
    for who in ('director', 'local', 'guard', 'resident'):
        assert opening(client, h[who], cid).status_code == 403
        assert client.get('/condominios/ensayo/proveedor/contratos', headers=h[who]).status_code == 403
        assert grant(client, h[who], cid).status_code == 403
    assert opening(client, h['operator'], cid, 'new-provider').status_code == 200
    assert opening(client, h['operator'], cid).status_code == 409
    assert opening(client, h['operator'], cid, 'new-provider', 'other').status_code == 409
    assert closing(client, h['operator'], cid).status_code == 409
    assert client.get('/condominios/ensayo/casas', headers=h['director']).status_code == 403
    assert client.get('/condominios/other/casas', headers=h['director']).status_code == 200
    assert grant(client, h['operator'], cid, 'resident').status_code == 409
    assert grant(client, h['operator'], cid, 'local').status_code == 409
    assert closing(client, h['operator'], cid, 'new-provider').status_code == 200


def test_new_personnel_records_contract_and_close_revokes_it(client, db_session, detached):
    h = detached; cid = str(uuid4())
    assert opening(client, h['operator'], cid).status_code == 200
    r = client.post('/condominios/ensayo/usuarios', headers=h['director'],
        json={'nombre': 'Contract guard', 'email': 'contract@example.invalid', 'rol': 'GUARDIA'})
    assert r.status_code == 200, r.text
    scope = db_session.query(UserTenantScope).filter_by(usuario_id=r.json()['usuario_id']).one()
    assert scope.metadata_json['grant_origin']['contract_id'] == cid
    assert closing(client, h['operator'], cid).status_code == 200
    db_session.refresh(scope)
    assert scope.estado == ScopeStatus.REVOCADO


def test_open_failure_atomic_and_unclassified_grants_block(client, db_session, db_gov_session, detached, monkeypatch):
    h = detached; cid = str(uuid4())
    old = db_session.query(UserTenantScope).filter_by(usuario_id='replacement').one()
    old.estado = ScopeStatus.INACTIVO; db_session.commit()
    assert opening(client, h['operator'], cid).status_code == 409
    old.estado = ScopeStatus.REVOCADO; db_session.commit()
    def fail(*args, **kwargs): raise RuntimeError('audit unavailable')
    monkeypatch.setattr(service, 'encolar_evento', fail)
    with pytest.raises(RuntimeError):
        service.open_contract(db_session, db_gov_session, db_session.query(Usuario).filter_by(usuario_id='operator').one(),
            'ensayo', cid, 'centinela', 'synthetic', 'token')
    db_session.rollback()
    assert db_session.query(ProviderContract).count() == 0
    assert db_session.query(Condominio).filter_by(condominio_id='ensayo').one().msp_id is None


def test_concurrent_contract_openings_serialize(client, db_session, db_gov_session, detached):
    if db_session.get_bind().dialect.name != 'postgresql': pytest.skip('PostgreSQL row locks required')
    from sqlalchemy.orm import Session
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    barrier = Barrier(2)
    db_session.rollback(); db_gov_session.rollback()
    def call(cid):
        with Session(db_session.get_bind()) as core, Session(db_gov_session.get_bind()) as gov:
            actor = core.query(Usuario).filter_by(usuario_id='operator').one()
            barrier.wait(timeout=10)
            try:
                return service.open_contract(core, gov, actor, 'ensayo', cid, 'centinela', 'synthetic', 'token')
            except HTTPException as exc:
                core.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(call, [str(uuid4()), str(uuid4())]))
    assert sum(isinstance(r, dict) for r in results) == 1 and 409 in results
    assert db_session.query(ProviderContract).count() == 1


def test_concurrent_same_contract_returns_one_receipt(client, db_session, db_gov_session, detached):
    if db_session.get_bind().dialect.name != 'postgresql': pytest.skip('PostgreSQL row locks required')
    from sqlalchemy.orm import Session
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    barrier = Barrier(2); cid = str(uuid4())
    db_session.rollback(); db_gov_session.rollback()
    def call(_):
        with Session(db_session.get_bind()) as core, Session(db_gov_session.get_bind()) as gov:
            actor = core.query(Usuario).filter_by(usuario_id='operator').one()
            barrier.wait(timeout=10)
            return service.open_contract(core, gov, actor, 'ensayo', cid, 'centinela', 'synthetic', 'token')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(call, range(2)))
    assert results[0]['open_event_uid'] == results[1]['open_event_uid']
    assert sorted(r['unchanged'] for r in results) == [False, True]
