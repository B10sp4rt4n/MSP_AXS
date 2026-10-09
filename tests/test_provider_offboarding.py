"""Mixed grant origins, same JWT, atomic audit and idempotent provider exit."""
from datetime import datetime
import pytest
from backend.db.core import (MSP, Condominio, Usuario, UserTenantScope, MSPMembership,
    ScopeStatus, AccessLevel, Visita, Evidencia, EventOutbox)
from backend.db.gov import Authority, AuthorityType
from backend.core.auth.jwt import create_access_token
from backend.services import provider_offboarding as service
from tests.test_recovery_mode import db_engine, db_gov_engine, db_event_engine


@pytest.fixture
def scenario(db_session,db_gov_session):
    db=db_session
    db.add(MSP(msp_id='centinela',nombre='Centinela'));db.flush()
    db.add_all([Condominio(condominio_id=t,msp_id='centinela') for t in ['ensayo','other']]);db.flush()
    for uid,role in [('operator','MSP_ADMIN'),('director','MSP_ADMIN'),('local','ADMIN_CONDOMINIO'),('guard','GUARDIA'),('replacement','GUARDIA'),('resident','RESIDENTE')]:
        db.add(Usuario(usuario_id=uid,email=uid+'@example.invalid',rol=role,condominio_id='ensayo'))
    db.flush()
    db.add(MSPMembership(usuario_id='director',msp_id='centinela'))
    for uid,level in [('local',AccessLevel.ADMIN_CONDOMINIO),('guard',AccessLevel.GUARDIA),('replacement',AccessLevel.GUARDIA),('resident',AccessLevel.RESIDENTE)]:
        db.add(UserTenantScope(usuario_id=uid,tenant_id='ensayo',access_level=level,estado=ScopeStatus.INACTIVO if uid=='replacement' else ScopeStatus.ACTIVO))
    db.add(UserTenantScope(usuario_id='guard',tenant_id='other',access_level=AccessLevel.GUARDIA,
        metadata_json={'grant_origin':{'kind':'msp','msp_id':'centinela'}}))
    db.add(Visita(visita_id='history',condominio_id='ensayo',estado='entrada_registrada',vigencia=datetime.utcnow(),entrada_registrada_en=datetime.utcnow()))
    db.flush();db.add(Evidencia(evidencia_id='proof',visita_id='history',guardia_id='guard',metadata_json={'synthetic':True}));db.commit()
    db_gov_session.add(Authority(authority_id='platform',identity_id='operator',tipo=AuthorityType.GLOBAL));db_gov_session.commit()
    return {u:{'Authorization':'Bearer '+create_access_token(u,r)} for u,r in [('operator','MSP_ADMIN'),('director','MSP_ADMIN'),('local','ADMIN_CONDOMINIO'),('guard','GUARDIA'),('resident','RESIDENTE')]}


def classify_all(client,db,h):
    for row in db.query(UserTenantScope).filter_by(tenant_id='ensayo').all():
        kind='msp' if row.usuario_id in ('guard','replacement') else 'condominio'
        body={'kind':kind,'evidence_ref':'synthetic-contract'}
        if kind=='msp': body['msp_id']='centinela'
        r=client.put(f'/condominios/ensayo/permisos/{row.id}/procedencia',headers=h,json=body)
        assert r.status_code==200,r.text


def leave(client,h):
    return client.post('/condominios/ensayo/proveedor/baja',headers=h,json={'msp_id':'centinela','reason':'Contract ended'})


def test_unknown_denied_then_scoped_atomic_idempotent_exit(client,db_session,scenario):
    db=db_session;h=scenario
    for u in ['operator','director','local','guard']:
        assert client.get('/condominios/ensayo/casas',headers=h[u]).status_code==200
    for u in ['director','local','guard','resident']:
        assert leave(client,h[u]).status_code==403
    denied=leave(client,h['operator']);assert denied.status_code==409
    assert len(denied.json()['detail']['scope_ids'])==4
    assert db.query(Condominio).filter_by(condominio_id='ensayo').one().msp_id=='centinela'
    classify_all(client,db,h['operator'])
    history=db.query(Visita).one().entrada_registrada_en
    result=leave(client,h['operator']);assert result.status_code==200,result.text
    body=result.json();assert len(body['revoked_scope_ids'])==2 and len(body['preserved_scope_ids'])==2
    assert leave(client,h['operator']).json()['event_uid']==body['event_uid']
    audits=[e for e in db.query(EventOutbox) if e.payload['accion']=='baja_proveedor'];assert len(audits)==1
    assert audits[0].payload['identity_id']=='operator'
    for u in ['director','guard']:
        assert client.get('/condominios/ensayo/casas',headers=h[u]).status_code==403
    assert client.get('/condominios/ensayo/casas',headers=h['local']).status_code==200
    assert client.get('/condominios/other/casas',headers=h['director']).status_code==200
    assert client.get('/condominios/other/casas',headers=h['guard']).status_code==200
    assert db.query(UserTenantScope).filter_by(usuario_id='resident').one().estado==ScopeStatus.ACTIVO
    assert db.query(Visita).one().entrada_registrada_en==history and db.query(Evidencia).count()==1
    assert db.query(MSPMembership).one().estado=='activo'


