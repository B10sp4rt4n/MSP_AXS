"""Fault injection through HTTP; PG counterpart uses independent durable stores."""
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from backend.db.core import Base_CORE, EventOutbox
from backend.db.core.corporate_operations import CorporateProvisioningOperation as Operation
from backend.db.gov import Policy
from backend.routers import corporate_superadmin_router as router
from tests.test_corporate_superadmin import company_setup, _audit_corporate_quota_setup


def setup(company_setup, monkeypatch):
    client, core, gov, auth, tenant, base, payload = _audit_corporate_quota_setup(company_setup, monkeypatch)
    return client, core, gov, auth, tenant, base, payload


def actions(core):
    return [r.payload['accion'] for r in core.query(EventOutbox).all()]


@pytest.mark.parametrize('database,commit_number,after', [
    ('core',1,False), ('core',1,True), ('gov',1,False),
    ('gov',1,True), ('core',2,False), ('core',2,True),
])
def test_retry_repairs_every_commit_boundary(company_setup, monkeypatch, database, commit_number, after):
    client, core, gov, auth, tenant, base, payload = setup(company_setup, monkeypatch)
    db = core if database == 'core' else gov
    original, count = db.commit, 0
    def fail_once():
        nonlocal count
        count += 1
        if count == commit_number:
            if after:
                original()
            raise RuntimeError('synthetic lost commit ACK' if after else 'synthetic precommit failure')
        return original()
    monkeypatch.setattr(db, 'commit', fail_once)
    first = client.put(base+'/capacidades', headers=auth('super'), json=payload)
    assert first.status_code == 503, first.text
    assert first.json()['detail']['request_id'] == payload['request_id']
    retry = client.put(base+'/capacidades', headers=auth('super'), json=payload)
    assert retry.status_code == 200, retry.text
    assert retry.json()['estado'] == 'confirmed'
    assert actions(core).count('solicitar_capacidades_directorio') == 1
    assert actions(core).count('confirmar_capacidades_directorio') == 1
    operation = core.query(Operation).filter_by(tenant_id=tenant).one()
    assert operation.estado == 'confirmed'
    assert operation.request_event_uid and operation.confirmation_event_uid
    assert client.get(base,headers=auth('super')).json()['capacidades_confirmadas'] is True
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code == 200
    assert actions(core).count('confirmar_capacidades_directorio') == 1


def test_pending_blocks_activation_and_different_intentions(company_setup, monkeypatch):
    client, core, gov, auth, tenant, base, payload = setup(company_setup, monkeypatch)
    original = router.audit
    def fail_confirmation(*args, **kwargs):
        if args[4] == 'confirmar_capacidades_directorio':
            raise RuntimeError('synthetic confirmation unavailable')
        return original(*args, **kwargs)
    monkeypatch.setattr(router,'audit',fail_confirmation)
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code == 503
    status = client.get(base,headers=auth('super')).json()
    assert status['capacidades'] == {k:payload[k] for k in ('max_sedes','max_destinos_por_sede')}
    assert status['capacidades_confirmadas'] is False
    assert status['capacidades_operacion']['estado'] == 'pending'
    assert status['capacidades_operacion']['request_id'] == payload['request_id']
    assert client.post(base+'/habilitar-directorio',headers=auth('super'),json={'confirmacion':True}).status_code == 409
    different = {**payload,'request_id':str(uuid4()),'expected_revision':1}
    assert client.put(base+'/capacidades',headers=auth('super'),json=different).status_code == 409
    assert actions(core).count('solicitar_capacidades_directorio') == 1
    monkeypatch.setattr(router,'audit',original)
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code == 200


def test_idempotency_conflict_stale_revision_and_aba(company_setup, monkeypatch):
    client, core, gov, auth, tenant, base, a = setup(company_setup, monkeypatch)
    put=lambda p:client.put(base+'/capacidades',headers=auth('super'),json=p)
    assert put(a).status_code == 200
    assert put({**a,'max_sedes':3}).status_code == 409
    assert put({**a,'request_id':str(uuid4())}).status_code == 409
    b={**a,'request_id':str(uuid4()),'expected_revision':1,'max_sedes':3}
    c={**a,'request_id':str(uuid4()),'expected_revision':2}
    assert put(b).status_code == 200
    assert put(c).status_code == 200
    before=[deepcopy(p.metadata_json) for p in gov.query(Policy).all()]
    assert put(a).status_code == 409
    assert [p.metadata_json for p in gov.query(Policy).all()] == before
    assert core.query(Operation).count() == 3
    assert actions(core).count('solicitar_capacidades_directorio') == 3
    assert actions(core).count('confirmar_capacidades_directorio') == 3


