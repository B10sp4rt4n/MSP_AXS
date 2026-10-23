"""Second, live-data predeploy gate for the isolated AXS Corporate sandbox.

Runs AFTER scripts/check_corporate_sandbox_config.py (which pins the Neon
branch, databases, roles and TLS), and BEFORE the API starts. Read-only.
A copied development branch containing users, homes, visits, evidence,
authorities, or events MUST NOT be exposed through a sandbox API.

Does NOT delete, anonymize, or print any database contents.
"""
import os
import sys

from sqlalchemy import create_engine, text
from scripts.check_corporate_sandbox_config import check as check_config


# Fixed identifiers, not derived from user input.
REQUIRED_EMPTY = {
    "DATABASE_CORE_URL": (
        "usuarios", "condominios_exo", "casas", "casetas",
        "visitas", "evidencias", "external_identities",
        "corporate_organizations", "corporate_memberships",
        "corporate_sites", "corporate_destinations", "corporate_site_assignments",
        "event_outbox", "security_outbox", "arco_cases",
    ),
    "DATABASE_GOV_URL": (
        "authorities_gov", "policies_gov", "delegations_gov",
    ),
    "DATABASE_EVENT_URL": ("events_aup",),
}
EXPECTED_ROLES = {
    "DATABASE_CORE_URL": "axs_core_app",
    "DATABASE_GOV_URL": "axs_corp_sandbox_gov",
    "DATABASE_EVENT_URL": "axs_corp_sandbox_event",
}
EXPECTED_DB = {
    "DATABASE_CORE_URL": "neondb",
    "DATABASE_GOV_URL": "aup_gov",
    "DATABASE_EVENT_URL": "aup_event",
}


def require_empty(connection, names: tuple[str, ...], *, label: str) -> None:
    """Fails on any inherited row or missing table; never exposes a row."""
    for table in names:
        try:
            has_row = connection.execute(
                text(f"SELECT EXISTS(SELECT 1 FROM public.{table} LIMIT 1)")
            ).scalar_one()
        except Exception as exc:
            raise RuntimeError(f"Sandbox: estructura incompleta o lectura denegada ({label})") from exc
        if has_row:
            raise RuntimeError(f"Sandbox: datos heredados presentes ({label}); API bloqueada")


def verify_role(connection, *, name: str) -> None:
    try:
        row = connection.execute(text("""
            SELECT current_database() AS db, current_user AS role,
                   r.rolsuper, r.rolbypassrls, r.rolcreatedb, r.rolcreaterole,
                   r.rolreplication
            FROM pg_roles r WHERE r.rolname=current_user
        """)).mappings().one()
        if (
            row["db"] != EXPECTED_DB[name]
            or row["role"] != EXPECTED_ROLES[name]
            or any(row[k] for k in (
                "rolsuper", "rolbypassrls", "rolcreatedb", "rolcreaterole",
                "rolreplication",
            ))
        ):
            raise ValueError("Incorrect or privileged role")
    except Exception as exc:
        raise RuntimeError(f"Sandbox: rol o base de datos incorrecto ({name})") from exc


def check_data(values: dict) -> None:
    """Read-only check; no password or database rows are returned."""
    check_config(values)
    for name, tables in REQUIRED_EMPTY.items():
        engine = None
        try:
            engine = create_engine(values[name], pool_pre_ping=True)
            if engine.dialect.name != "postgresql":
                raise ValueError("Wrong dialect")
            with engine.connect() as conn:
                verify_role(conn, name=name)
                require_empty(conn, tables, label=name)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Sandbox: conexión o estructura no verificable ({name})") from exc
        finally:
            if engine is not None:
                engine.dispose()


if __name__ == "__main__":
    try:
        check_data(os.environ)
        print("AXS corporate sandbox: databases empty, roles limited, deployment gate PASS")
    except Exception as exc:
        # Do not print exception chains: psycopg might include connection details.
        print(f"FAIL: sandbox no apto para arranque ({type(exc).__name__})", file=sys.stderr)
        sys.exit(1)
