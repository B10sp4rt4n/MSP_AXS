import pytest
from scripts.check_development_config import check


def config():
    endpoint = "ep-dev-example"
    values = {"APP_ENV": "development", "ENVIRONMENT": "production", "NEON_DEV_ENDPOINT": endpoint}
    for name, database in [("DATABASE_CORE_URL", "neondb"), ("DATABASE_URL", "neondb"),
                           ("DATABASE_EVENT_URL", "aup_event"), ("DATABASE_GOV_URL", "aup_gov")]:
        values[name] = f"postgresql://user:secret@{endpoint}-pooler.c-7.us-east-2.aws.neon.tech/{database}?sslmode=require"
    return values


def test_development_accepts_isolated_domain_connections():
    check(config())


@pytest.mark.parametrize("name", ["DATABASE_CORE_URL", "DATABASE_URL", "DATABASE_EVENT_URL", "DATABASE_GOV_URL"])
def test_development_rejects_one_production_connection(name):
    values = config()
    values[name] = values[name].replace("ep-dev-example", "ep-rough-voice-b5vx4odv")
    with pytest.raises(RuntimeError) as error:
        check(values)
    assert "secret" not in str(error.value)


def test_development_rejects_missing_domain_instead_of_sqlite_fallback():
    values = config()
    del values["DATABASE_EVENT_URL"]
    with pytest.raises(RuntimeError):
        check(values)


def test_development_rejects_wrong_database():
    values = config()
    values["DATABASE_EVENT_URL"] = values["DATABASE_CORE_URL"]
    with pytest.raises(RuntimeError):
        check(values)


def test_development_keeps_debug_endpoint_disabled():
    values = config()
    values["ENVIRONMENT"] = "development"
    with pytest.raises(RuntimeError):
        check(values)
