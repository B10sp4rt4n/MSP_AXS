"""Fresh-run SQL, ACL, certificate and provisioner checks on disposable CI only."""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from scripts.bootstrap_corporate_sandbox_schemas import install_schema
from scripts.corporate_sandbox_attestation import certify_empty, verify_attestation
from scripts.corporate_sandbox_targets import INTEGRATED, VISITS
from scripts.prepare_integrated_sandbox_bundle import permission_scripts


@pytest.mark.parametrize('targets,profile,visits', [(INTEGRATED,'integrated-20261114',False),(VISITS,'visits-20261115',True)])
def test_new_run_certificate_and_isolation(monkeypatch,targets,profile,visits):
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
                                    {"names": list(targets.roles.values())}).scalar_one()
        created_roles = list(targets.roles.values())
        for domain in targets.databases:
            db = "axs_integrated_ci_" + uuid4().hex[:12]
            with admin.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {db}"))
            engine = create_engine(url.set(database=db))
            engines[domain] = (db, engine)
            with engine.begin() as conn:
                install_schema(conn, domain)
            for sql in permission_scripts(domain,targets):
                sql = sql.replace(targets.databases[domain], db)
                with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    conn.execute(text(sql))
            created_roles = list(targets.roles.values())
            with engine.begin() as conn:
                certify_empty(conn, domain, run, issuer, expected_db=db, targets=targets,visits_enabled=visits)
            with pytest.raises(RuntimeError), engine.begin() as conn:
                certify_empty(conn, domain, run, issuer, expected_db=db, targets=targets,visits_enabled=visits)
            roles = (domain, "PROVISIONER") if domain == "CORE" else (domain,)
            for role in roles:
                with engine.begin() as conn:
                    conn.execute(text("SET LOCAL ROLE " + targets.roles[role]))
                    verify_attestation(conn, role, run, issuer, expected_db=db, targets=targets,visits_enabled=visits)
                    if role == 'CORE' and visits:
                        from scripts.check_corporate_visit_schema import check_schema
                        check_schema(conn,role=targets.roles[role])
                    with pytest.raises(RuntimeError):
                        verify_attestation(conn, role, run, issuer, expected_db=db)
            # Preserve the 24h boundary: fresh profile does not renew old certificates.
            with engine.begin() as conn:
                conn.execute(text("UPDATE corporate_sandbox_attestation SET certified_at=CURRENT_TIMESTAMP-interval '25 hours', expires_at=CURRENT_TIMESTAMP-interval '1 hour'"))
            with pytest.raises(RuntimeError), engine.begin() as conn:
                conn.execute(text("SET LOCAL ROLE " + targets.roles[domain]))
                verify_attestation(conn, domain, run, issuer, expected_db=db, targets=targets,visits_enabled=visits)
            if visits:
                # Independent authorization accepts an expired ORIGINAL certificate
                # while keeping evidence and all normal privileges unchanged.
                with engine.connect() as conn:
                    original = dict(conn.execute(text('SELECT * FROM corporate_sandbox_attestation')).mappings().one())
                now = datetime.now(timezone.utc)
                window = {'version':1, 'authorization_id':str(uuid4()), 'run_id':run,
                    'clerk_issuer':issuer, 'approved_by':'Synthetic CI operator',
                    'reason':'Isolated seven-day window rehearsal', 'synthetic_only':True, 'revoked':False,
                    'approved_at':now.isoformat(), 'starts_at':now.isoformat(),
                    'expires_at':(now+timedelta(days=7)).isoformat(),
                    'certificates':{d: {k: original[k].isoformat() if isinstance(original[k],datetime) else original[k]
                        for k in ('database_name','catalog_hash','certified_at','expires_at')} for d in ('CORE','GOV','EVENT')}}
                for role in roles:
                    with engine.begin() as conn:
                        conn.execute(text('SET LOCAL ROLE '+targets.roles[role]))
                        assert verify_attestation(conn,role,run,issuer,expected_db=db,targets=targets,
                            visits_enabled=True,authorization=window) == now+timedelta(days=7)
                with engine.connect() as conn:
                    assert dict(conn.execute(text('SELECT * FROM corporate_sandbox_attestation')).mappings().one()) == original
                # Even with an approved window, unexpected catalog drift is denied.
                with pytest.raises(RuntimeError), engine.begin() as conn:
                    conn.execute(text('CREATE TABLE public.unapproved_window_catalog(id integer)'))
                    conn.execute(text('SET LOCAL ROLE '+targets.roles[domain]))
                    verify_attestation(conn,domain,run,issuer,expected_db=db,targets=targets,
                        visits_enabled=True,authorization=window)
        from backend.services.corporate_provisioner_db import require_provisioner_role
        monkeypatch.setenv("AXS_CORPORATE_SANDBOX_ONLY", "true")
        monkeypatch.setenv("AXS_CORPORATE_SANDBOX_RUN_PROFILE", profile)
        with engines["CORE"][1].begin() as conn:
            conn.execute(text("SET LOCAL ROLE " + targets.roles["PROVISIONER"]))
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
