"""C2: credencial de aprovisionamiento en PostgreSQL 16 EFÍMERO de CI.

No consulta Neon ni producción: require explicit local admin test URL.
"""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


@pytest.mark.integration
def test_corporate_provisioner_least_privilege_postgres():
    normal = os.getenv("AXS_TEST_POSTGRES_URL")
    admin = os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not normal or not admin:
        pytest.skip("Solo PostgreSQL descartable de CI con administrador local")
    url, root = make_url(normal), make_url(admin)
    assert url.host in ("localhost", "127.0.0.1") and url.database == "axs_rls_ci"
    assert root.host in ("localhost", "127.0.0.1")
    assert root.database == "axs_rls_ci" and root.username == "postgres"
    engine = create_engine(admin)
    schema = "axs_boot_" + uuid4().hex[:12]
    try:
        with engine.begin() as c:
            c.execute(text(f"CREATE SCHEMA {schema}"))
            c.execute(text(f"""CREATE TABLE {schema}.condominios_exo(
                id serial PRIMARY KEY, condominio_id varchar UNIQUE NOT NULL,
                msp_id varchar, nombre varchar, modalidad varchar(16) DEFAULT 'residencial',
                corporativo_habilitado boolean DEFAULT false)"""))
            c.execute(text(f"""CREATE TABLE {schema}.corporate_organizations(
                tenant_id varchar PRIMARY KEY, modalidad varchar(16) DEFAULT 'corporativo',
                created_at timestamp DEFAULT now())"""))
            c.execute(text(f"""CREATE TABLE {schema}.corporate_memberships(
                membership_id varchar PRIMARY KEY, tenant_id varchar, user_id varchar,
                rol varchar, estado varchar)"""))
            c.execute(text(f"""CREATE TABLE {schema}.event_outbox(
                event_uid varchar PRIMARY KEY,condominio_id varchar,payload json,
                created_at timestamp,next_attempt_at timestamp,attempts integer)"""))
            c.execute(text(f"CREATE TABLE {schema}.visitas(visita_id varchar PRIMARY KEY)"))
        sql = Path("migrations/20261023_corporate_superadmin_c2.sql").read_text()
        sql = sql.replace("public.", schema + ".").replace("%I", "%%I").replace("%s", "%%s")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
            c.exec_driver_sql(sql)
            c.exec_driver_sql(sql)
        with engine.begin() as c:
            memberships = ("SELECT", "INSERT", "UPDATE", "DELETE")
            for action in memberships:
                granted = c.execute(text(
                    "SELECT has_table_privilege('axs_corporate_provisioner',:tbl,:action)"
                ), {"tbl": f"{schema}.corporate_memberships", "action": action}).scalar_one()
                assert granted is (action in ("SELECT", "INSERT"))
            assert not c.execute(text(
                "SELECT has_table_privilege('axs_corporate_provisioner',:tbl,'SELECT')"
            ), {"tbl": f"{schema}.visitas"}).scalar_one()
            assert not c.execute(text(
                "SELECT has_schema_privilege('axs_corporate_provisioner',:name,'CREATE')"
            ), {"name": schema}).scalar_one()
            for table in ("corporate_organizations", "corporate_memberships"):
                c.execute(text(f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY"))
                c.execute(text(f"ALTER TABLE {schema}.{table} FORCE ROW LEVEL SECURITY"))
                c.execute(text(f"CREATE POLICY tenant ON {schema}.{table} "
                               "USING (tenant_id=current_setting('app.tenant_id',true)) "
                               "WITH CHECK (tenant_id=current_setting('app.tenant_id',true))"))
        # Un rol NOLOGIN sí es utilizable mediante SET ROLE del administrador
        # del contenedor descartable para verificar privilegios efectivos.
        with engine.begin() as c:
            c.exec_driver_sql("SET LOCAL ROLE axs_corporate_provisioner")
            c.execute(text("SELECT set_config('app.tenant_id','corp_ci',true)"))
            c.execute(text(f"""INSERT INTO {schema}.condominios_exo
                (condominio_id,msp_id,nombre,modalidad,corporativo_habilitado)
                VALUES ('corp_ci','provider','Empresa CI','corporativo',false)"""))
            c.execute(text(f"INSERT INTO {schema}.corporate_organizations(tenant_id) VALUES ('corp_ci')"))
            c.execute(text(f"""INSERT INTO {schema}.corporate_memberships
                (membership_id,tenant_id,user_id,rol,estado)
                VALUES ('mem1','corp_ci','owner','owner','activo')"""))
            assert c.execute(text(f"SELECT count(*) FROM {schema}.corporate_memberships")).scalar_one() == 1
        with engine.begin() as c:
            c.exec_driver_sql("SET LOCAL ROLE axs_corporate_provisioner")
            c.execute(text("SELECT set_config('app.tenant_id','another',true)"))
            assert c.execute(text(f"SELECT count(*) FROM {schema}.corporate_memberships")).scalar_one() == 0
        with engine.connect() as c:
            c.exec_driver_sql("SET LOCAL ROLE axs_corporate_provisioner")
            c.execute(text("SELECT set_config('app.tenant_id','corp_ci',true)"))
            with pytest.raises(DBAPIError):
                c.execute(text(f"DELETE FROM {schema}.corporate_memberships WHERE membership_id='mem1'"))
            c.rollback()
    finally:
        with engine.begin() as c:
            c.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            exists = c.execute(text("SELECT 1 FROM pg_roles WHERE rolname='axs_corporate_provisioner'")).first()
            if exists:
                c.execute(text("REVOKE CONNECT ON DATABASE axs_rls_ci FROM axs_corporate_provisioner"))
                c.execute(text("DROP ROLE axs_corporate_provisioner"))
        engine.dispose()
