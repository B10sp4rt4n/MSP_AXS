"""Validate schema creation exclusively in disposable, local CI PostgreSQL.

Does NOT exercise Neon, does NOT grant runtime access, does NOT create data.
"""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from scripts.bootstrap_corporate_sandbox_schemas import install_schema, get_metadata


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
