"""Real additive migration against a disposable PostgreSQL schema only."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


def test_progressive_identity_migration_repeatable_preserves_existing_users():
    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires disposable PostgreSQL")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    schema = "axs_identity_" + uuid4().hex
    try:
        with engine.begin() as conn:
            role = conn.execute(text("SELECT current_user")).scalar_one()
            conn.execute(text(f"CREATE SCHEMA {schema}"))
            conn.execute(text(f"CREATE TABLE {schema}.usuarios (usuario_id varchar PRIMARY KEY, nombre varchar)"))
            conn.execute(text(f"INSERT INTO {schema}.usuarios VALUES ('person', 'Existing user')"))
        sql = Path("migrations/20261018_progressive_identity.sql").read_text().replace("public.", schema + ".")
        sql = sql.replace("TO axs_core_app", 'TO "' + role.replace('"', '""') + '"')
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql(sql)
            conn.exec_driver_sql(sql)
        with engine.begin() as conn:
            assert conn.execute(text(f"SELECT usuario_id,nombre,celular,celular_verified_at,celular_consent_at FROM {schema}.usuarios")).one() == ("person", "Existing user", None, None, None)
            conn.execute(text(f"INSERT INTO {schema}.external_identities VALUES ('i','person','facebook','https://facebook.com/person',now(),'profile-reference-v1',NULL,NULL,NULL,now())"))
        amazon_sql = Path("migrations/20261018_amazon_identity.sql").read_text().replace("public.", schema + ".")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql(amazon_sql)
            conn.exec_driver_sql(amazon_sql)
        with engine.begin() as conn:
            assert conn.execute(text(f"SELECT reference FROM {schema}.external_identities WHERE identity_id='i'")).scalar_one() == "https://facebook.com/person"
            conn.execute(text(f"INSERT INTO {schema}.external_identities VALUES ('amazon','person','amazon','person@example.com',now(),'profile-reference-v1',NULL,NULL,NULL,now())"))
        with engine.connect() as conn:
            with pytest.raises(IntegrityError):
                conn.execute(text(f"INSERT INTO {schema}.external_identities VALUES ('duplicate','person','facebook','https://facebook.com/other',now(),'profile-reference-v1',NULL,NULL,NULL,now())"))
            conn.rollback()
            with pytest.raises(IntegrityError):
                conn.execute(text(f"UPDATE {schema}.external_identities SET revoked_at=now() WHERE identity_id='i'"))
            conn.rollback()
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE {schema}.external_identities SET revoked_at=now(),reference=NULL WHERE identity_id='i'"))
            assert conn.execute(text(f"SELECT count(*) FROM {schema}.usuarios")).scalar_one() == 1
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
