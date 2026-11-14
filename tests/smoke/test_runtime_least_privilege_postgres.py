"""Actual SQL grants/RLS and app delivery, only disposable local CI databases."""
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend.db.event import Base_EVENT
from backend.db.gov import Base_GOV
from backend.core.event.registry import calcular_hash_evento
from backend.services.event_outbox import publicar_evento
from scripts.check_runtime_permissions import check_connection, RuntimeGateError


@pytest.fixture(scope="module")
def domains():
    raw = os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not raw:
        pytest.skip("Requires disposable local CI PostgreSQL admin")
    url = make_url(raw)
    assert url.host in ("localhost", "127.0.0.1") and url.database == "axs_rls_ci" and url.username == "postgres"
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    suffix = uuid4().hex[:10]
    resources = {}
    try:
        for domain, base in (("EVENT", Base_EVENT), ("GOV", Base_GOV)):
            name, role = "axs_perm_" + domain.lower() + "_" + suffix, "axs_perm_" + domain.lower() + "_" + suffix
            with admin.connect() as c:
                c.exec_driver_sql(f'CREATE DATABASE "{name}"')
            engine = create_engine(url.set(database=name))
            runtime_engine = create_engine(url.set(database=name, username=role, password="ci-only-" + suffix))
            resources[domain] = (name, role, engine, runtime_engine)
            base.metadata.create_all(engine)
            sql = Path(f"migrations/20261114_{domain.lower()}_runtime_permissions.sql").read_text()
            sql = sql.replace("aup_" + domain.lower(), name).replace("axs_" + domain.lower() + "_app", role)
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
                c.execute(text(sql))
                assert not c.execute(text("SELECT rolcanlogin FROM pg_roles WHERE rolname=:role"), {"role": role}).scalar_one()
                # Local disposable CI only: real runtime authentication, not an
                # admin SET ROLE session that could still SET ROLE back to admin.
                c.exec_driver_sql(f"ALTER ROLE {role} LOGIN PASSWORD 'ci-only-{suffix}'")
        yield resources
    finally:
        for name, role, engine, runtime_engine in resources.values():
            runtime_engine.dispose()
            engine.dispose()
            with admin.connect() as c:
                c.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
                c.exec_driver_sql(f'DROP ROLE IF EXISTS "{role}"')
        admin.dispose()


@contextmanager
def runtime(domains, domain, tenant=None, *, read_only=False):
    _, role, _, engine = domains[domain]
    with engine.connect() as conn, conn.begin():
        if read_only:
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        assert conn.exec_driver_sql("SELECT session_user=current_user").scalar_one()
        if tenant:
            conn.execute(text("SELECT set_config('app.tenant_id',:tenant,true)"), {"tenant": tenant})
        yield conn


@pytest.mark.parametrize("domain", ["EVENT", "GOV"])
def test_read_only_gate_accepts_only_runtime_contract(domains, domain):
    with runtime(domains, domain, read_only=True) as conn:
        assert check_connection(conn, domain, expected_role=domains[domain][1])["gate"] == "PASS"


def test_event_delivery_replay_and_cross_tenant_denial(domains):
    _, role, _, runtime_engine = domains["EVENT"]
    # Use actual publisher with a runtime connection, including post-commit SELECT.
    stamp = datetime(2026, 11, 14, 12)
    payload = {"event_uid": "runtime_replay", "session_hash": "synthetic", "identity_id": "synthetic",
               "tenant_id": "A", "entidad": "visita", "entidad_id": "synthetic",
               "accion": "registrar", "resultado": "exito", "tipo_evento": "registrar",
               "timestamp": stamp.isoformat()}
    payload["hash_evento"] = calcular_hash_evento(payload["event_uid"], payload["identity_id"],
        payload["session_hash"], "A", "visita", "synthetic", "registrar", "exito", stamp)
    try:
        with Session(runtime_engine) as session:
            publicar_evento(session, payload)
            publicar_evento(session, payload)
        with runtime(domains, "EVENT", "A") as c:
            assert c.exec_driver_sql("SELECT count(*) FROM events_aup WHERE event_uid='runtime_replay'").scalar_one() == 1
        for tenant in (None, "B"):
            with runtime(domains, "EVENT", tenant) as c:
                assert c.exec_driver_sql("SELECT count(*) FROM events_aup WHERE event_uid='runtime_replay'").scalar_one() == 0
        with pytest.raises(DBAPIError) as error, runtime(domains, "EVENT", "B") as c:
            c.exec_driver_sql("INSERT INTO events_aup(event_uid,tipo_evento,identity_id,tenant_id,entidad,entidad_id,accion,resultado,timestamp,hash_evento) VALUES ('cross','synthetic','synthetic','A','visita','synthetic','registrar','exito',now(),'cross')")
        assert error.value.orig.sqlstate == "42501"
    finally:
        runtime_engine.dispose()


