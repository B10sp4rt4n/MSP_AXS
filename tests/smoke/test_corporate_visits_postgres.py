"""Actual reviewed migration/RLS using a separately authenticated runtime role."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from backend.db.core import Base_CORE, MSP, Condominio, Usuario, CorporateOrganization, CorporateSite, CorporateDestination, CorporateMembership, CorporateSiteAssignment
from scripts.check_corporate_visit_schema import check_schema


@pytest.fixture(scope="module")
def runtime():
    raw = os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not raw:
        pytest.skip("Requires disposable local CI PostgreSQL")
    url = make_url(raw)
    assert url.host in {"localhost", "127.0.0.1"} and url.username == "postgres" and url.database == "axs_rls_ci"
    name = "axs_visit_" + uuid4().hex[:10]
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    core = create_engine(url.set(database=name))
    engine = create_engine(url.set(database=name, username=name, password="ci-only"))
    try:
        with admin.connect() as c:
            c.exec_driver_sql(f'CREATE DATABASE {name}')
            c.exec_driver_sql(f"CREATE ROLE {name} LOGIN PASSWORD 'ci-only' NOINHERIT NOSUPERUSER NOBYPASSRLS")
        Base_CORE.metadata.create_all(core)
        with Session(core) as db:
            db.add(MSP(msp_id="m",nombre="synthetic"))
            db.add_all([Usuario(usuario_id="u"+t,email=t+"@example.test",rol="RESIDENTE") for t in ('a','b','r')])
            db.commit()
            for t in ('a','b'):
                db.add(Condominio(condominio_id=t,msp_id="m",nombre=t,modalidad="corporativo",corporativo_habilitado=True))
                db.flush()
                db.add(CorporateOrganization(tenant_id=t));db.flush()
                db.add(CorporateSite(tenant_id=t,site_id='s'+t,nombre=t));db.flush()
                db.add(CorporateDestination(tenant_id=t,site_id='s'+t,destination_id='d'+t,nombre=t))
                db.add(CorporateMembership(tenant_id=t,user_id='u'+t,membership_id=t,rol='host'))
            db.add(CorporateMembership(tenant_id='a',user_id='ur',membership_id='r',rol='reception'))
            db.flush()
            db.add_all([CorporateSiteAssignment(tenant_id='a',user_id=u,site_id='sa',assignment_id=u) for u in ('ua','ur')])
            db.commit()
        sql=Path('migrations/20261115_corporate_visits_c5.sql').read_text().replace('axs_core_app',name)
        with core.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
            c.execute(text(sql))
            c.exec_driver_sql(f'GRANT SELECT ON corporate_organizations,corporate_sites,corporate_destinations,corporate_memberships,corporate_site_assignments,usuarios,condominios_exo,event_outbox TO {name}')
            c.exec_driver_sql(f'GRANT INSERT ON event_outbox TO {name}')
            c.exec_driver_sql(f'GRANT UPDATE(nombre) ON condominios_exo TO {name}')
            c.exec_driver_sql(f'GRANT UPDATE(nombre) ON corporate_destinations TO {name}')
            c.exec_driver_sql(f'GRANT UPDATE(nombre) ON corporate_sites TO {name}')
        yield engine,name
    finally:
        engine.dispose();core.dispose()
        with admin.connect() as c:
            c.exec_driver_sql(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)')
            c.exec_driver_sql(f'DROP ROLE IF EXISTS {name}')
        admin.dispose()


def insert(tenant='a',destination='da',host='ua'):
    return "INSERT INTO corporate_visits(tenant_id,visit_id,site_id,destination_id,host_user_id,visitor_ref,state,created_by,created_at) VALUES " + f"('{tenant}','{uuid4()}','sa','{destination}','{host}','opaque','preregistrada','ua',now())"


def test_runtime_gate_and_rls(runtime):
    engine,role=runtime
    with engine.connect() as c,c.begin():
        c.exec_driver_sql('SET TRANSACTION READ ONLY')
        assert check_schema(c,role)['gate']=='PASS'
    with engine.connect() as c,c.begin():
        c.exec_driver_sql("SELECT set_config('app.tenant_id','a',true)")
        c.exec_driver_sql(insert())
        assert c.exec_driver_sql('SELECT count(*) FROM corporate_visits').scalar_one()==1
        c.exec_driver_sql("SELECT set_config('app.tenant_id','b',true)")
        assert c.exec_driver_sql('SELECT count(*) FROM corporate_visits').scalar_one()==0


@pytest.mark.parametrize('statement,code',[
    (insert(tenant='b'),'42501'),(insert(destination='db'),'23503'),(insert(host='ub'),'23503'),
    ('DELETE FROM corporate_visits','42501'),('TRUNCATE corporate_visits','42501'),
    ("UPDATE corporate_visits SET visitor_ref='altered'",'42501'),
    ("UPDATE corporate_visits SET state='cerrada'",'23514'),
    ('ALTER TABLE corporate_visits DISABLE ROW LEVEL SECURITY','42501'),
    ('SET ROLE postgres','42501'),
])
def test_denials(runtime,statement,code):
    engine,_=runtime
    with pytest.raises(DBAPIError) as exc,engine.connect() as c,c.begin():
        c.exec_driver_sql("SELECT set_config('app.tenant_id','a',true)")
        c.exec_driver_sql(insert())
        c.exec_driver_sql(statement)
    assert exc.value.orig.sqlstate==code


def test_http_cycle_uses_real_runtime_login_and_atomic_outbox(runtime,monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.core.auth.dependencies import get_current_user
    from backend.core.auth.jwt import create_access_token
    from backend.db.core import get_core_db
    engine,_=runtime
    for flag in ('AXS_CORPORATE_API_ENABLED','AXS_CORPORATE_VISITS_ENABLED'):
        monkeypatch.setenv(flag,'true')
    actor={'id':'ur'}
    def session():
        with Session(engine) as db: yield db
    previous=app.dependency_overrides.copy()
    app.dependency_overrides[get_core_db]=session
    app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(usuario_id=actor['id'])
    def headers(): return {'Authorization':'Bearer '+create_access_token(actor['id'],'GUARDIA')}
    try:
        with TestClient(app) as client:
            root='/corporativo/a/sedes/sa/visitas'
            body={'request_id':str(uuid4()),'destination_id':'da','host_user_id':'ua','visitor_ref':'opaque_http'}
            response=client.post(root,headers=headers(),json=body)
            assert response.status_code==201,response.text
            path=root+'/'+body['request_id']
            actor['id']='ua'
            response=client.patch(path+'/autorizar',headers=headers())
            assert response.status_code==200,response.text
            actor['id']='ur'
            for action in ('entrada','salida'):
                response=client.patch(path+'/'+action,headers=headers())
                assert response.status_code==200,response.text
                assert client.patch(path+'/'+action,headers=headers()).json()==response.json()
            response=client.get(path+'/bitacora',headers=headers())
            assert response.status_code==200,response.text
            assert [e['action'] for e in response.json()]==['preregistrar','autorizar','entrada','salida']
    finally:
        app.dependency_overrides.clear();app.dependency_overrides.update(previous)
