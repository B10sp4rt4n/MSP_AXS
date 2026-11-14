"""Export schema/ACL SQL for a fresh, fixed sandbox run; never connect or apply."""
import json
from pathlib import Path
from scripts.corporate_sandbox_targets import INTEGRATED, render_sandbox_sql
from scripts.export_corporate_sandbox_ddl import export_domain


def permission_scripts(domain, targets=INTEGRATED):
    files = []
    if domain == "CORE":
        files += ["20261023_corporate_superadmin_c2.sql", "20261023_corporate_reconciliation_c4.sql"]
    files.append(f"20261024_corporate_sandbox_{domain.lower()}_permissions.sql")
    root = Path(__file__).resolve().parents[1] / "migrations"
    return [render_sandbox_sql((root / name).read_text(), targets) for name in files]


def bundle():
    return {domain: {"database": db, "schema": export_domain(domain),
                     "permissions": permission_scripts(domain)}
            for domain, db in INTEGRATED.databases.items()}


if __name__ == "__main__":
    print(json.dumps(bundle(), indent=2))
