"""C4: conciliación HTTP CORE/GOV real sobre PostgreSQL desechable (16+).

Ambas bases lógicas usan schemas efímeros distintos, conexiones independientes y
sesiones nuevas por petición. Nunca ejecutar contra Neon ni datos productivos.
EVENT permanece sintético; autenticación, GOV, transacciones y RLS son reales.
"""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from backend.main import app
from backend.core.auth.jwt import create_access_token
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import Base_CORE, EventOutbox, MSP, Usuario, get_core_db
from backend.db.core.corporate_operations import CorporateProvisioningOperation
from backend.db.event import get_event_db
from backend.db.gov import Authority, AuthorityType, Base_GOV, GovStatus, Policy, PolicyScope, get_gov_db
from backend.routers import corporate_superadmin_router as corporate
from backend.services import security_outbox
from backend.services.corporate_provisioner_db import get_provisioning_db


pytestmark = pytest.mark.integration
BASE = "/plataforma/corporativo/empresas"
REQUESTED = "solicitar_capacidades_directorio"
CONFIRMED = "confirmar_capacidades_directorio"
TABLE = "corporate_provisioning_operations"
C4 = "20261023_corporate_reconciliation_c4.sql"


def migration_sql(filename, schema):
    return (Path("migrations", filename).read_text()
            .replace("public.", schema + ".")
            .replace("schemaname='public'", f"schemaname='{schema}'")
            .replace("GRANT USAGE ON SCHEMA public TO", f"GRANT USAGE ON SCHEMA {schema} TO")
            .replace("TO axs_core_app", "TO axs_rls_ci")
            .replace("%I", "%%I").replace("%s", "%%s"))


