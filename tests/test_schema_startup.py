"""Runtime startup must not acquire DDL rights to bootstrap PostgreSQL."""
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy import Column, Integer, create_engine, inspect
from sqlalchemy.orm import declarative_base

from backend.db.startup import bootstrap_local_schema


def test_postgres_runtime_never_connects_or_creates_optional_table():
    base = SimpleNamespace(metadata=Mock())
    engine = Mock(dialect=SimpleNamespace(name="postgresql"))
    assert bootstrap_local_schema(base, engine) is False
    base.metadata.create_all.assert_not_called()
    engine.connect.assert_not_called()


def test_local_sqlite_still_bootstraps_schema():
    base = declarative_base()

    class LocalRow(base):
        __tablename__ = "local_row"
        id = Column(Integer, primary_key=True)

    engine = create_engine("sqlite://")
    try:
        assert bootstrap_local_schema(base, engine) is True
        assert inspect(engine).has_table("local_row")
    finally:
        engine.dispose()
