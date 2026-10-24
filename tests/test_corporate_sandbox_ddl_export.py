"""Schema-only exporter: no database connections, no runtime grants, no PII."""
import pytest
from scripts.export_corporate_sandbox_ddl import (
    export_domain, get_metadata, DOMAINS, CORPORATE,
)


@pytest.mark.parametrize("domain", DOMAINS)
def test_export_matches_actual_models(domain):
    ddl = export_domain(domain)
    metadata = get_metadata(domain)
    names = tuple(metadata.tables.keys())
    assert len(ddl) >= len(names) * 3
    for name in names:
        assert any("CREATE TABLE" in sql and name in sql for sql in ddl)
        assert f'ALTER TABLE public."{name}" ENABLE ROW LEVEL SECURITY' in ddl
        assert f'ALTER TABLE public."{name}" FORCE ROW LEVEL SECURITY' in ddl
    assert all("DROP " not in sql.upper() and "GRANT " not in sql.upper() for sql in ddl)


def test_export_corporate_rows_are_scoped_by_rls():
    ddl = export_domain("CORE")
    for name in CORPORATE:
        target = [sql for sql in ddl if sql.startswith(f'CREATE POLICY "{name}_tenant"')]
        assert len(target) == 1
        assert "current_setting('app.tenant_id',true)" in target[0]
    assert len([sql for sql in ddl if sql.startswith("CREATE POLICY")]) == 5


def test_export_rejects_missing_domain():
    with pytest.raises(ValueError):
        export_domain("PRODUCTION")
