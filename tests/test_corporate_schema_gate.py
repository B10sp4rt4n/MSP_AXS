"""Safety properties of the stand-alone read-only schema gate."""
from types import SimpleNamespace

import pytest

from scripts.check_corporate_schema import SchemaGateError, main, run_gate


def test_gate_refuses_non_postgres_without_opening_a_connection():
    engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    with pytest.raises(SchemaGateError, match="PostgreSQL obligatorio"):
        run_gate(engine)


def test_connection_failures_do_not_disclose_credentials():
    class BrokenEngine:
        dialect = SimpleNamespace(name="postgresql")

        def connect(self):
            raise RuntimeError("postgresql://owner:DO_NOT_DISCLOSE@private/db")

    with pytest.raises(SchemaGateError) as error:
        run_gate(BrokenEngine())
    assert "DO_NOT_DISCLOSE" not in str(error.value)
    assert "private" not in str(error.value)


def test_cli_requires_explicit_core_destination(monkeypatch):
    monkeypatch.delenv("DATABASE_CORE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://unrelated/other")
    with pytest.raises(SchemaGateError, match="falta DATABASE_CORE_URL"):
        main()
