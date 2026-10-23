"""Manual, guarded schema bootstrap for the three EMPTY AXS Corporate sandbox DBs.

Never run from Railway deploy/start commands. This uses schema owner credentials
only while manually initializing brand-new, empty databases and never copies data.
Every table is FORCE RLS and receives NO runtime grants. A separate reviewed
policy/grants migration must precede any live API test.

Example:
  AXS_CORPORATE_SCHEMA_BOOTSTRAP_CONFIRM=only-empty-axs-corporate-sandbox \\
  AXS_CORPORATE_BOOTSTRAP_CORE_URL=... \\
  AXS_CORPORATE_BOOTSTRAP_GOV_URL=... \\
  AXS_CORPORATE_BOOTSTRAP_EVENT_URL=... \\
  python scripts/bootstrap_corporate_sandbox_schemas.py --apply

The operation is NOT atomic across the three PostgreSQL databases; a failure
may leave a partially initialized sandbox. Inspect it; never retry by force.
"""
import argparse
import os
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine, text

from scripts.check_corporate_sandbox_config import ENDPOINT, HOSTS

TARGETS = (
    ("CORE", "axs_corp_core_sbx", "backend.db.core.models", "Base_CORE"),
    ("GOV", "axs_corp_gov_sbx", "backend.db.gov.models", "Base_GOV"),
    ("EVENT", "axs_corp_event_sbx", "backend.db.event.models", "Base_EVENT"),
)
CONFIRM = "only-empty-axs-corporate-sandbox"


def check_bootstrap_url(url: str, expected_db: str) -> None:
    """No secret is included in exception messages."""
    try:
        value = urlsplit(url)
        query = parse_qs(value.query)
        if (
            value.scheme not in ("postgresql", "postgresql+psycopg")
            or value.hostname not in HOSTS
            or value.path != "/" + expected_db
            or value.username != "neondb_owner"
            or not value.password
            or value.fragment
            or query.get("sslmode", [None])[-1] not in ("require", "verify-ca", "verify-full")
        ):
            raise ValueError("Not a sandbox owner URL")
    except Exception as exc:
        raise RuntimeError(f"Bootstrap: conexión incompatible con base {expected_db}") from exc


def assert_empty_database(conn, expected_db: str) -> None:
    """Fail closed if any application table/view exists, or role/db differs."""
    actual = conn.execute(text("SELECT current_database(), current_user")).one()
    if actual[0] != expected_db or actual[1] != "neondb_owner":
        raise RuntimeError(f"Bootstrap: base o propietario incorrecto ({expected_db})")
    existing = conn.execute(text("""
        SELECT count(*) FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')
    """)).scalar_one()
    if existing:
        raise RuntimeError(f"Bootstrap: base no vacía ({expected_db})")


def get_metadata(which: str):
    # Importing models registers all expected entities; no connection is opened.
    if which == "CORE":
        from backend.db.core.engine import Base_CORE
        from backend.db.core import models  # noqa: F401
        return Base_CORE.metadata
    if which == "GOV":
        from backend.db.gov.engine import Base_GOV
        from backend.db.gov import models  # noqa: F401
        return Base_GOV.metadata
    from backend.db.event.engine import Base_EVENT
    from backend.db.event import models  # noqa: F401
    return Base_EVENT.metadata


def install_schema(conn, which: str) -> int:
    meta = get_metadata(which)
    # create_all does not populate business objects, identities or events.
    meta.create_all(conn, checkfirst=False)
    for name in sorted(meta.tables):
        if name != meta.tables[name].name or not name.replace("_", "").isalnum():
            raise RuntimeError("Bootstrap: identificador SQL inesperado")
        conn.execute(text(f'ALTER TABLE public."{name}" ENABLE ROW LEVEL SECURITY'))
        conn.execute(text(f'ALTER TABLE public."{name}" FORCE ROW LEVEL SECURITY'))
    if which == "CORE":
        for name in ("corporate_organizations", "corporate_sites",
                     "corporate_destinations", "corporate_memberships",
                     "corporate_site_assignments"):
            conn.execute(text(
                f'CREATE POLICY "{name}_tenant" ON public."{name}" '
                "USING (tenant_id=current_setting('app.tenant_id',true)) "
                "WITH CHECK (tenant_id=current_setting('app.tenant_id',true))"
            ))
    # Intentionally NO GRANT here. Old axs_core_app may be overprivileged
    # on the cloned DB but gets no inherited grants on these fresh tables.
    return len(meta.tables)


def apply_bootstrap(values: dict, *, explicitly_confirmed: bool) -> dict:
    if not explicitly_confirmed or values.get("AXS_CORPORATE_SCHEMA_BOOTSTRAP_CONFIRM") != CONFIRM:
        raise RuntimeError("Bootstrap: falta autorización explícita")
    configurations = []
    for key, database, _, _ in TARGETS:
        name = f"AXS_CORPORATE_BOOTSTRAP_{key}_URL"
        url = values.get(name, "")
        check_bootstrap_url(url, database)
        configurations.append((key, database, url))
    engines = []
    try:
        # Preflight ALL databases before mutating ANY of them.
        for key, dbname, url in configurations:
            engine = create_engine(url, pool_pre_ping=True)
            engines.append(engine)
            if engine.dialect.name != "postgresql":
                raise RuntimeError("Bootstrap: PostgreSQL obligatorio")
            with engine.connect() as conn:
                assert_empty_database(conn, dbname)
        result = {}
        for (key, database, _), engine in zip(configurations, engines):
            with engine.begin() as conn:
                # Recheck in same transaction to avoid silently overwriting
                # a database created after preflight.
                assert_empty_database(conn, database)
                result[key] = install_schema(conn, key)
        return result
    finally:
        for engine in engines:
            engine.dispose()


if __name__ == "__main__":
    arg = argparse.ArgumentParser(description="Crear solo esquemas AXS Corporativo en bases vacías")
    arg.add_argument("--apply", action="store_true", help="Requiere además variable de confirmación")
    opts = arg.parse_args()
    try:
        result = apply_bootstrap(os.environ, explicitly_confirmed=opts.apply)
        print("AXS corporate sandbox schemas initialized, FORCE RLS, no runtime grants:",
              ", ".join(f"{key}={value}" for key, value in result.items()))
    except Exception as exc:
        raise SystemExit(f"DENIED: {type(exc).__name__} (sin detalles de conexión)") from None
