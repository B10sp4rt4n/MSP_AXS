"""Export exact SQLAlchemy PostgreSQL DDL for AXS Corporate's EMPTY sandbox DBs.

This does not open a DB connection; output is schema-only and contains no
identities, tokens or credentials. The generated statements are meant for a
separate, explicitly reviewed operation on the named sandbox branch only.
"""
import hashlib
import json
import os
import sys

from sqlalchemy import create_mock_engine
from sqlalchemy.dialects import postgresql


DOMAINS = ("CORE", "GOV", "EVENT")
CORPORATE = (
    "corporate_organizations",
    "corporate_sites",
    "corporate_destinations",
    "corporate_memberships",
    "corporate_site_assignments",
)


def get_metadata(domain: str):
    if domain == "CORE":
        from backend.db.core.engine import Base_CORE
        from backend.db.core import models  # noqa: F401
        return Base_CORE.metadata
    if domain == "GOV":
        from backend.db.gov.engine import Base_GOV
        from backend.db.gov import models  # noqa: F401
        return Base_GOV.metadata
    if domain == "EVENT":
        from backend.db.event.engine import Base_EVENT
        from backend.db.event import models  # noqa: F401
        return Base_EVENT.metadata
    raise ValueError("Unknown domain")


def export_domain(domain: str) -> list[str]:
    metadata = get_metadata(domain)
    statements = []

    def capture(statement, *args, **kwargs):
        sql = str(statement.compile(dialect=postgresql.dialect())).strip()
        if not sql.upper().startswith("CREATE "):
            raise RuntimeError("Unexpected SQLAlchemy DDL")
        statements.append(sql)

    engine = create_mock_engine("postgresql+psycopg://", capture)
    metadata.create_all(engine, checkfirst=False)
    for name in sorted(metadata.tables):
        if not name.replace("_", "").isalnum():
            raise RuntimeError("Unexpected table identifier")
        statements += [
            f'ALTER TABLE public."{name}" ENABLE ROW LEVEL SECURITY',
            f'ALTER TABLE public."{name}" FORCE ROW LEVEL SECURITY',
        ]
    if domain == "CORE":
        for name in CORPORATE:
            if name not in metadata.tables:
                raise RuntimeError("Missing corporate model")
            statements.append(
                f'CREATE POLICY "{name}_tenant" ON public."{name}" '
                "USING (tenant_id=current_setting('app.tenant_id',true)) "
                "WITH CHECK (tenant_id=current_setting('app.tenant_id',true))"
            )
    if not statements or any("DROP " in sql.upper() or "GRANT " in sql.upper()
                              or "TRUNCATE " in sql.upper() for sql in statements):
        raise RuntimeError("Unsafe schema export")
    return statements


def emit():
    # Required flag prevents accidental schema printing in ordinary app tests.
    if os.getenv("AXS_EXPORT_SANDBOX_DDL") != "schema-only":
        raise RuntimeError("Schema-only export flag missing")
    for domain in DOMAINS:
        statements = export_domain(domain)
        serialized = json.dumps(statements, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        print(f"AXS_DDL_META::{domain}::{len(statements)}::{digest}", flush=True)
        for i, sql in enumerate(statements):
            print(f"AXS_DDL::{domain}::{i}::{json.dumps(sql, ensure_ascii=True)}", flush=True)


if __name__ == "__main__":
    try:
        emit()
    except Exception as exc:
        print(f"Schema export denied: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
