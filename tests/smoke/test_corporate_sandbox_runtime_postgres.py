"""Actual minimum grants and certificates; local disposable PostgreSQL only.

Uses exact proposed SQL with database names replaced by three uniquely named
CI databases. NO remote connection, LOGIN, passwords or production overrides.
"""
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
from scripts.bootstrap_corporate_sandbox_schemas import install_schema
from scripts.corporate_sandbox_contract import DATABASES,ROLES,ACK
from scripts.corporate_sandbox_attestation import certify_empty,verify_attestation


@pytest.fixture(scope='module')
def sandbox_databases():
    raw=os.getenv('AXS_TEST_POSTGRES_ADMIN_URL')
    if not raw:
        pytest.skip('Requires disposable local CI PostgreSQL')
    url=make_url(raw)
    assert url.host in ('localhost','127.0.0.1') and url.username=='postgres' and url.database=='axs_rls_ci'
    admin=create_engine(raw,isolation_level='AUTOCOMMIT')
    engines={}
    created_roles=[]
    try:
        with admin.connect() as conn:
            created_roles=[r for r in ROLES.values() if not conn.execute(text('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:r)'),{'r':r}).scalar_one()]
        for domain in DATABASES:
            name='axs_sbx_ci_'+uuid4().hex[:12]
            with admin.connect() as conn:
                conn.execute(text(f'CREATE DATABASE {name}'))
            engine=create_engine(url.set(database=name))
            engines[domain]=(name,engine)
            with engine.begin() as conn:
                install_schema(conn,domain)
            if domain=='CORE':
                with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                    conn.execute(text(Path('migrations/20261023_corporate_superadmin_c2.sql').read_text()))
                    conn.execute(text(Path('migrations/20261023_corporate_reconciliation_c4.sql').read_text()))
            sql=Path(f'migrations/20261024_corporate_sandbox_{domain.lower()}_permissions.sql').read_text().replace(DATABASES[domain],name)
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                conn.execute(text(sql))
        yield engines
    finally:
        for name,engine in engines.values():
            engine.dispose()
            with admin.connect() as conn:
                conn.execute(text(f'DROP DATABASE {name} WITH (FORCE)'))
        with admin.connect() as conn:
            for role in created_roles:
                conn.execute(text(f'DROP ROLE IF EXISTS {role}'))
        admin.dispose()


def as_role(conn, domain):
    conn.execute(text('SET LOCAL ROLE '+ROLES[domain]))


def test_initial_certification_then_seeded_restarts_and_negative_privileges(sandbox_databases):
    run=str(uuid4())
    issuer='https://axs-test.clerk.accounts.dev'
    for domain,(db,engine) in sandbox_databases.items():
        with pytest.raises(Exception),engine.begin() as conn:
            as_role(conn,domain)
            verify_attestation(conn,domain,run,issuer,expected_db=db)
        with pytest.raises(RuntimeError),engine.begin() as conn:
            as_role(conn,domain)
            certify_empty(conn,domain,run,issuer,expected_db=db)
        with engine.begin() as conn:
            certify_empty(conn,domain,run,issuer,expected_db=db)
        with engine.begin() as conn:
            # Actual synthetic business data: subsequent runtime starts must accept it.
            if domain=='CORE':
                conn.execute(text("INSERT INTO usuarios(usuario_id,clerk_id,nombre,email,rol) VALUES ('synthetic_owner','user_synthetic','Synthetic','synthetic@example.invalid','ADMIN_CONDOMINIO')"))
            elif domain=='GOV':
                conn.execute(text("INSERT INTO authorities_gov(authority_id,identity_id,tipo,estado,created_at) VALUES ('synthetic_global','synthetic_owner','GLOBAL','ACTIVO',CURRENT_TIMESTAMP)"))
            else:
                conn.execute(text("INSERT INTO events_aup(event_uid,tipo_evento,identity_id,tenant_id,entidad,entidad_id,accion,resultado,timestamp,hash_evento) VALUES ('synthetic_event','ensayo','synthetic_owner','A','scope','A','ensayo','exito',CURRENT_TIMESTAMP,'synthetic')"))
        for role_domain in (domain,'PROVISIONER') if domain=='CORE' else (domain,):
            with engine.begin() as conn:
                as_role(conn,role_domain)
                verify_attestation(conn,role_domain,run,issuer,expected_db=db)
            for mutation in (
                f"DELETE FROM public.{ACK}",
                f"UPDATE public.{ACK} SET clerk_issuer='https://attacker.example'",
                f"INSERT INTO public.{ACK} SELECT * FROM public.{ACK}",
                "CREATE TABLE public.sandbox_escape(id int)",
            ):
                with pytest.raises(Exception),engine.begin() as conn:
                    as_role(conn,role_domain)
                    conn.execute(text(mutation))
        with engine.begin() as conn:
            as_role(conn,domain)
            with pytest.raises(RuntimeError):
                verify_attestation(conn,domain,str(uuid4()),issuer,expected_db=db)
            with pytest.raises(RuntimeError):
                verify_attestation(conn,domain,run,'https://other.clerk.accounts.dev',expected_db=db)
        # Empty certifier must refuse rerun after data/certificate, never overwrite.
        with pytest.raises(RuntimeError),engine.begin() as conn:
            certify_empty(conn,domain,run,issuer,expected_db=db)
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE public.{ACK} SET certified_at=CURRENT_TIMESTAMP-interval '25 hours',expires_at=CURRENT_TIMESTAMP-interval '1 hour'"))
        with pytest.raises(RuntimeError),engine.begin() as conn:
            as_role(conn,domain)
            verify_attestation(conn,domain,run,issuer,expected_db=db)
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE public.{ACK} SET certified_at=CURRENT_TIMESTAMP,expires_at=CURRENT_TIMESTAMP+interval '1 hour'"))
        # Broad privileges must be rejected even if normal queries still succeed.
        table={'CORE':'visitas','GOV':'authorities_gov','EVENT':'events_aup'}[domain]
        with engine.begin() as conn:
            conn.execute(text(f'GRANT DELETE ON public.{table} TO '+ROLES[domain]))
        with pytest.raises(RuntimeError),engine.begin() as conn:
            as_role(conn,domain)
            verify_attestation(conn,domain,run,issuer,expected_db=db)
        with engine.begin() as conn:
            conn.execute(text(f'REVOKE DELETE ON public.{table} FROM '+ROLES[domain]))


