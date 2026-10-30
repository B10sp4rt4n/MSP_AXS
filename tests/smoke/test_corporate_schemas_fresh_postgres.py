"""Validate schema creation exclusively in disposable, local CI PostgreSQL.

Does NOT exercise Neon, does NOT grant runtime access, does NOT create data.
"""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from scripts.bootstrap_corporate_sandbox_schemas import install_schema, get_metadata
from scripts.check_corporate_sandbox_data import require_empty


@pytest.mark.integration
@pytest.mark.parametrize("has_data", [False, True])
def test_runtime_rls_view_cannot_certify_global_emptiness(has_data):
    raw = os.getenv("AXS_TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Requires disposable local CI PostgreSQL")
    url = make_url(raw)
    assert url.host in {"localhost", "127.0.0.1"} and url.database == "axs_rls_ci" and url.username == "axs_rls_ci"
    engine = create_engine(raw)
    schema = "axs_empty_" + uuid4().hex[:12]
    try:
        with engine.begin() as conn:
            assert not conn.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")).scalar_one()
            conn.execute(text(f"CREATE SCHEMA {schema}"))
            conn.execute(text(f"CREATE TABLE {schema}.sample (marker text)"))
            if has_data:
                conn.execute(text(f"INSERT INTO {schema}.sample VALUES ('PRIVATE_SENTINEL')"))
            conn.execute(text(f"ALTER TABLE {schema}.sample ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"ALTER TABLE {schema}.sample FORCE ROW LEVEL SECURITY"))
            conn.execute(text(f"CREATE POLICY closed ON {schema}.sample USING (false)"))
        with engine.connect() as conn:
            assert conn.execute(text(f"SELECT count(*) FROM {schema}.sample")).scalar_one() == 0
            class ScopedConnection:
                dialect = engine.dialect
                def execute(self, statement):
                    return conn.execute(text(str(statement).replace("public.", schema+".")))
            with pytest.raises(RuntimeError) as error:
                require_empty(ScopedConnection(), ("sample",), label="CORE")
            assert "PRIVATE_SENTINEL" not in str(error.value)
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()


@pytest.mark.integration
def test_bootstrap_three_domains_forces_rls_without_rows():
    raw = os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not raw:
        pytest.skip("Requires disposable CI PostgreSQL")
    url = make_url(raw)
    assert url.host in ("localhost", "127.0.0.1")
    assert url.database == "axs_rls_ci" and url.username == "postgres"
    engine = create_engine(raw)
    schemas = ["axs_ci_" + uuid4().hex[:12] for _ in range(3)]
    try:
        for schema, domain in zip(schemas, ("CORE", "GOV", "EVENT")):
            with engine.begin() as conn:
                conn.exec_driver_sql(f"CREATE SCHEMA {schema}")
                count = install_schema(conn, domain, schema=schema)
                assert count == len(get_metadata(domain).tables)
                rows = conn.execute(text("""
                    SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname=:schema AND c.relkind='r'
                """), {"schema": schema}).all()
                assert len(rows) == count
                assert all(bool(row[1]) and bool(row[2]) for row in rows)
                for name in get_metadata(domain).tables:
                    assert conn.execute(text(
                        f'SELECT count(*) FROM "{schema}"."{name}"'
                    )).scalar_one() == 0
                if domain == "CORE":
                    assert conn.execute(text("""
                        SELECT count(*) FROM pg_policy p
                        JOIN pg_class c ON c.oid=p.polrelid
                        JOIN pg_namespace n ON n.oid=c.relnamespace
                        WHERE n.nspname=:schema AND c.relname LIKE 'corporate_%'
                    """), {"schema": schema}).scalar_one() == 5
    finally:
        with engine.begin() as conn:
            for schema in schemas:
                conn.exec_driver_sql(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        engine.dispose()
