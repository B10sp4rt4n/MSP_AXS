"""C0->C1->C2->C4 upgrade, partial failure and read-only gate on local CI only.

The legacy schema/rows are representative synthetic fixtures, not a production
catalog clone. No Neon URL, account credential or actual tenant data is used.
"""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from scripts import check_corporate_schema as gate


pytestmark = pytest.mark.integration
MIGRATIONS = [
    "20261023_tenant_modalidad_c0.sql",
    "20261023_corporate_directory_c1.sql",
    "20261023_corporate_superadmin_c2.sql",
    "20261023_corporate_reconciliation_c4.sql",
]


@pytest.fixture
def upgrade():
    raw = os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not raw:
        pytest.skip("Requires disposable local CI PostgreSQL")
    url = make_url(raw)
    assert url.get_backend_name() == "postgresql"
    assert url.host in {"localhost", "127.0.0.1"}
    assert url.database == "axs_rls_ci" and url.username == "postgres"
    engine = create_engine(raw)
    suffix = uuid4().hex[:12]
    schema, runtime, provisioner = "axs_upgrade_" + suffix, "axs_old_" + suffix, "axs_prov_" + suffix

    def apply(index, *, fail_before_commit=False):
        sql = Path("migrations", MIGRATIONS[index]).read_text()
        sql = (sql.replace("public.", schema + ".")
               .replace("ON SCHEMA public TO", f"ON SCHEMA {schema} TO")
               .replace("axs_core_app", runtime)
               .replace("axs_corporate_provisioner", provisioner)
               .replace("%", "%%"))
        if fail_before_commit:
            sql = sql.replace("COMMIT;", "DO $$ BEGIN RAISE EXCEPTION 'synthetic C4 failure'; END $$; COMMIT;")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            try:
                connection.exec_driver_sql(sql)
            except Exception:
                connection.exec_driver_sql("ROLLBACK")
                raise

    try:
        with engine.begin() as c:
            c.exec_driver_sql(f"CREATE ROLE {runtime} NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS")
            c.exec_driver_sql(f"CREATE SCHEMA {schema}")
            c.exec_driver_sql(f"""CREATE TABLE {schema}.condominios_exo(
                id serial PRIMARY KEY,condominio_id varchar UNIQUE NOT NULL,
                msp_id varchar,nombre varchar)""")
            c.exec_driver_sql(f"CREATE TABLE {schema}.usuarios(usuario_id varchar PRIMARY KEY)")
            c.exec_driver_sql(f"CREATE TABLE {schema}.event_outbox(event_uid varchar PRIMARY KEY,condominio_id varchar,payload json)")
            c.exec_driver_sql(f"INSERT INTO {schema}.usuarios VALUES ('owner_synthetic')")
            c.exec_driver_sql(f"INSERT INTO {schema}.condominios_exo(condominio_id,msp_id,nombre) VALUES ('res_a','msp_synthetic','Residential A'),('res_b','msp_synthetic','Residential B')")
            c.exec_driver_sql(f"GRANT USAGE ON SCHEMA {schema} TO {runtime}")
            c.exec_driver_sql(f"GRANT SELECT,INSERT,UPDATE ON {schema}.condominios_exo TO {runtime}")
            c.exec_driver_sql(f"GRANT USAGE ON SEQUENCE {schema}.condominios_exo_id_seq TO {runtime}")
        yield engine, schema, runtime, provisioner, apply
    finally:
        with engine.begin() as c:
            c.exec_driver_sql(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            for role in (runtime, provisioner):
                if c.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:role)"), {"role": role}):
                    c.exec_driver_sql(f"DROP OWNED BY {role}")
                    c.exec_driver_sql(f"DROP ROLE {role}")
        engine.dispose()


def ready(fixture):
    engine, schema, runtime, provisioner, apply = fixture
    for index in range(4):
        apply(index)
    return engine, schema, runtime, provisioner


def check(engine, schema, provisioner):
    return gate.run_gate(engine, schema=schema, provisioner_role=provisioner)