@pytest.mark.parametrize('drift',['quota','marker','partial_marker','expiry'])
def test_pending_gov_drift_becomes_visible_needs_review(company_setup, monkeypatch, drift):
    client, core, gov, auth, tenant, base, payload=setup(company_setup,monkeypatch)
    original=router.audit
    def fail_confirmation(*args,**kwargs):
        if args[4]=='confirmar_capacidades_directorio':raise RuntimeError('synthetic failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(router,'audit',fail_confirmation)
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code==503
    monkeypatch.setattr(router,'audit',original)
    rows=gov.query(Policy).order_by(Policy.policy_id).all()
    if drift=='quota':rows[0].limites={'max_count':99}
    elif drift=='expiry':rows[0].valida_hasta=datetime.utcnow()-timedelta(days=1)
    elif drift=='partial_marker':rows[0].metadata_json={}
    else:
        for row in rows:row.metadata_json={'axs_corporate_operation':{'request_id':str(uuid4())}}
    gov.commit()
    expected=router.quota_snapshot({r.policy_id:r for r in rows})
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code==409
    assert core.query(Operation).one().estado=='needs_review'
    assert actions(core).count('conflicto_capacidades_directorio')==1
    assert actions(core).count('confirmar_capacidades_directorio')==0
    assert router.quota_snapshot({r.policy_id:r for r in gov.query(Policy).all()})==expected
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code==409
    assert actions(core).count('conflicto_capacidades_directorio')==1
    status=client.get(base,headers=auth('super')).json()
    assert status['capacidades_operacion']['estado']=='needs_review'
    assert status['capacidades_confirmadas'] is False


def test_legacy_quota_pair_needs_new_explicit_confirmation(company_setup,monkeypatch):
    client,core,gov,auth,tenant,base,payload=setup(company_setup,monkeypatch)
    for action,field in [('crear_sede_corporativa','max_sedes'),('crear_destino_corporativo','max_destinos_por_sede')]:
        gov.add(Policy(policy_id=router.policy_key(tenant,action),nombre=action,
            ambito=router.PolicyScope.TENANT,target_tenant_id=tenant,accion_objetivo=action,
            limites={'max_count':payload[field]}))
    gov.commit()
    status=client.get(base,headers=auth('super')).json()
    assert status['capacidades_confirmadas'] is False
    assert status['capacidades_revision']==0
    assert status['capacidades_operacion'] is None
    assert client.post(base+'/habilitar-directorio',headers=auth('super'),json={'confirmacion':True}).status_code==409
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code==200
    assert actions(core).count('solicitar_capacidades_directorio')==1
    assert actions(core).count('confirmar_capacidades_directorio')==1


def test_journal_cannot_be_created_by_legacy_startup():
    assert 'corporate_provisioning_operations' not in Base_CORE.metadata.tables


@pytest.mark.parametrize('metadata',[['legacy'], 'legacy', 7])
def test_invalid_legacy_metadata_rejected_before_intent(company_setup,monkeypatch,metadata):
    client,core,gov,auth,tenant,base,payload=setup(company_setup,monkeypatch)
    gov.add(Policy(policy_id=router.policy_key(tenant,'crear_sede_corporativa'),nombre='Legacy',
        ambito=router.PolicyScope.TENANT,target_tenant_id=tenant,accion_objetivo='crear_sede_corporativa',
        limites={'max_count':2},metadata_json=metadata))
    gov.commit()
    response=client.put(base+'/capacidades',headers=auth('super'),json=payload)
    assert response.status_code==409
    assert core.query(Operation).count()==0
    assert actions(core).count('solicitar_capacidades_directorio')==0
    assert gov.query(Policy).one().metadata_json==metadata


@pytest.mark.parametrize('field,value',[('max_sedes',True),('max_destinos_por_sede','5'),('expected_revision',False)])
def test_corporate_operation_rejects_ambiguous_types(company_setup,monkeypatch,field,value):
    client,core,gov,auth,tenant,base,payload=setup(company_setup,monkeypatch)
    response=client.put(base+'/capacidades',headers=auth('super'),json={**payload,field:value})
    assert response.status_code==422
    assert core.query(Operation).count()==0


def test_missing_journal_schema_does_not_report_success(company_setup,monkeypatch):
    client,core,gov,auth,tenant,base,payload=setup(company_setup,monkeypatch)
    Operation.__table__.drop(core.bind)
    assert client.get(base,headers=auth('super')).status_code==503
    core.rollback()
    assert client.put(base+'/capacidades',headers=auth('super'),json=payload).status_code==503
    assert gov.query(Policy).count()==0


@pytest.mark.parametrize('drift',['metadata','binding'])
def test_post_gov_commit_invalid_policy_is_reviewable_not_invisible(company_setup,monkeypatch,drift):
    client,core,gov,auth,tenant,base,payload=setup(company_setup,monkeypatch)
    original,armed=gov.commit,[True]
    def commit_then_external_change():
        original()
        if armed[0]:
            armed[0]=False
            policy=gov.query(Policy).first()
            if drift=='metadata':policy.metadata_json=['invalid']
            else:policy.target_tenant_id='other-tenant'
            original()
    monkeypatch.setattr(gov,'commit',commit_then_external_change)
    response=client.put(base+'/capacidades',headers=auth('super'),json=payload)
    assert response.status_code==409
    assert core.query(Operation).one().estado=='needs_review'
    assert actions(core).count('confirmar_capacidades_directorio')==0
    assert actions(core).count('conflicto_capacidades_directorio')==1
    status=client.get(base,headers=auth('super'))
    assert status.status_code==200,status.text
    assert status.json()['capacidades_operacion']['estado']=='needs_review'
    assert status.json()['capacidades_confirmadas'] is False