@pytest.fixture
def postgres_reconciliation(db_event_session, monkeypatch):
    normal = os.getenv("AXS_TEST_POSTGRES_URL")
    admin = os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not normal or not admin:
        pytest.skip("Solo CI PostgreSQL descartable")
    for value in (normal, admin):
        parsed = make_url(value)
        assert parsed.get_backend_name() == "postgresql"
        assert parsed.host in ("localhost", "127.0.0.1")
        assert parsed.database == "axs_rls_ci"
    assert make_url(admin).username == "postgres"
    assert make_url(normal).username == "axs_rls_ci"

    # Different pools, schemas and ORM sessions: no shared SQLite transaction.
    core_root, gov_root = create_engine(admin), create_engine(admin)
    core_app, gov_app = create_engine(normal), create_engine(normal)
    suffix = uuid4().hex[:12]
    core_schema, gov_schema = "axs_c4_core_" + suffix, "axs_c4_gov_" + suffix
    core_owner = core_root.execution_options(schema_translate_map={None: core_schema})
    gov_owner = gov_root.execution_options(schema_translate_map={None: gov_schema})
    core_scoped = core_app.execution_options(schema_translate_map={None: core_schema})
    gov_scoped = gov_app.execution_options(schema_translate_map={None: gov_schema})
    previous = app.dependency_overrides.copy()
    faults = {}
    sessions = {"core": [], "gov": [], "provisioner": []}
    role_existed = True

    class ProvisionerSession(Session):
        def commit(self):
            phase = self.info.pop("commit_phase", None)
            if phase and faults.pop(phase + "_before_commit", False):
                raise RuntimeError("synthetic CORE failure before durable commit")
            lose_ack = self.info.pop("lose_confirmation_ack", False)
            pause = self.info.pop("pause_after_prepare", None)
            super().commit()
            if phase and faults.pop(phase + "_after_commit", False):
                raise RuntimeError("synthetic CORE acknowledgement loss after durable commit")
            if pause:
                prepared, release = pause
                prepared.set()
                assert release.wait(15), "Test did not release the committed CORE preparation"
            if lose_ack:
                # Durable commit really happened; only its acknowledgement is lost.
                raise RuntimeError("synthetic CORE confirmation acknowledgement loss")

    class GovSession(Session):
        def commit(self):
            if faults.pop("gov_before_commit", False):
                raise RuntimeError("synthetic GOV failure before commit")
            lose_ack = faults.pop("gov_after_commit", False)
            super().commit()
            if lose_ack:
                raise RuntimeError("synthetic GOV acknowledgement loss after durable commit")

    @event.listens_for(ProvisionerSession, "after_begin")
    def set_restricted_role(session, transaction, connection):
        connection.exec_driver_sql("SET LOCAL ROLE axs_corporate_provisioner")

    core_factory = sessionmaker(bind=core_scoped, autoflush=False)
    gov_factory = sessionmaker(bind=gov_scoped, class_=GovSession, autoflush=False)
    provisioner_factory = sessionmaker(bind=core_owner, class_=ProvisionerSession, autoflush=False)

    def dependency(factory, kind):
        def fresh_session():
            with factory() as db:
                # Hold references to prove different HTTP requests never reuse sessions.
                sessions[kind].append(db)
                yield db
        return fresh_session

    try:
        with core_root.begin() as connection:
            assert int(connection.scalar(text("SHOW server_version_num"))) // 10000 >= 16
            role_existed = bool(connection.scalar(text(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corporate_provisioner')")))
            connection.execute(text(f"CREATE SCHEMA {core_schema}"))
            connection.execute(text(f"CREATE SCHEMA {gov_schema}"))
        Base_CORE.metadata.create_all(core_owner)
        Base_GOV.metadata.create_all(gov_owner)
        assert CorporateProvisioningOperation.__table__.metadata is not Base_CORE.metadata
        assert TABLE not in inspect(core_root).get_table_names(schema=core_schema)

        for filename in (
            "20261023_corporate_directory_c1.sql",
            "20261023_corporate_superadmin_c2.sql",
            "20261023_corporate_reconciliation_c4.sql",
        ):
            sql = migration_sql(filename, core_schema)
            with core_root.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.exec_driver_sql(sql)
                if filename != C4:
                    connection.exec_driver_sql(sql)  # C1/C2 permit replays; C4 fails closed.

        with core_root.begin() as connection:
            connection.execute(text(f"GRANT USAGE ON SCHEMA {core_schema}, {gov_schema} TO axs_rls_ci"))
            connection.execute(text(
                f"GRANT SELECT ON {core_schema}.usuarios, {core_schema}.msps_exo TO axs_rls_ci"))
            connection.execute(text(
                f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {gov_schema} TO axs_rls_ci"))
            connection.execute(text(f"ALTER TABLE {core_schema}.event_outbox ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {core_schema}.event_outbox FORCE ROW LEVEL SECURITY"))
            connection.execute(text(
                f"CREATE POLICY c4_tenant ON {core_schema}.event_outbox "
                "USING (condominio_id=current_setting('app.tenant_id',true)) "
                "WITH CHECK (condominio_id=current_setting('app.tenant_id',true))"))
        with Session(core_owner) as db:
            db.add(MSP(msp_id="provider", nombre="Proveedor sintético C4"))
            db.add_all([
                Usuario(usuario_id="owner", email="owner@example.test", rol="RESIDENTE"),
                Usuario(usuario_id="super", email="super@example.test", rol="MSP_ADMIN"),
            ])
            db.commit()
        with Session(gov_owner) as db:
            db.add(Authority(authority_id="global_c4", identity_id="super",
                             tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
            db.commit()

        monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
        monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "true")
        monkeypatch.setenv("TESTING", "1")
        monkeypatch.setattr(security_outbox, "SessionFactory", sessionmaker(bind=core_owner))
        app.dependency_overrides[get_core_db] = dependency(core_factory, "core")
        app.dependency_overrides[get_gov_db] = dependency(gov_factory, "gov")
        app.dependency_overrides[get_provisioning_db] = dependency(provisioner_factory, "provisioner")
        app.dependency_overrides[get_event_db] = lambda: db_event_session
        headers = {"Authorization": "Bearer " + create_access_token("super", "MSP_ADMIN")}
        with TestClient(app, raise_server_exceptions=False) as client:
            yield SimpleNamespace(
                client=client, headers=headers, core=core_owner, gov=gov_owner,
                root=core_root, schema=core_schema, provisioner=provisioner_factory, runtime=core_scoped,
                faults=faults, sessions=sessions,
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        core_app.dispose()
        gov_app.dispose()
        with core_root.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {gov_schema} CASCADE"))
            connection.execute(text(f"DROP SCHEMA IF EXISTS {core_schema} CASCADE"))
            if not role_existed and connection.scalar(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corporate_provisioner')")):
                connection.execute(text("DROP OWNED BY axs_corporate_provisioner"))
                connection.execute(text("DROP ROLE IF EXISTS axs_corporate_provisioner"))
        core_root.dispose()
        gov_root.dispose()


def sqlstate(error):
    # Both psycopg 3 and psycopg2 CI URLs are supported.
    return getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)


def company(env):
    response = env.client.post(BASE, headers=env.headers, json={
        "request_id": str(uuid4()), "nombre": "Empresa sintética C4",
        "msp_id": "provider", "owner_user_id": "owner",
        "privacy_contact": "privacidad@example.test",
        "privacy_notice_url": "https://example.test/privacidad",
        "privacy_notice_version": "synthetic-c4",
    })
    assert response.status_code == 201, response.text
    return response.json()["tenant_id"]


def limits(max_sedes=2, max_destinos_por_sede=4, request_id=None, expected_revision=0):
    return {"request_id": request_id or str(uuid4()), "expected_revision": expected_revision,
            "max_sedes": max_sedes,
            "max_destinos_por_sede": max_destinos_por_sede}


def put(env, tenant, body):
    return env.client.put(f"{BASE}/{tenant}/capacidades", headers=env.headers, json=body)


def status(env, tenant):
    response = env.client.get(f"{BASE}/{tenant}", headers=env.headers)
    assert response.status_code == 200, response.text
    return response.json()


def activate(env, tenant):
    return env.client.post(f"{BASE}/{tenant}/habilitar-directorio", headers=env.headers,
                           json={"confirmacion": True})


def operations(env, tenant):
    with Session(env.core) as db:
        return [{column.name: getattr(row, column.name) for column in row.__table__.columns}
                for row in db.query(CorporateProvisioningOperation).filter_by(tenant_id=tenant).all()]


def audit_counts(env, tenant):
    with Session(env.core) as db:
        events = {row.event_uid: row.payload for row in db.query(EventOutbox)
                  .filter_by(condominio_id=tenant).all()}
        for operation in db.query(CorporateProvisioningOperation).filter_by(tenant_id=tenant).all():
            requested = events[operation.request_event_uid]
            assert requested["accion"] == REQUESTED
            for key in ("request_id", "payload_hash", "revision"):
                assert requested["metadata_json"][key] == getattr(operation, key)
            if operation.estado == "confirmed":
                confirmed = events[operation.confirmation_event_uid]
                assert confirmed["accion"] == CONFIRMED
                for key in ("request_id", "payload_hash", "revision"):
                    assert confirmed["metadata_json"][key] == getattr(operation, key)
                assert confirmed["metadata_json"]["requested_by"] == operation.requested_by
            else:
                assert operation.confirmation_event_uid is None
        actions = [payload["accion"] for payload in events.values()]
        return actions.count(REQUESTED), actions.count(CONFIRMED)


def gov_snapshot(env, tenant):
    with Session(env.gov) as db:
        return {row.policy_id: {
            "limites": row.limites, "metadata_json": row.metadata_json,
            "estado": row.estado, "valida_desde": row.valida_desde,
            "valida_hasta": row.valida_hasta,
        } for row in db.query(Policy).filter_by(target_tenant_id=tenant).all()}


def assert_policies(env, tenant, body, operation):
    snapshot = gov_snapshot(env, tenant)
    assert len(snapshot) == 2
    for action, key in (("crear_sede_corporativa", "max_sedes"),
                        ("crear_destino_corporativo", "max_destinos_por_sede")):
        policy = snapshot[corporate.policy_key(tenant, action)]
        assert policy["limites"] == {"max_count": body[key]}
        assert policy["metadata_json"]["axs_corporate_operation"] == {
            "request_id": body["request_id"], "payload_hash": operation["payload_hash"],
            "revision": operation["revision"],
        }


def fail_audit_once(monkeypatch, action):
    original = corporate.audit
    armed = [True]

    def failing(db, tenant_id, actor, request, accion, **kwargs):
        uid = original(db, tenant_id, actor, request, accion, **kwargs)
        if accion == action and armed[0]:
            armed[0] = False
            raise RuntimeError("synthetic failure after queued audit, before CORE commit")
        return uid
    monkeypatch.setattr(corporate, "audit", failing)


def test_request_audit_and_operation_are_atomic(postgres_reconciliation, monkeypatch):
    env = postgres_reconciliation
    tenant, body = company(env), limits()
    fail_audit_once(monkeypatch, REQUESTED)
    failed = put(env, tenant, body)
    assert failed.status_code == 503, failed.text
    assert operations(env, tenant) == []
    assert audit_counts(env, tenant) == (0, 0)
    assert gov_snapshot(env, tenant) == {}
    retried = put(env, tenant, body)
    assert retried.status_code == 200, retried.text
    assert audit_counts(env, tenant) == (1, 1)


def test_recovers_committed_gov_with_fresh_sessions(postgres_reconciliation, monkeypatch):
    env = postgres_reconciliation
    tenant, body = company(env), limits()
    initial = status(env, tenant)
    assert initial["capacidades_confirmadas"] is False
    assert initial["capacidades_operacion"] is None
    missing_id = put(env, tenant, {key: value for key, value in body.items() if key != "request_id"})
    assert missing_id.status_code == 422
    fail_audit_once(monkeypatch, CONFIRMED)
    failed = put(env, tenant, body)
    assert failed.status_code == 503, failed.text
    pending, = operations(env, tenant)
    assert pending["estado"] == "pending" and pending["confirmed_at"] is None
    assert audit_counts(env, tenant) == (1, 0)
    assert_policies(env, tenant, body, pending)
    snapshot = gov_snapshot(env, tenant)
    current = status(env, tenant)
    assert current["capacidades_confirmadas"] is False
    assert current["capacidades_operacion"]["request_id"] == body["request_id"]
    assert current["capacidades_operacion"]["estado"] == "pending"
    assert current["capacidades_revision"] == 1
    assert current["capacidades_operacion"]["revision"] == 1
    assert current["capacidades_operacion"]["expected_revision"] == 0
    assert current["capacidades_operacion"]["max_sedes"] == body["max_sedes"]
    assert current["capacidades_operacion"]["max_destinos_por_sede"] == body["max_destinos_por_sede"]
    assert activate(env, tenant).status_code == 409

    used_sessions = len(env.sessions["provisioner"])
    recovered = put(env, tenant, body)
    assert recovered.status_code == 200, recovered.text
    assert len(env.sessions["provisioner"]) > used_sessions
    assert len({id(session) for session in env.sessions["provisioner"]}) == len(env.sessions["provisioner"])
    assert len({id(session) for session in env.sessions["gov"]}) == len(env.sessions["gov"])
    confirmed, = operations(env, tenant)
    assert confirmed["estado"] == "confirmed" and confirmed["confirmed_at"] is not None
    assert audit_counts(env, tenant) == (1, 1)
    assert gov_snapshot(env, tenant) == snapshot  # Recovery confirms, never reapplies GOV.
    assert status(env, tenant)["capacidades_confirmadas"] is True
    assert activate(env, tenant).status_code == 200


def test_lost_core_commit_ack_replays_without_duplicates(postgres_reconciliation, monkeypatch):
    env = postgres_reconciliation
    tenant, body = company(env), limits()
    original = corporate.audit
    armed = [True]

    def lose_ack(db, tenant_id, actor, request, accion, **kwargs):
        uid = original(db, tenant_id, actor, request, accion, **kwargs)
        if accion == CONFIRMED and armed[0]:
            armed[0] = False
            db.info["lose_confirmation_ack"] = True
        return uid
    monkeypatch.setattr(corporate, "audit", lose_ack)
    failed = put(env, tenant, body)
    assert failed.status_code == 503, failed.text
    confirmed, = operations(env, tenant)
    assert confirmed["estado"] == "confirmed"
    assert confirmed["confirmed_at"] is not None
    assert audit_counts(env, tenant) == (1, 1)
    snapshot = gov_snapshot(env, tenant)
    replay = put(env, tenant, body)
    assert replay.status_code == 200, replay.text
    assert operations(env, tenant) == [confirmed]
    assert audit_counts(env, tenant) == (1, 1)
    assert gov_snapshot(env, tenant) == snapshot
    assert status(env, tenant)["capacidades_confirmadas"] is True


def test_same_id_concurrency_has_one_request_and_confirmation(postgres_reconciliation, monkeypatch):
    env = postgres_reconciliation
    tenant, body = company(env), limits()
    entered, release = threading.Event(), threading.Event()
    original = corporate.audit

    def hold_first_request(db, tenant_id, actor, request, accion, **kwargs):
        uid = original(db, tenant_id, actor, request, accion, **kwargs)
        if accion == REQUESTED:
            entered.set()
            assert release.wait(10), "Concurrent test did not release CORE transaction"
        return uid
    monkeypatch.setattr(corporate, "audit", hold_first_request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(put, env, tenant, body)
        try:
            assert entered.wait(10), "First HTTP request did not reach the atomic request audit"
            second = pool.submit(put, env, tenant, body)
            # Prove a real PostgreSQL lock conflict, not just sequential HTTP replays.
            deadline = time.monotonic() + 5
            blocked = False
            while time.monotonic() < deadline and not blocked:
                with env.root.connect() as connection:
                    blocked = bool(connection.scalar(text(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                        "WHERE datname=current_database() AND wait_event_type='Lock' "
                        "AND cardinality(pg_blocking_pids(pid)) > 0 AND query LIKE :schema)"),
                        {"schema": "%" + env.schema + "%"}))
                if not blocked:
                    time.sleep(0.02)
            assert blocked, "Second HTTP request did not wait for the first tenant lock"
        finally:
            release.set()
        responses = [first.result(timeout=15), second.result(timeout=15)]
    assert [response.status_code for response in responses] == [200, 200], [r.text for r in responses]
    operation, = operations(env, tenant)
    assert operation["estado"] == "confirmed"
    assert audit_counts(env, tenant) == (1, 1)
    assert_policies(env, tenant, body, operation)


def test_pending_blocks_new_id_and_old_replay_cannot_revert(postgres_reconciliation, monkeypatch):
    env = postgres_reconciliation
    tenant, first, second = company(env), limits(), limits(3, 5, expected_revision=1)
    fail_audit_once(monkeypatch, CONFIRMED)
    assert put(env, tenant, first).status_code == 503
    snapshot = gov_snapshot(env, tenant)
    assert put(env, tenant, second).status_code == 409
    assert put(env, tenant, {**first, "max_sedes": 3}).status_code == 409
    assert len(operations(env, tenant)) == 1
    assert audit_counts(env, tenant) == (1, 0)
    assert gov_snapshot(env, tenant) == snapshot
    assert put(env, tenant, first).status_code == 200
    # A new UUID cannot replay a stale form after the prior revision committed.
    assert put(env, tenant, limits(3, 5, expected_revision=0)).status_code == 409
    assert put(env, tenant, second).status_code == 200
    latest = gov_snapshot(env, tenant)
    assert put(env, tenant, first).status_code == 409
    assert put(env, tenant, {**second, "max_sedes": 4}).status_code == 409
    assert gov_snapshot(env, tenant) == latest
    assert len(operations(env, tenant)) == 2
    assert audit_counts(env, tenant) == (2, 2)
    current = status(env, tenant)
    assert current["capacidades_confirmadas"] is True
    assert current["capacidades_operacion"]["request_id"] == second["request_id"]
    assert current["capacidades"] == {"max_sedes": 3, "max_destinos_por_sede": 5}
    # ABA: a new third intent legitimately returns to A's numeric quotas, but
    # A's old reference is still superseded and cannot be treated as confirmed.
    third = limits(expected_revision=2)
    assert put(env, tenant, third).status_code == 200
    returned_to_a = gov_snapshot(env, tenant)
    assert put(env, tenant, first).status_code == 409
    assert gov_snapshot(env, tenant) == returned_to_a
    assert len(operations(env, tenant)) == 3
    assert audit_counts(env, tenant) == (3, 3)
    assert status(env, tenant)["capacidades_operacion"]["request_id"] == third["request_id"]
    assert status(env, tenant)["capacidades_revision"] == 3


@pytest.mark.parametrize("drift", ["marker", "snapshot"])
def test_pending_replay_refuses_gov_drift(postgres_reconciliation, monkeypatch, drift):
    env = postgres_reconciliation
    tenant, first, second = company(env), limits(), limits(3, 5, expected_revision=1)
    assert put(env, tenant, first).status_code == 200
    if drift == "marker":
        fail_audit_once(monkeypatch, CONFIRMED)
    else:
        env.faults["gov_before_commit"] = True
    failed = put(env, tenant, second)
    assert failed.status_code == 503, failed.text
    with Session(env.gov) as db:
        policy = db.query(Policy).filter_by(
            policy_id=corporate.policy_key(tenant, "crear_sede_corporativa")).one()
        if drift == "marker":
            metadata = dict(policy.metadata_json)
            metadata["axs_corporate_operation"] = {
                **metadata["axs_corporate_operation"], "request_id": str(uuid4())}
            policy.metadata_json = metadata
        else:
            policy.limites = {"max_count": 99}
        db.commit()
    snapshot = gov_snapshot(env, tenant)
    rejected = put(env, tenant, second)
    assert rejected.status_code == 409, rejected.text
    pending = next(row for row in operations(env, tenant) if row["request_id"] == second["request_id"])
    assert pending["estado"] == "needs_review" and pending["confirmed_at"] is None
    assert pending["confirmation_event_uid"] is None
    assert audit_counts(env, tenant) == (2, 1)
    assert gov_snapshot(env, tenant) == snapshot
    assert status(env, tenant)["capacidades_confirmadas"] is False
    assert activate(env, tenant).status_code == 409
    assert put(env, tenant, second).status_code == 409
    assert put(env, tenant, limits(6, 7, expected_revision=2)).status_code == 409
    assert gov_snapshot(env, tenant) == snapshot
    assert len(operations(env, tenant)) == 2


def test_operations_force_rls_and_exact_minimum_privileges(postgres_reconciliation):
    env = postgres_reconciliation
    tenant_a, tenant_b, body = company(env), company(env), limits()
    # Request IDs are tenant-scoped, not a global cross-tenant uniqueness channel.
    assert put(env, tenant_a, body).status_code == 200
    assert put(env, tenant_b, body).status_code == 200
    table = f"{env.schema}.{TABLE}"
    with env.root.connect() as connection:
        rls = connection.execute(text(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid=CAST(:table AS regclass)"),
            {"table": table}).one()
        assert tuple(rls) == (True, True)
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            permitted = connection.scalar(text(
                "SELECT has_table_privilege('axs_corporate_provisioner', :table, :privilege)"),
                {"table": table, "privilege": privilege})
            assert permitted is (privilege in ("SELECT", "INSERT")), privilege
        for column in CorporateProvisioningOperation.__table__.columns:
            permitted = connection.scalar(text(
                "SELECT has_column_privilege('axs_corporate_provisioner', :table, :column, 'UPDATE')"),
                {"table": table, "column": column.name})
            assert permitted is (column.name in ("estado", "confirmed_at", "confirmation_event_uid")), column.name

    with Session(env.runtime) as db:
        with pytest.raises(DBAPIError) as denied_error:
            db.query(CorporateProvisioningOperation).count()
        assert sqlstate(denied_error.value) == "42501"
        db.rollback()
    with env.provisioner() as db:
        _set_postgres_tenant(db, tenant_a)
        with pytest.raises(DBAPIError) as denied_error:
            db.query(EventOutbox).count()
        assert sqlstate(denied_error.value) == "42501"
        db.rollback()
    with env.provisioner() as db:
        assert db.query(CorporateProvisioningOperation).count() == 0
        _set_postgres_tenant(db, tenant_a)
        visible, = db.query(CorporateProvisioningOperation).all()
        assert visible.tenant_id == tenant_a
        assert db.query(CorporateProvisioningOperation).filter_by(tenant_id=tenant_b).count() == 0
        changed = db.execute(text(f"UPDATE {table} SET estado=estado WHERE tenant_id=:tenant"),
                             {"tenant": tenant_b})
        assert changed.rowcount == 0
        db.execute(text(f"UPDATE {table} SET estado=estado, confirmed_at=confirmed_at WHERE tenant_id=:tenant"),
                   {"tenant": tenant_a})
        db.commit()

    denied = [f"UPDATE {table} SET {column}={column}" for column in (
        "tenant_id", "request_id", "revision", "payload", "payload_hash", "requested_by",
        "expected_gov", "request_event_uid", "created_at")]
    denied.extend((f"DELETE FROM {table}", f"TRUNCATE {table}",
                   f"ALTER TABLE {table} ADD COLUMN forbidden integer",
                   f"CREATE TABLE {env.schema}.forbidden (id integer)"))
    for statement in denied:
        with env.provisioner() as db:
            _set_postgres_tenant(db, tenant_a)
            with pytest.raises(DBAPIError) as denied_error:
                db.execute(text(statement))
            assert sqlstate(denied_error.value) == "42501", statement
            db.rollback()
    with env.provisioner() as db:
        _set_postgres_tenant(db, tenant_a)
        db.add(CorporateProvisioningOperation(
            tenant_id=tenant_b, request_id=str(uuid4()), revision=2, request_event_uid="evt_synthetic", payload={"max_sedes": 1, "max_destinos_por_sede": 1},
            payload_hash="0" * 64, requested_by="super", expected_gov={}, estado="pending",
            created_at=datetime.utcnow(),
        ))
        with pytest.raises(DBAPIError) as denied_error:
            db.commit()
        assert sqlstate(denied_error.value) == "42501"
        db.rollback()
    assert len(operations(env, tenant_a)) == len(operations(env, tenant_b)) == 1


def test_prepared_request_cannot_override_concurrent_needs_review(postgres_reconciliation, monkeypatch):
    env = postgres_reconciliation
    tenant, body = company(env), limits()
    prepared, release = threading.Event(), threading.Event()
    original = corporate.audit

    def pause_after_preparation(db, tenant_id, actor, request, accion, **kwargs):
        uid = original(db, tenant_id, actor, request, accion, **kwargs)
        if accion == REQUESTED:
            db.info["pause_after_prepare"] = (prepared, release)
        return uid
    monkeypatch.setattr(corporate, "audit", pause_after_preparation)

    with ThreadPoolExecutor(max_workers=1) as pool:
        original_request = pool.submit(put, env, tenant, body)
        try:
            assert prepared.wait(10), "Original HTTP request did not commit its preparation"
            assert not original_request.done()
            pending, = operations(env, tenant)
            assert pending["estado"] == "pending" and pending["expected_gov"] == {}
            assert audit_counts(env, tenant) == (1, 0)
            # While the first call has released its CORE lock, an external GOV
            # change makes a second request persist needs_review for the same ID.
            with Session(env.gov) as db:
                db.add(Policy(
                    policy_id=corporate.policy_key(tenant, "crear_sede_corporativa"),
                    nombre="Cambio sintético durante preparación", ambito=PolicyScope.TENANT,
                    target_tenant_id=tenant, accion_objetivo="crear_sede_corporativa",
                    limites={"max_count": 99}, estado=GovStatus.ACTIVO,
                ))
                db.commit()
            rejected = put(env, tenant, body)
            assert rejected.status_code == 409, rejected.text
            reviewed, = operations(env, tenant)
            assert reviewed["estado"] == "needs_review"
            # Restore the original snapshot. A stale in-memory pending state
            # must not resurrect the operation now that review is durable.
            with Session(env.gov) as db:
                db.query(Policy).filter_by(target_tenant_id=tenant).delete()
                db.commit()
            assert gov_snapshot(env, tenant) == {}
        finally:
            release.set()
        resumed = original_request.result(timeout=15)
    assert resumed.status_code == 409, resumed.text
    reviewed, = operations(env, tenant)
    assert reviewed["estado"] == "needs_review"
    assert reviewed["confirmation_event_uid"] is None and reviewed["confirmed_at"] is None
    assert audit_counts(env, tenant) == (1, 0)
    assert gov_snapshot(env, tenant) == {}
    with Session(env.core) as db:
        conflicts = [row for row in db.query(EventOutbox).filter_by(condominio_id=tenant).all()
                     if row.payload["accion"] == "conflicto_capacidades_directorio"]
        assert len(conflicts) == 1
    assert status(env, tenant)["capacidades_confirmadas"] is False
    assert activate(env, tenant).status_code == 409


@pytest.mark.parametrize("permissive_policy", [False, True])
def test_c4_rerun_fails_without_changing_acl_or_policy(postgres_reconciliation, permissive_policy):
    env = postgres_reconciliation
    table = f"{env.schema}.{TABLE}"
    with env.root.begin() as connection:
        # Existing or suspicious objects must not gain privileges from a rerun.
        connection.execute(text(f"REVOKE ALL ON {table} FROM axs_corporate_provisioner"))
        connection.execute(text(
            f"REVOKE UPDATE (estado,confirmed_at,confirmation_event_uid) ON {table} "
            "FROM axs_corporate_provisioner"))
        if permissive_policy:
            connection.execute(text(
                f"CREATE POLICY unexpected_permissive ON {table} USING (true) WITH CHECK (true)"))

    def catalog_state():
        with env.root.connect() as connection:
            table_state = connection.execute(text(
                "SELECT relacl::text,relrowsecurity,relforcerowsecurity FROM pg_class "
                "WHERE oid=CAST(:table AS regclass)"), {"table": table}).one()
            columns = connection.execute(text(
                "SELECT attname,attacl::text FROM pg_attribute WHERE attrelid=CAST(:table AS regclass) "
                "AND attnum>0 ORDER BY attnum"), {"table": table}).all()
            policies = connection.execute(text(
                "SELECT policyname,roles::text,cmd,qual,with_check FROM pg_policies "
                "WHERE schemaname=:schema AND tablename=:table ORDER BY policyname"),
                {"schema": env.schema, "table": TABLE}).all()
            return table_state, columns, policies

    before = catalog_state()
    with env.root.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        with pytest.raises(DBAPIError) as duplicate:
            connection.exec_driver_sql(migration_sql(C4, env.schema))
        assert sqlstate(duplicate.value) == "42P07"
        connection.exec_driver_sql("ROLLBACK")
    assert catalog_state() == before
    with env.root.connect() as connection:
        assert connection.scalar(text(
            "SELECT has_table_privilege('axs_corporate_provisioner',:table,'SELECT,INSERT,UPDATE,DELETE')"),
            {"table": table}) is False
        assert connection.scalar(text(
            "SELECT has_column_privilege('axs_corporate_provisioner',:table,'estado','UPDATE')"),
            {"table": table}) is False


def test_c4_unexpected_default_acl_rolls_back_before_grants(postgres_reconciliation):
    env = postgres_reconciliation
    schema = env.schema + "_default_acl"
    try:
        with env.root.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
            connection.execute(text(f"CREATE TABLE {schema}.corporate_organizations (tenant_id varchar PRIMARY KEY)"))
            connection.execute(text(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT ON TABLES TO axs_rls_ci"))
        with env.root.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            with pytest.raises(DBAPIError) as inherited_acl:
                connection.exec_driver_sql(migration_sql(C4, schema))
            assert sqlstate(inherited_acl.value) == "P0001"
            assert "Unexpected inherited/default privileges" in str(inherited_acl.value.orig)
            connection.exec_driver_sql("ROLLBACK")
        # The entire explicit transaction, including table and policy creation,
        # rolls back. No journal or provisioner grants survive the rejection.
        assert inspect(env.root).get_table_names(schema=schema) == ["corporate_organizations"]
        with env.root.connect() as connection:
            assert connection.scalar(text(
                "SELECT count(*) FROM pg_policies WHERE schemaname=:schema"), {"schema": schema}) == 0
    finally:
        with env.root.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))


@pytest.mark.parametrize("phase,moment", [
    ("core_prepare", "before"), ("core_prepare", "after"),
    ("gov", "before"), ("gov", "after"),
    ("core_confirm", "before"), ("core_confirm", "after"),
])
def test_every_commit_boundary_recovers_without_false_success(
    postgres_reconciliation, monkeypatch, phase, moment,
):
    env = postgres_reconciliation
    tenant, body = company(env), limits()
    original = corporate.audit

    def mark_commit_phase(db, tenant_id, actor, request, accion, **kwargs):
        uid = original(db, tenant_id, actor, request, accion, **kwargs)
        if accion in (REQUESTED, CONFIRMED):
            db.info["commit_phase"] = "core_prepare" if accion == REQUESTED else "core_confirm"
        return uid
    monkeypatch.setattr(corporate, "audit", mark_commit_phase)
    fault = phase + "_" + moment + "_commit"
    env.faults[fault] = True
    failed = put(env, tenant, body)
    assert failed.status_code == 503, failed.text
    assert fault not in env.faults, "Requested commit boundary was never exercised"

    # These checks run through independent connections after the route's rollback.
    # An error before commit rolls back; an error after super().commit() cannot.
    saved = operations(env, tenant)
    if phase == "core_prepare" and moment == "before":
        assert saved == []
        assert audit_counts(env, tenant) == (0, 0)
    else:
        operation, = saved
        is_confirmed = phase == "core_confirm" and moment == "after"
        assert operation["estado"] == ("confirmed" if is_confirmed else "pending")
        assert (operation["confirmed_at"] is not None) is is_confirmed
        assert (operation["confirmation_event_uid"] is not None) is is_confirmed
        assert audit_counts(env, tenant) == (1, 1 if is_confirmed else 0)
    gov_was_committed = phase == "core_confirm" or (phase == "gov" and moment == "after")
    before_retry = gov_snapshot(env, tenant)
    if gov_was_committed:
        assert_policies(env, tenant, body, saved[0])
    else:
        assert before_retry == {}

    prior_core = len(env.sessions["provisioner"])
    prior_gov = len(env.sessions["gov"])
    retry = put(env, tenant, body)
    assert retry.status_code == 200, retry.text
    assert len(env.sessions["provisioner"]) > prior_core
    assert len(env.sessions["gov"]) > prior_gov
    assert env.sessions["provisioner"][-1] is not env.sessions["provisioner"][prior_core - 1]
    assert env.sessions["gov"][-1] is not env.sessions["gov"][prior_gov - 1]
    confirmed, = operations(env, tenant)
    assert confirmed["estado"] == "confirmed" and confirmed["confirmed_at"] is not None
    assert audit_counts(env, tenant) == (1, 1)
    assert_policies(env, tenant, body, confirmed)
    if gov_was_committed:
        assert gov_snapshot(env, tenant) == before_retry
    final_snapshot = gov_snapshot(env, tenant)
    assert put(env, tenant, body).status_code == 200
    assert operations(env, tenant) == [confirmed]
    assert audit_counts(env, tenant) == (1, 1)
    assert gov_snapshot(env, tenant) == final_snapshot
    assert status(env, tenant)["capacidades_confirmadas"] is True
