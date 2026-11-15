from uuid import uuid4

import pytest
from backend.db.core import (Usuario, CorporateMembership, CorporateSiteAssignment,
                             CorporateSite, CorporateDestination, EventOutbox)
from backend.db.core.corporate_visits import CorporateVisit, CorporateVisitBase
from tests.test_corporate_superadmin import company_setup  # noqa: F401


@pytest.fixture
def visit_setup(company_setup, monkeypatch):
    client, db, gov, template, auth = company_setup
    for flag in ("AXS_CORPORATE_PROVISIONING_ENABLED", "AXS_CORPORATE_API_ENABLED", "AXS_CORPORATE_VISITS_ENABLED"):
        monkeypatch.setenv(flag, "true")
    CorporateVisitBase.metadata.create_all(db.bind)
    db.add_all([Usuario(usuario_id=u, email=u+"@example.test", rol="RESIDENTE")
                for u in ("host_a", "host_b", "reception")])
    db.commit()
    tenant = client.post('/plataforma/corporativo/empresas', headers=auth('super'),
                         json={**template, 'request_id':str(uuid4())}).json()['tenant_id']
    from backend.db.core import Condominio
    db.query(Condominio).filter_by(condominio_id=tenant).one().corporativo_habilitado = True
    db.add_all([CorporateSite(site_id=s, tenant_id=tenant, nombre=s) for s in ('s1','s2')])
    db.flush()
    db.add_all([CorporateDestination(destination_id=d,site_id=s,tenant_id=tenant,nombre=d)
                for d,s in [('d1','s1'),('d2','s2')]])
    for u,role in [('host_a','host'),('host_b','host'),('reception','reception')]:
        db.add(CorporateMembership(membership_id=u, tenant_id=tenant,user_id=u,rol=role))
        db.flush()
        db.add(CorporateSiteAssignment(assignment_id=u,tenant_id=tenant,site_id='s1',user_id=u))
    db.commit()
    root=f'/corporativo/{tenant}/sedes/s1/visitas'
    body={'request_id':str(uuid4()),'destination_id':'d1','host_user_id':'host_a','visitor_ref':'synthetic_visitor'}
    return client,db,auth,tenant,root,body


def test_complete_corporate_cycle_and_idempotent_audit(visit_setup):
    client,db,auth,tenant,root,body=visit_setup
    created=client.post(root,headers=auth('reception'),json=body)
    assert created.status_code==201,created.text
    assert created.json()['state']=='preregistrada'
    assert client.post(root,headers=auth('reception'),json=body).json()==created.json()
    path=root+'/'+body['request_id']
    assert client.patch(path+'/entrada',headers=auth('reception')).status_code==409
    for action,actor,state in [('autorizar','host_a','autorizada'),('entrada','reception','dentro'),('salida','reception','cerrada')]:
        response=client.patch(path+'/'+action,headers=auth(actor))
        assert response.status_code==200,response.text
        assert response.json()['state']==state
        assert client.patch(path+'/'+action,headers=auth(actor)).json()==response.json()
    events=client.get(path+'/bitacora',headers=auth('host_a'))
    assert events.status_code==200,events.text
    assert [r['action'] for r in events.json()]==['preregistrar','autorizar','entrada','salida']
    assert db.query(CorporateVisit).count()==1
    assert all('synthetic_visitor' not in str(r.payload) for r in db.query(EventOutbox))
    assert client.patch(path+'/entrada',headers=auth('reception')).status_code==409


@pytest.mark.parametrize('actor',['super','provider','host_b'])
def test_read_scope_and_authorization_denied(visit_setup,actor):
    client,db,auth,tenant,root,body=visit_setup
    assert client.post(root,headers=auth('host_a'),json=body).status_code==201
    path=root+'/'+body['request_id']
    assert client.get(path,headers=auth(actor)).status_code in (403,404)
    assert client.patch(path+'/autorizar',headers=auth(actor)).status_code in (403,404)
    assert client.get(path+'/bitacora',headers=auth(actor)).status_code in (403,404)


def test_flags_revocation_and_role_boundaries(visit_setup,monkeypatch):
    client,db,auth,tenant,root,body=visit_setup
    monkeypatch.delenv('AXS_CORPORATE_VISITS_ENABLED')
    assert client.post(root,headers=auth('host_a'),json=body).status_code==404
    monkeypatch.setenv('AXS_CORPORATE_VISITS_ENABLED','true')
    assert client.post(root,headers=auth('host_a'),json=body).status_code==201
    path=root+'/'+body['request_id']
    assert client.patch(path+'/autorizar',headers=auth('reception')).status_code==403
    assert client.patch(path+'/entrada',headers=auth('host_a')).status_code==403
    assert client.patch(path+'/autorizar',headers=auth('host_a')).status_code==200
    db.query(CorporateMembership).filter_by(user_id='host_a').one().estado='revocado'
    db.commit()
    assert client.get(path,headers=auth('host_a')).status_code==403
    assert client.patch(path+'/entrada',headers=auth('reception')).status_code==409


def test_wrong_destination_id_conflict_cancel_and_site_assignment(visit_setup):
    client,db,auth,tenant,root,body=visit_setup
    assert client.post(root,headers=auth('host_a'),json={**body,'destination_id':'d2'}).status_code==404
    assert client.post(root,headers=auth('host_b'),json=body).status_code==403
    assert client.post(root,headers=auth('reception'),json=body).status_code==201
    assert client.post(root,headers=auth('reception'),json={**body,'visitor_ref':'different'}).status_code==409
    path=root+'/'+body['request_id']
    assert client.patch(path+'/cancelar',headers=auth('host_a')).status_code==200
    assert client.patch(path+'/autorizar',headers=auth('host_a')).status_code==409
    assert client.get(root.replace('s1','s2'),headers=auth('reception')).status_code==403


