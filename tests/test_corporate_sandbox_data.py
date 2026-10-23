"""Isolated, read-only data gate tests. No network or real Neon/Clerk tokens."""
import pytest
from sqlalchemy import create_engine, text

from scripts.check_corporate_sandbox_data import (
    REQUIRED_EMPTY, require_empty, verify_role, check_data,
)


@pytest.fixture
def synthetic_connection():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS public")
        for table in sorted(set(sum((list(rows) for rows in REQUIRED_EMPTY.values()), []))):
            conn.execute(text(f"CREATE TABLE public.{table}(id TEXT NOT NULL)"))
        yield conn
    engine.dispose()


def test_empty_synthetic_schema_passes(synthetic_connection):
    for key, tables in REQUIRED_EMPTY.items():
        require_empty(synthetic_connection, tables, label=key)


@pytest.mark.parametrize("table", [
    "usuarios", "condominios_exo", "visitas", "evidencias",
    "corporate_organizations", "event_outbox", "arco_cases",
    "authorities_gov", "policies_gov", "events_aup",
])
def test_any_inherited_row_blocks_read_only(synthetic_connection, table):
    private_marker = "pii-should-never-appear-in-error-message"
    synthetic_connection.execute(
        text(f"INSERT INTO public.{table}(id) VALUES (:id)"),
        {"id": private_marker},
    )
    with pytest.raises(RuntimeError) as result:
        for key, tables in REQUIRED_EMPTY.items():
            require_empty(synthetic_connection, tables, label=key)
    assert "heredados" in str(result.value)
    assert private_marker not in str(result.value)


def test_missing_table_fails_closed(synthetic_connection):
    synthetic_connection.execute(text("DROP TABLE public.usuarios"))
    with pytest.raises(RuntimeError) as exc:
        require_empty(synthetic_connection, ("usuarios",), label="DATABASE_CORE_URL")
    assert "estructura" in str(exc.value)


class MappingResult:
    def __init__(self, mapping):
        self.mapping = mapping
    def mappings(self):
        return self
    def one(self):
        return self.mapping


class FakeRoleConnection:
    def __init__(self, db, role, **flags):
        self.row = dict(db=db, role=role, rolsuper=False, rolbypassrls=False,
                        rolcreatedb=False, rolcreaterole=False, rolreplication=False)
        self.row.update(flags)
    def execute(self, statement):
        return MappingResult(self.row)


@pytest.mark.parametrize("database,name,role", [
    ("neondb", "DATABASE_CORE_URL", "axs_core_app"),
    ("aup_gov", "DATABASE_GOV_URL", "axs_corp_sandbox_gov"),
    ("aup_event", "DATABASE_EVENT_URL", "axs_corp_sandbox_event"),
])
def test_role_matches_exact_database(database, name, role):
    verify_role(FakeRoleConnection(database, role), name=name)


@pytest.mark.parametrize("db,role,flag", [
    ("neondb", "neondb_owner", None),
    ("neondb", "axs_core_app", "rolbypassrls"),
    ("neondb", "axs_core_app", "rolcreatedb"),
    ("neondb", "axs_core_app", "rolsuper"),
    ("aup_gov", "axs_core_app", None),
    ("aup_event", "axs_corp_sandbox_event", "rolcreaterole"),
])
def test_role_rejects_privileged_or_cross_database_accounts(db, role, flag):
    flags = {flag: True} if flag else {}
    with pytest.raises(RuntimeError):
        verify_role(FakeRoleConnection(db, role, **flags), name={
            "neondb":"DATABASE_CORE_URL",
            "aup_gov":"DATABASE_GOV_URL",
            "aup_event":"DATABASE_EVENT_URL",
        }[db])


def test_check_data_rejects_missing_connection_before_network():
    with pytest.raises(RuntimeError):
        check_data({})
