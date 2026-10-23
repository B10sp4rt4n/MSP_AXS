"""ARCO migration, fail-closed RLS and locks on disposable PostgreSQL only."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


def test_arco_migration_rls_and_concurrent_lock():
    raw = os.getenv('AXS_TEST_POSTGRES_URL')
    if not raw:
        pytest.skip('Requires disposable CI PostgreSQL')
    url = make_url(raw)
    assert url.host in ('localhost','127.0.0.1') and url.database == 'axs_rls_ci' and url.username == 'axs_rls_ci'
    engine = create_engine(raw)
    schema = 'axs_arco_' + uuid4().hex
    try:
        with engine.begin() as c:
            assert not c.execute(text('SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user')).scalar_one()
            c.execute(text(f'CREATE SCHEMA {schema}'))
            c.execute(text(f'CREATE TABLE {schema}.condominios_exo(condominio_id varchar PRIMARY KEY)'))
            c.execute(text(f"INSERT INTO {schema}.condominios_exo VALUES ('a'),('b')"))
        sql = Path('migrations/20261022_arco_cases.sql').read_text().replace('public.',schema+'.').replace('TO axs_core_app','TO axs_rls_ci')
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
            c.exec_driver_sql(sql)
            c.exec_driver_sql(sql)
        def context(c, tenant):
            c.execute(text("SELECT set_config('app.tenant_id',:t,true)"),{'t':tenant})
        def insert(c, tenant, key):
            c.execute(text(f'''INSERT INTO {schema}.arco_cases
                (case_id,condominio_id,received_at,determination_due,"right",subject_ref,owner_id,state,version,pending_actions,history)
                VALUES (:id,:t,now(),now()+interval '20 days','acceso','synthetic','owner','recibida',1,0,'[]')'''),{'t':tenant,'id':key})
        for tenant in ('a','b'):
            with engine.begin() as c:
                context(c,tenant); insert(c,tenant,tenant)
        with engine.begin() as c:
            assert c.execute(text(f'SELECT count(*) FROM {schema}.arco_cases')).scalar_one()==0
            context(c,'a')
            assert c.execute(text(f'SELECT case_id FROM {schema}.arco_cases')).scalars().all()==['a']
            assert c.execute(text(f"UPDATE {schema}.arco_cases SET pending_actions=9 WHERE case_id='b'")).rowcount==0
        with engine.connect() as c:
            context(c,'a')
            with pytest.raises(DBAPIError): insert(c,'b','forbidden')
            c.rollback()
        with engine.connect() as first, engine.connect() as second:
            context(first,'a'); context(second,'a')
            first.execute(text(f"SELECT * FROM {schema}.arco_cases WHERE case_id='a' FOR UPDATE"))
            second.execute(text("SET LOCAL lock_timeout='100ms'"))
            with pytest.raises(DBAPIError):
                second.execute(text(f"SELECT * FROM {schema}.arco_cases WHERE case_id='a' FOR UPDATE"))
            second.rollback()
            first.execute(text(f"UPDATE {schema}.arco_cases SET version=2 WHERE case_id='a'"))
            first.commit()
            context(second,'a')
            assert second.execute(text(f"SELECT version FROM {schema}.arco_cases WHERE case_id='a' FOR UPDATE")).scalar_one()==2
            second.rollback()
    finally:
        with engine.begin() as c: c.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
        engine.dispose()