def test_audit_failure_rolls_back_visit_and_movement(visit_setup,monkeypatch):
    from backend.routers import corporate_visits_router as router
    client,db,auth,tenant,root,body=visit_setup
    original=router.audit
    def fail(*args): raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(router,'audit',fail)
    with pytest.raises(RuntimeError): client.post(root,headers=auth('host_a'),json=body)
    assert db.query(CorporateVisit).count()==0
    monkeypatch.setattr(router,'audit',original)
    assert client.post(root,headers=auth('host_a'),json=body).status_code==201
    monkeypatch.setattr(router,'audit',fail)
    with pytest.raises(RuntimeError): client.patch(root+'/'+body['request_id']+'/autorizar',headers=auth('host_a'))
    assert db.query(CorporateVisit).one().state=='preregistrada'


def test_capabilities_only_list_scoped_hosts(visit_setup):
    client,db,auth,tenant,root,body=visit_setup
    caps=client.get(root+'/capacidades',headers=auth('host_a'))
    assert caps.status_code==200,caps.text
    assert [h['user_id'] for h in caps.json()['hosts']]==['host_a']
    assert caps.json()['can_authorize'] and not caps.json()['can_record_movement']


def test_privacy_requires_designation_and_survives_business_suspension(visit_setup,monkeypatch):
    from backend.db.core import Condominio
    client,db,auth,tenant,root,body=visit_setup
    assert client.post(root,headers=auth('host_a'),json=body).status_code==201
    path=f'/arco-corporativo/{tenant}/visitas?subject_ref=synthetic_visitor'
    assert client.get(path,headers=auth('owner')).status_code==403
    monkeypatch.setenv('AXS_ARCO_OPERATORS',f'owner:{tenant}')
    monkeypatch.setenv('AXS_CORPORATE_VISITS_ENABLED','false')
    monkeypatch.setenv('AXS_CORPORATE_API_ENABLED','false')
    db.query(Condominio).filter_by(condominio_id=tenant).one().corporativo_habilitado=False
    db.commit()
    response=client.get(path,headers=auth('owner'))
    assert response.status_code==200,response.text
    assert [v['visit_id'] for v in response.json()]==[body['request_id']]
    assert 'no-store' in response.headers['cache-control']
    assert client.get(path.replace('synthetic_visitor','another'),headers=auth('owner')).json()==[]
    assert client.get(path,headers=auth('host_a')).status_code==403


@pytest.mark.parametrize('movement,after_commit',[(False,False),(False,True),(True,False),(True,True)])
def test_lost_commit_ack_retries_without_duplicate_events(visit_setup,monkeypatch,movement,after_commit):
    client,db,auth,tenant,root,body=visit_setup
    if movement:
        assert client.post(root,headers=auth('host_a'),json=body).status_code==201
    original=db.commit
    def fail():
        if after_commit: original()
        raise RuntimeError('synthetic commit boundary')
    monkeypatch.setattr(db,'commit',fail)
    request=lambda:client.patch(root+'/'+body['request_id']+'/autorizar',headers=auth('host_a')) if movement else client.post(root,headers=auth('host_a'),json=body)
    with pytest.raises(RuntimeError): request()
    monkeypatch.setattr(db,'commit',original)
    retry=request()
    assert retry.status_code in (200,201),retry.text
    assert db.query(CorporateVisit).count()==1
    events=[r for r in db.query(EventOutbox) if r.payload['entidad']=='visita_corporativa']
    assert [r.payload['accion'] for r in events]==(['preregistrar','autorizar'] if movement else ['preregistrar'])


def test_cross_company_and_revoked_reception_do_not_disclose_visit(visit_setup):
    from backend.db.core import Condominio,CorporateOrganization
    client,db,auth,tenant,root,body=visit_setup
    db.add(Condominio(condominio_id='corp_foreign',msp_id='msp_synthetic',nombre='B',modalidad='corporativo',corporativo_habilitado=True))
    db.flush();db.add(CorporateOrganization(tenant_id='corp_foreign'));db.commit()
    assert client.post(root,headers=auth('host_a'),json=body).status_code==201
    other=root.replace(tenant,'corp_foreign')+'/'+body['request_id']
    assert client.get(other,headers=auth('owner')).status_code==403
    assert client.patch(other+'/autorizar',headers=auth('owner')).status_code==403
    db.query(CorporateMembership).filter_by(user_id='reception').one().estado='revocado';db.commit()
    assert client.get(root,headers=auth('reception')).status_code==403
    assert client.get(root+'/'+body['request_id']+'/bitacora',headers=auth('reception')).status_code==403


def test_host_revoked_after_entry_does_not_prevent_receiving_exit(visit_setup):
    client,db,auth,tenant,root,body=visit_setup
    assert client.post(root,headers=auth('host_a'),json=body).status_code==201
    path=root+'/'+body['request_id']
    assert client.patch(path+'/autorizar',headers=auth('host_a')).status_code==200
    assert client.patch(path+'/entrada',headers=auth('reception')).status_code==200
    db.query(CorporateMembership).filter_by(user_id='host_a').one().estado='revocado';db.commit()
    assert client.patch(path+'/salida',headers=auth('reception')).status_code==200