@pytest.mark.parametrize("command", [
    "UPDATE events_aup SET motivo='changed'", "DELETE FROM events_aup", "TRUNCATE events_aup",
    "CREATE TABLE public.escape(id int)", "CREATE TEMP TABLE escape(id int)",
    "ALTER TABLE events_aup DISABLE ROW LEVEL SECURITY", "SET ROLE postgres",
])
def test_event_runtime_cannot_mutate_history_or_escalate(domains, command):
    with pytest.raises(DBAPIError) as error, runtime(domains, "EVENT", "A") as c:
        c.exec_driver_sql(command)
    assert error.value.orig.sqlstate == "42501"


def test_gov_reads_control_plane_but_writes_only_scoped_quota(domains):
    _, _, engine, _ = domains["GOV"]
    with engine.begin() as c:
        c.exec_driver_sql("INSERT INTO authorities_gov(authority_id,identity_id,tipo,estado,created_at) VALUES ('synthetic_global','synthetic','GLOBAL','ACTIVO',now())")
        c.exec_driver_sql("INSERT INTO policies_gov(policy_id,nombre,ambito,accion_objetivo,limites,valida_desde,estado,created_at) VALUES ('global','synthetic','GLOBAL','crear_visita','{}',now(),'ACTIVO',now())")
    with runtime(domains, "GOV", "A") as c:
        assert c.exec_driver_sql("SELECT count(*) FROM authorities_gov WHERE authority_id='synthetic_global'").scalar_one() == 1
        assert c.exec_driver_sql("SELECT count(*) FROM policies_gov WHERE policy_id='global'").scalar_one() == 1
        c.exec_driver_sql("SELECT * FROM delegations_gov")
        c.exec_driver_sql("SELECT * FROM recovery_gov_checkpoints")
        c.exec_driver_sql("INSERT INTO policies_gov(policy_id,nombre,ambito,target_tenant_id,accion_objetivo,limites,valida_desde,estado,created_at) VALUES ('quota_a','synthetic','TENANT','A','crear_sede_corporativa','{}',now(),'ACTIVO',now())")
        c.exec_driver_sql("SELECT * FROM policies_gov WHERE policy_id='quota_a' FOR UPDATE")
        assert c.exec_driver_sql("UPDATE policies_gov SET limites='{\"max_count\":2}' WHERE policy_id='quota_a'").rowcount == 1
    with runtime(domains, "GOV", "B") as c:
        assert c.exec_driver_sql("UPDATE policies_gov SET limites='{}' WHERE policy_id='quota_a'").rowcount == 0
    with runtime(domains, "GOV", "A") as c:
        assert c.exec_driver_sql("UPDATE policies_gov SET limites='{}' WHERE policy_id='global'").rowcount == 0


@pytest.mark.parametrize("command", [
    "INSERT INTO authorities_gov(authority_id,identity_id,tipo,estado,created_at) VALUES ('escape','synthetic','GLOBAL','ACTIVO',now())",
    "UPDATE authorities_gov SET estado='REVOCADO'", "DELETE FROM delegations_gov", "TRUNCATE policies_gov",
    "UPDATE policies_gov SET accion_objetivo='crear_tenant'",
    "INSERT INTO policies_gov(policy_id,nombre,ambito,accion_objetivo,limites,valida_desde,estado,created_at) VALUES ('escape','synthetic','GLOBAL','crear_tenant','{}',now(),'ACTIVO',now())",
    "INSERT INTO policies_gov(policy_id,nombre,ambito,target_tenant_id,accion_objetivo,limites,valida_desde,estado,created_at) VALUES ('cross','synthetic','TENANT','B','crear_sede_corporativa','{}',now(),'ACTIVO',now())",
    "CREATE TABLE public.escape(id int)", "SET ROLE postgres",
])
def test_gov_runtime_cannot_create_authority_change_global_or_escalate(domains, command):
    with pytest.raises(DBAPIError) as error, runtime(domains, "GOV", "A") as c:
        c.exec_driver_sql(command)
    assert error.value.orig.sqlstate == "42501"


@pytest.mark.parametrize("domain,command", [
    ("EVENT", "GRANT UPDATE(motivo) ON events_aup TO {role}"),
    ("GOV", "GRANT INSERT ON authorities_gov TO {role}"),
    ("EVENT", "ALTER POLICY event_runtime_insert ON events_aup WITH CHECK(true)"),
])
def test_gate_rejects_privilege_or_policy_drift(domains, domain, command):
    _, role, engine, _ = domains[domain]
    with engine.connect() as c, c.begin():
        c.exec_driver_sql(command.format(role='"'+role+'"'))
        c.exec_driver_sql('SET LOCAL ROLE "'+role+'"')
        with pytest.raises(RuntimeGateError):
            check_connection(c, domain, expected_role=role)
        # Keep drift inside a transaction; no contamination of subsequent tests.
        c.rollback()
