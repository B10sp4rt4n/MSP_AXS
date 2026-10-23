"""C1: SQL real, FKs fuertes y RLS en PostgreSQL desechable (no Neon)."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


@pytest.mark.integration
def test_corporate_directory_migration_and_cross_tenant_fks():
    raw = os.getenv("AXS_TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Requiere PostgreSQL desechable de CI")
    url = make_url(raw)
    assert (url.host in ("localhost", "127.0.0.1")
            and url.database == "axs_rls_ci" and url.username == "axs_rls_ci")
    engine = create_engine(raw)
    schema = "axs_corp_" + uuid4().hex[:12]
    try:
        with engine.begin() as c:
            assert not c.execute(text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )).scalar_one()
            c.execute(text(f"CREATE SCHEMA {schema}"))
            c.execute(text(f"CREATE TABLE {schema}.condominios_exo("
                           "condominio_id varchar PRIMARY KEY, modalidad varchar(16) NOT NULL)"))
            c.execute(text(f"CREATE TABLE {schema}.usuarios(usuario_id varchar PRIMARY KEY)"))
            c.execute(text(f"INSERT INTO {schema}.condominios_exo VALUES "
                           "('res','residencial'),('ca','corporativo'),('cb','corporativo')"))
            c.execute(text(f"INSERT INTO {schema}.usuarios VALUES ('worker'),('other')"))

        sql = Path("migrations/20261023_corporate_directory_c1.sql").read_text()
        sql = sql.replace("public.", schema + ".").replace("TO axs_core_app", "TO axs_rls_ci")
        # psycopg interpreta el %I de format() dentro del DO como placeholder.
        # exec_driver_sql requiere escapar %, aunque psql usa el SQL original.
        sql = sql.replace("%I", "%%I")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
            c.exec_driver_sql(sql)
            c.exec_driver_sql(sql)

        tables = ("corporate_organizations", "corporate_sites",
                  "corporate_destinations", "corporate_memberships",
                  "corporate_site_assignments")
        with engine.begin() as c:
            for table in tables:
                row = c.execute(text(
                    "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
                    "WHERE oid=to_regclass(:relation)"
                ), {"relation": f"{schema}.{table}"}).one()
                assert row == (True, True)
                assert c.execute(text(f"SELECT count(*) FROM {schema}.{table}")).scalar_one() == 0

        # Una organización residencial no puede crear perfil de empresa ni por SQL.
        with engine.connect() as c:
            c.execute(text("SELECT set_config('app.tenant_id','res',true)"))
            with pytest.raises(DBAPIError):
                c.execute(text(f"INSERT INTO {schema}.corporate_organizations(tenant_id) VALUES ('res')"))
            c.rollback()

        with engine.begin() as c:
            c.execute(text("SELECT set_config('app.tenant_id','ca',true)"))
            c.execute(text(f"INSERT INTO {schema}.corporate_organizations(tenant_id) VALUES ('ca')"))
            c.execute(text(f"INSERT INTO {schema}.corporate_sites(site_id,tenant_id,nombre) "
                           "VALUES ('site_a','ca','Sede A')"))
            c.execute(text(f"INSERT INTO {schema}.corporate_memberships "
                           "(membership_id,tenant_id,user_id,rol) "
                           "VALUES ('membership_a','ca','worker','host')"))
        with engine.begin() as c:
            c.execute(text("SELECT set_config('app.tenant_id','cb',true)"))
            c.execute(text(f"INSERT INTO {schema}.corporate_organizations(tenant_id) VALUES ('cb')"))
            c.execute(text(f"INSERT INTO {schema}.corporate_sites(site_id,tenant_id,nombre) "
                           "VALUES ('site_b','cb','Sede B')"))

        # Con contexto de A, no se ven filas de B y tampoco hay escritura sobre B.
        with engine.begin() as c:
            c.execute(text("SELECT set_config('app.tenant_id','ca',true)"))
            assert c.execute(text(f"SELECT site_id FROM {schema}.corporate_sites")).scalars().all() == ['site_a']
            assert c.execute(text(f"UPDATE {schema}.corporate_sites "
                                  "SET nombre='Invasión' WHERE site_id='site_b'")).rowcount == 0

        # La FK compuesta bloquea incluso una fila con tenant A + sede B.
        with engine.connect() as c:
            c.execute(text("SELECT set_config('app.tenant_id','ca',true)"))
            with pytest.raises(DBAPIError):
                c.execute(text(f"INSERT INTO {schema}.corporate_destinations "
                               "(destination_id,tenant_id,site_id,nombre) "
                               "VALUES ('area_falsa','ca','site_b','Área cruzada')"))
            c.rollback()

        with engine.connect() as c:
            c.execute(text("SELECT set_config('app.tenant_id','ca',true)"))
            with pytest.raises(DBAPIError):
                c.execute(text(f"INSERT INTO {schema}.corporate_site_assignments "
                               "(assignment_id,tenant_id,site_id,user_id) "
                               "VALUES ('bad','ca','site_b','worker')"))
            c.rollback()

        with engine.begin() as c:
            c.execute(text("SELECT set_config('app.tenant_id','ca',true)"))
            c.execute(text(f"INSERT INTO {schema}.corporate_site_assignments "
                           "(assignment_id,tenant_id,site_id,user_id) "
                           "VALUES ('good','ca','site_a','worker')"))
            assert c.execute(text(f"SELECT user_id FROM {schema}.corporate_site_assignments")).scalar_one() == "worker"
        with engine.begin() as c:
            assert c.execute(text(f"SELECT count(*) FROM {schema}.corporate_site_assignments")).scalar_one() == 0
    finally:
        with engine.begin() as c:
            c.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
