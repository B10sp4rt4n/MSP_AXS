"""Fresh-run SQL, ACL, certificate and provisioner checks on disposable CI only."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from scripts.bootstrap_corporate_sandbox_schemas import install_schema
from scripts.corporate_sandbox_attestation import certify_empty, verify_attestation
from scripts.corporate_sandbox_targets import INTEGRATED
from scripts.prepare_integrated_sandbox_bundle import permission_scripts


def test_new_run_certificate_and_isolation(monkeypatch):
    raw = os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not raw:
        pytest.skip("Requires disposable local CI PostgreSQL")
    url = make_url(raw)
    assert url.host in ("localhost", "127.0.0.1") and url.username == "postgres" and url.database == "axs_rls_ci"
    admin = create_engine(raw, isolation_level="AUTOCOMMIT")
    engines = {}
    created_roles = []
    run, issuer = str(uuid4()), "https://axs-test.clerk.accounts.dev"
    try:
        with admin.connect() as conn:
            assert not conn.execute(text("SELECT count(*) FROM pg_roles WHERE rolname = ANY(:names)"),
                                    {"names": list(INTEGRATED.roles.values())}).scalar_one()
        created_roles = list(INTEGRATED.roles.values())
        for domain in INTEGRATED.databases:
            db = "axs_integrated_ci_" + uuid4().hex[:12]
            with admin.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {db}"))
            engine = create_engine(url.set(database=db))
            engines[domain] = (db, engine)
            with engine.begin() as conn:
                install_schema(conn, domain)
            for sql in permission_scripts(domain):
                sql = sql.replace(INTEGRATED.databases[domain], db)
                with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    conn.execute(text(sql))
            created_roles = list(INTEGRATED.roles.values())
            with engine.begin() as conn:
                certify_empty(conn, domain, run, issuer, expected_db=db, targets=INTEGRATED)
            with pytest.raises(RuntimeError), engine.begin() as conn:
                certify_empty(conn, domain, run, issuer, expected_db=db, targets=INTEGRATED)
            roles = (domain, "PROVISIONER") if domain == "CORE" else (domain,)
            for role in roles:
                with engine.begin() as conn:
                    conn.execute(text("SET LOCAL ROLE " + INTEGRATED.roles[role]))
                    verify_attestation(conn, role, run, issuer, expected_db=db, targets=INTEGRATED)
                    with pytest.raises(RuntimeError):
                        verify_attestation(conn, role, run, issuer, expected_db=db)
            # Preserve the 24h boundary: fresh profile does not renew old certificates.
            with engine.begin() as conn:
                conn.execute(text("UPDATE corporate_sandbox_attestation SET certified_at=CURRENT_TIMESTAMP-interval '25 hours', expires_at=CURRENT_TIMESTAMP-interval '1 hour'"))
            with pytest.raises(RuntimeError), engine.begin() as conn:
                conn.execute(text("SET LOCAL ROLE " + INTEGRATED.roles[domain]))
                verify_attestation(conn, domain, run, issuer, expected_db=db, targets=INTEGRATED)
        from backend.services.corporate_provisioner_db import require_provisioner_role
        monkeypatch.setenv("AXS_CORPORATE_SANDBOX_ONLY", "true")
        monkeypatch.setenv("AXS_CORPORATE_SANDBOX_RUN_PROFILE", "integrated-20261114")
        with engines["CORE"][1].begin() as conn:
            conn.execute(text("SET LOCAL ROLE " + INTEGRATED.roles["PROVISIONER"]))
            with Session(bind=conn) as session:
                require_provisioner_role(session)
                monkeypatch.setenv("AXS_CORPORATE_SANDBOX_ONLY", "false")
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as denied:
                    require_provisioner_role(session)
                assert denied.value.status_code == 503
    finally:
        for db, engine in engines.values():
            engine.dispose()
            with admin.connect() as conn:
                conn.execute(text(f"DROP DATABASE {db} WITH (FORCE)"))
        with admin.connect() as conn:
            for role in created_roles:
                conn.execute(text(f"DROP ROLE IF EXISTS {role}"))
        admin.dispose()