def test_gov_rls_quota_boundary_and_read_only_authority(sandbox_databases):
    db,engine=sandbox_databases['GOV']
    with engine.begin() as conn:
        as_role(conn,'GOV')
        conn.execute(text("SELECT set_config('app.tenant_id','A',true)"))
        conn.execute(text("INSERT INTO policies_gov(policy_id,nombre,ambito,target_tenant_id,accion_objetivo,limites,estado,valida_desde,created_at) VALUES ('quota_a','Synthetic','TENANT','A','crear_sede_corporativa','{\"max_count\":2}','ACTIVO',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    with engine.begin() as conn:
        as_role(conn,'GOV')
        conn.execute(text("SELECT set_config('app.tenant_id','B',true)"))
        assert conn.execute(text("SELECT count(*) FROM policies_gov WHERE policy_id='quota_a'")).scalar_one()==0
    for mutation in (
        "UPDATE authorities_gov SET estado='REVOCADO'",
        "INSERT INTO policies_gov(policy_id,nombre,ambito,target_tenant_id,accion_objetivo,limites,estado,valida_desde,created_at) VALUES ('escape','Synthetic','GLOBAL',NULL,'crear_sede_corporativa','{}','ACTIVO',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
        "UPDATE policies_gov SET accion_objetivo='crear_tenant'",
    ):
        with pytest.raises(Exception),engine.begin() as conn:
            as_role(conn,'GOV')
            conn.execute(text("SELECT set_config('app.tenant_id','A',true)"))
            conn.execute(text(mutation))


def test_core_lock_without_root_update_or_residential_access(sandbox_databases):
    _,engine=sandbox_databases['CORE']
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO condominios_exo(condominio_id,nombre,modalidad,corporativo_habilitado) VALUES ('A','Synthetic','corporativo',false),('residential_sentinel','Private sentinel','residencial',false)"))
    with engine.begin() as conn:
        as_role(conn,'CORE')
        conn.execute(text("SELECT public.corporate_sandbox_lock_company('A')"))
        assert conn.execute(text("SELECT count(*) FROM condominios_exo WHERE modalidad='residencial'")).scalar_one()==0
    for mutation in ("UPDATE condominios_exo SET corporativo_habilitado=true", "INSERT INTO usuarios(usuario_id) VALUES ('escape')", "SELECT * FROM visitas", "SELECT * FROM evidencias"):
        with pytest.raises(Exception),engine.begin() as conn:
            as_role(conn,'CORE')
            conn.execute(text(mutation))


def test_event_delivery_rechecks_tenant_and_preserves_append_only(sandbox_databases):
    from sqlalchemy.orm import Session
    from backend.services.event_outbox import publicar_evento
    from backend.core.event.registry import calcular_hash_evento
    _,engine=sandbox_databases['EVENT']
    moment=datetime.utcnow()
    payload=dict(event_uid='synthetic_delivery',session_hash='synthetic_session',tipo_evento='ensayo',
        identity_id='synthetic_owner',tenant_id='A',entidad='scope',entidad_id='A',
        accion='ensayo',resultado='exito',timestamp=moment.isoformat())
    payload['hash_evento']=calcular_hash_evento(payload['event_uid'],payload['identity_id'],
        payload['session_hash'],payload['tenant_id'],payload['entidad'],payload['entidad_id'],
        payload['accion'],payload['resultado'],moment)
    with engine.begin() as conn:
        as_role(conn,'EVENT')
        with Session(bind=conn) as session:
            publicar_evento(session,payload)
            publicar_evento(session,payload)
        assert conn.execute(text("SELECT count(*) FROM events_aup WHERE event_uid='synthetic_delivery'")).scalar_one()==1
        conn.execute(text("SELECT set_config('app.tenant_id','B',true)"))
        assert conn.execute(text("SELECT count(*) FROM events_aup WHERE event_uid='synthetic_delivery'")).scalar_one()==0
    for mutation in ("UPDATE events_aup SET resultado='forged'", "DELETE FROM events_aup"):
        with pytest.raises(Exception),engine.begin() as conn:
            as_role(conn,'EVENT')
            conn.execute(text("SELECT set_config('app.tenant_id','A',true)"))
            conn.execute(text(mutation))