def test_upgrade_preserves_old_residential_queries_and_defaults(upgrade):
    engine, schema, runtime, provisioner, apply = upgrade
    with engine.connect() as c:
        before = c.execute(text(f"SELECT condominio_id,msp_id,nombre FROM {schema}.condominios_exo ORDER BY condominio_id")).all()
    # Every incomplete stage must fail; no create_all may silently fill gaps.
    for index in range(4):
        with pytest.raises(gate.SchemaGateError):
            check(engine, schema, provisioner)
        apply(index)
        if index < 3:
            apply(index)  # Supported replay of C0/C1/C2, not C4.
    assert check(engine, schema, provisioner)["gate"] == "PASS"
    with engine.begin() as c:
        c.exec_driver_sql(f"SET LOCAL ROLE {runtime}")
        assert c.execute(text(f"SELECT condominio_id,msp_id,nombre FROM {schema}.condominios_exo ORDER BY condominio_id")).all() == before
        # The old application still omits the two new fields.
        c.exec_driver_sql(f"INSERT INTO {schema}.condominios_exo(condominio_id,msp_id,nombre) VALUES ('res_c','msp_synthetic','Residential C')")
        rows = c.execute(text(f"SELECT modalidad,corporativo_habilitado FROM {schema}.condominios_exo")).all()
        assert rows == [("residencial", False)] * 3
        c.exec_driver_sql(f"UPDATE {schema}.condominios_exo SET nombre='Legacy update' WHERE condominio_id='res_a'")
        assert c.scalar(text(f"SELECT nombre FROM {schema}.condominios_exo WHERE condominio_id='res_a'")) == "Legacy update"
        assert c.scalar(text(f"SELECT count(*) FROM {schema}.corporate_sites")) == 0
    assert check(engine, schema, provisioner)["gate"] == "PASS"


def test_c4_failure_rolls_back_and_completed_c4_is_not_replayed(upgrade):
    engine, schema, runtime, provisioner, apply = upgrade
    for i in range(3):
        apply(i)
    with pytest.raises(DBAPIError):
        apply(3, fail_before_commit=True)
    with engine.connect() as c:
        assert c.scalar(text("SELECT to_regclass(:name)"), {"name": schema + ".corporate_provisioning_operations"}) is None
    with pytest.raises(gate.SchemaGateError):
        check(engine, schema, provisioner)
    apply(3)
    with pytest.raises(DBAPIError) as error:
        apply(3)
    assert getattr(error.value.orig, "sqlstate", None) == "42P07"
    assert check(engine, schema, provisioner)["gate"] == "PASS"


@pytest.mark.parametrize("drift", [
    "privacy_column", "tenant_default", "rls", "foreign_key", "pending_index", "state_check", "policy", "extra_policy",
])
def test_gate_rejects_incomplete_or_drifted_schema(upgrade, drift):
    engine, schema, runtime, provisioner = ready(upgrade)
    sql = {
        "privacy_column": "ALTER TABLE {s}.corporate_organizations DROP COLUMN privacy_notice_version",
        "tenant_default": "ALTER TABLE {s}.condominios_exo ALTER COLUMN corporativo_habilitado SET DEFAULT true",
        "rls": "ALTER TABLE {s}.corporate_sites NO FORCE ROW LEVEL SECURITY",
        "foreign_key": "ALTER TABLE {s}.corporate_destinations DROP CONSTRAINT fk_corporate_destination_site",
        "pending_index": "DROP INDEX {s}.uq_corporate_operation_pending",
        "state_check": "ALTER TABLE {s}.corporate_provisioning_operations DROP CONSTRAINT ck_corporate_operation_state",
        "policy": "ALTER POLICY corporate_sites_tenant ON {s}.corporate_sites USING(true) WITH CHECK(true)",
        "extra_policy": "CREATE POLICY open_site ON {s}.corporate_sites USING(true) WITH CHECK(true)",
    }[drift].format(s=schema)
    with engine.begin() as c:
        c.exec_driver_sql(sql)
    with pytest.raises(gate.SchemaGateError):
        check(engine, schema, provisioner)


def test_read_only_transaction_prevents_unexpected_ddl(upgrade, monkeypatch):
    engine, schema, runtime, provisioner = ready(upgrade)
    def accidental_write(connection, **kwargs):
        connection.exec_driver_sql(f"CREATE TABLE {schema}.should_never_exist(id integer)")
    monkeypatch.setattr(gate, "check_schema", accidental_write)
    with pytest.raises(gate.SchemaGateError, match="no se pudo verificar"):
        check(engine, schema, provisioner)
    with engine.connect() as c:
        assert c.scalar(text("SELECT to_regclass(:name)"), {"name": schema + ".should_never_exist"}) is None


def test_runtime_can_inspect_catalog_but_not_create_schema_objects(upgrade):
    engine, schema, runtime, provisioner = ready(upgrade)
    with engine.begin() as c:
        c.exec_driver_sql(f"SET LOCAL ROLE {runtime}")
        assert gate.check_schema(c, schema=schema, provisioner_role=provisioner)["gate"] == "PASS"
        assert not c.scalar(text("SELECT has_schema_privilege(current_user,:schema,'CREATE')"), {"schema": schema})
        assert not c.scalar(text("SELECT has_table_privilege(current_user,:table,'UPDATE')"), {"table": schema + ".corporate_memberships"})