def test_origin_immutable_and_provider_cannot_launder_grants(client,db_session,scenario):
    db=db_session;h=scenario
    classify_all(client,db,h['operator'])
    guard=db.query(UserTenantScope).filter_by(usuario_id='guard',tenant_id='ensayo').one()
    url=f'/condominios/ensayo/permisos/{guard.id}/procedencia'
    body={'kind':'condominio','evidence_ref':'spoof'}
    assert client.put(url,headers=h['director'],json=body).status_code==403
    assert client.put(url,headers=h['operator'],json=body).status_code==409
    r=client.post('/condominios/ensayo/usuarios',headers=h['director'],json={'nombre':'New','email':'new@example.invalid','rol':'GUARDIA'})
    assert r.status_code==200,r.text
    row=db.query(UserTenantScope).filter_by(usuario_id=r.json()['usuario_id']).one()
    assert row.metadata_json['grant_origin']['msp_id']=='centinela'
    r=client.post('/condominios/ensayo/usuarios',headers=h['local'],json={'nombre':'Local','email':'newlocal@example.invalid','rol':'GUARDIA'})
    assert r.status_code==200,r.text
    assert db.query(UserTenantScope).filter_by(usuario_id=r.json()['usuario_id']).one().metadata_json['grant_origin']['kind']=='condominio'


def test_audit_failure_rolls_back_everything(client,db_session,db_gov_session,scenario,monkeypatch):
    db=db_session;classify_all(client,db,scenario['operator'])
    def fail(*a,**k): raise RuntimeError('outbox unavailable')
    monkeypatch.setattr(service,'encolar_evento',fail)
    with pytest.raises(RuntimeError):
        service.offboard(db,db_gov_session,db.query(Usuario).filter_by(usuario_id='operator').one(),'ensayo','centinela','test','token')
    db.rollback()
    assert db.query(Condominio).filter_by(condominio_id='ensayo').one().msp_id=='centinela'
    assert db.query(UserTenantScope).filter_by(usuario_id='guard',tenant_id='ensayo').one().estado==ScopeStatus.ACTIVO


def test_concurrent_offboarding_one_receipt(client,db_session,db_gov_session,scenario):
    if db_session.get_bind().dialect.name!='postgresql': pytest.skip('PostgreSQL row locks required')
    from sqlalchemy.orm import Session
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    classify_all(client,db_session,scenario['operator'])
    db_session.rollback();db_gov_session.rollback()
    barrier=Barrier(2)
    def call(_):
        with Session(db_session.get_bind()) as core, Session(db_gov_session.get_bind()) as gov:
            user=core.query(Usuario).filter_by(usuario_id='operator').one()
            barrier.wait(timeout=10)
            return service.offboard(core,gov,user,'ensayo','centinela','test','token')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(call,range(2)))
    assert results[0]['event_uid']==results[1]['event_uid']
    assert sorted(r['unchanged'] for r in results)==[False,True]


def test_offboarding_waits_for_authorized_operation(client,db_session,db_gov_session,scenario):
    if db_session.get_bind().dialect.name!='postgresql': pytest.skip('PostgreSQL row locks required')
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import OperationalError
    from backend.core.scope.msp_boundary import require_condominio
    from backend.core.security_denial import SecurityDenial
    classify_all(client,db_session,scenario['operator'])
    db_session.rollback();db_gov_session.rollback()
    with Session(db_session.get_bind()) as operation, Session(db_session.get_bind()) as exit_db, Session(db_gov_session.get_bind()) as gov:
        guard=operation.query(Usuario).filter_by(usuario_id='guard').one()
        require_condominio(operation,gov,guard,'ensayo',AccessLevel.GUARDIA)
        operator=exit_db.query(Usuario).filter_by(usuario_id='operator').one()
        exit_db.execute(text("SET LOCAL lock_timeout = '200ms'"))
        with pytest.raises(OperationalError) as blocked:
            service.offboard(exit_db,gov,operator,'ensayo','centinela','test','token')
        assert blocked.value.orig.sqlstate=='55P03'
        exit_db.rollback()
        operation.commit()
        result=service.offboard(exit_db,gov,operator,'ensayo','centinela','test','token')
        assert result['unchanged'] is False
        with pytest.raises(SecurityDenial):
            require_condominio(operation,gov,guard,'ensayo',AccessLevel.GUARDIA)
