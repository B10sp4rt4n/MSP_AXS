import uuid
from datetime import datetime, timedelta, timezone
import pytest
from tests.test_destinos_visitas import people, headers
from backend.db.core import EventOutbox
from backend.db.core.models import ArcoCase


@pytest.fixture
def arco(people, monkeypatch):
    monkeypatch.setenv('AXS_ARCO_CASES_ENABLED', 'true')
    monkeypatch.setenv('AXS_ARCO_OPERATORS', 'admin:a1,msp:a1')
    return people


def body():
    return {'request_id': str(uuid.uuid4()), 'received_at': datetime.now(timezone.utc).isoformat(),
            'determination_due': (datetime.now(timezone.utc)+timedelta(days=20)).isoformat(),
            'right': 'cancelacion', 'subject_ref': 'SYNTHETIC_001', 'owner_id': 'privacy_owner'}


def test_private_lifecycle_and_minimal_audit(client, arco):
    b=body(); h=headers('admin','ADMIN_CONDOMINIO')
    r=client.post('/arco/a1',json=b,headers=h)
    assert r.status_code==200,r.text
    assert r.headers['cache-control']=='private, no-store'
    assert client.post('/arco/a1',json=b,headers=h).json()==r.json()
    assert arco.query(ArcoCase).count()==1 and arco.query(EventOutbox).count()==1
    url='/arco/a1/'+b['request_id']+'/estado'
    def change(version,state,**kw):
        return client.post(url,headers=h,json={'version':version,'state':state,'reference':'EVIDENCE_001',**kw})
    assert change(1,'cerrada',communication_ref='REPLY').status_code==409
    assert change(1,'verificada').status_code==200
    assert change(1,'resuelta').status_code==409
    assert change(2,'resuelta',outcome='procedente').status_code==422
    assert change(2,'resuelta',outcome='procedente',communication_ref='DECISION',
                  execution_due=(datetime.now(timezone.utc)+timedelta(days=15)).isoformat(),pending_actions=2).status_code==200
    assert change(3,'ejecutando',pending_actions=1).status_code==200
    assert change(4,'cerrada',pending_actions=1,communication_ref='REPLY').status_code==422
    assert change(4,'cerrada').status_code==422
    closed=change(4,'cerrada',communication_ref='REPLY')
    assert closed.status_code==200 and closed.json()['state']=='cerrada'
    assert change(5,'verificada').status_code==409
    payloads=str([r.payload for r in arco.query(EventOutbox).all()])
    assert 'SYNTHETIC_001' not in payloads and 'EVIDENCE_001' not in payloads
    assert len(closed.json()['history'])==4


def test_private_selector_preserves_residential_access(client, arco):
    response = client.get('/arco-clientes', headers=headers('admin', 'ADMIN_CONDOMINIO'))
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'private, no-store'
    assert {item['tenant_id'] for item in response.json()} == {'a1'}
    assert {item['modalidad'] for item in response.json()} == {'residencial'}


@pytest.mark.parametrize('user,role,tenant',[('guard','GUARDIA','a1'),('resident','RESIDENTE','a1'),('admin','ADMIN_CONDOMINIO','b1'),('msp','MSP_ADMIN','b1')])
def test_scope_and_roles(client,arco,user,role,tenant):
    assert client.get('/arco/'+tenant,headers=headers(user,role)).status_code==403
    assert client.post('/arco/'+tenant,json=body(),headers=headers(user,role)).status_code==403


def test_designation_flag_and_anonymous(client,arco,monkeypatch):
    assert client.get('/arco/a1').status_code in (401,403)
    monkeypatch.setenv('AXS_ARCO_OPERATORS','')
    assert client.get('/arco/a1',headers=headers('admin','ADMIN_CONDOMINIO')).status_code==403
    monkeypatch.setenv('AXS_ARCO_CASES_ENABLED','false')
    assert client.get('/arco/a1',headers=headers('admin','ADMIN_CONDOMINIO')).status_code==404


def test_dates_conflict_and_no_extra_fields(client,arco):
    h=headers('admin','ADMIN_CONDOMINIO'); b=body()
    bad={**b,'received_at':'2026-01-01T00:00:00'}
    assert client.post('/arco/a1',json=bad,headers=h).status_code==422
    assert client.post('/arco/a1',json={**b,'photo':'forbidden'},headers=h).status_code==422
    assert client.post('/arco/a1',json=b,headers=h).status_code==200
    assert client.post('/arco/a1',json={**b,'subject_ref':'OTHER'},headers=h).status_code==409
    assert client.get('/arco/a1?limit=101',headers=h).status_code==422


def test_atomic_audit_failure(client,arco,monkeypatch):
    from backend.routers import arco_router
    def fail(*args,**kwargs):
        raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(arco_router,'encolar_evento',fail)
    with pytest.raises(RuntimeError,match='synthetic audit failure'):
        client.post('/arco/a1',json=body(),headers=headers('admin','ADMIN_CONDOMINIO'))
    arco.rollback()
    assert arco.query(ArcoCase).count()==0
