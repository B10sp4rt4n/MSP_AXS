"""Exercise the actual additive migration/RLS in a disposable schema, never production."""
import os
import uuid
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from backend.db.core import Base_CORE


def test_request_migration_rls_and_cross_tenant_insert():
    url = os.getenv('AXS_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('Requires isolated non-bypass PostgreSQL')
    engine = create_engine(url)
    schema = 'axs_requests_' + uuid.uuid4().hex
    core = engine.execution_options(schema_translate_map={None: schema})
    try:
        with engine.begin() as conn:
            role = conn.execute(text('SELECT current_user')).scalar_one()
            assert not conn.execute(text('SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user')).scalar_one()
            conn.execute(text(f'CREATE SCHEMA {schema}'))
        tables = [t for t in Base_CORE.metadata.sorted_tables if t.name != 'solicitudes_acceso']
        Base_CORE.metadata.create_all(core, tables=tables)
        migration = Path('migrations/20261017_solicitudes_acceso.sql').read_text().replace('public.', schema+'.')
        migration = migration.replace('TO axs_core_app', 'TO "'+role.replace('"','""')+'"')
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.exec_driver_sql(migration)
            conn.exec_driver_sql(migration)  # deployment retry is safe
        with engine.begin() as conn:
            conn.execute(text(f"INSERT INTO {schema}.msps_exo(msp_id,nombre) VALUES ('m','m')"))
            for tenant in ('a','b'):
                conn.execute(text(f"INSERT INTO {schema}.condominios_exo(condominio_id,msp_id,nombre) VALUES (:t,'m',:t)"),{'t':tenant})
                conn.execute(text(f"INSERT INTO {schema}.casas(casa_id,condominio_id,numero,tipo) VALUES (:t,:t,'101','casa')"),{'t':tenant})
                conn.execute(text(f"INSERT INTO {schema}.visitas(visita_id,condominio_id,destino_id) VALUES (:t,:t,:t)"),{'t':tenant})
            conn.execute(text(f"INSERT INTO {schema}.usuarios(usuario_id) VALUES ('guard')"))
        insert = f"INSERT INTO {schema}.solicitudes_acceso(solicitud_id,condominio_id,visita_id,destino_id,solicitada_por,destinatarios,fingerprint,creada_en,expira_en) VALUES (:id,:t,:v,:d,'guard','[]','test',now(),now()+interval '5 minutes')"
        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.tenant_id','a',true)"))
            conn.execute(text(insert),{'id':'a','t':'a','v':'a','d':'a'})
        for values in [{'id':'bad','t':'b','v':'b','d':'b'}, {'id':'bad','t':'a','v':'b','d':'a'}, {'id':'bad','t':'a','v':'a','d':'b'}]:
            with engine.connect() as conn:
                conn.execute(text("SELECT set_config('app.tenant_id','a',true)"))
                with pytest.raises(Exception, match='row-level security'):
                    conn.execute(text(insert),values)
                conn.rollback()
        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.tenant_id','b',true)"))
            assert conn.execute(text(f'SELECT count(*) FROM {schema}.solicitudes_acceso')).scalar_one() == 0
            assert conn.execute(text(f"UPDATE {schema}.solicitudes_acceso SET estado='rechazada' WHERE solicitud_id='a'")).rowcount == 0
        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.tenant_id','a',true)"))
            assert conn.execute(text(f'SELECT count(*) FROM {schema}.solicitudes_acceso')).scalar_one() == 1
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
        engine.dispose()
