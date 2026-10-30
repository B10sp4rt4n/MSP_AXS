"""Pure unit tests for schema bootstrap safeguard. Never open a Neon connection."""
import pytest
from scripts.bootstrap_corporate_sandbox_schemas import (
    CONFIRM, TARGETS, apply_bootstrap, check_bootstrap_url, get_metadata,
)


def bootstrap_values():
    host = "ep-bitter-snow-b5sgxc4h.c-7.us-east-2.aws.neon.tech"
    values = {"AXS_CORPORATE_SCHEMA_BOOTSTRAP_CONFIRM": CONFIRM}
    for key, database, _, _ in TARGETS:
        values[f"AXS_CORPORATE_BOOTSTRAP_{key}_URL"] = (
            f"postgresql+psycopg://neondb_owner:synthetic-only@{host}/{database}?sslmode=require"
        )
    return values


def test_rejects_without_double_confirmation():
    with pytest.raises(RuntimeError):
        apply_bootstrap(bootstrap_values(), explicitly_confirmed=False)
    values = bootstrap_values()
    del values["AXS_CORPORATE_SCHEMA_BOOTSTRAP_CONFIRM"]
    with pytest.raises(RuntimeError):
        apply_bootstrap(values, explicitly_confirmed=True)


def test_validation_is_offline(monkeypatch):
    values = bootstrap_values()
    from scripts import bootstrap_corporate_sandbox_schemas as runner
    monkeypatch.setattr(runner, "create_engine", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Never connect during validation")))
    for _, database, _, _ in TARGETS:
        url = next(values[f"AXS_CORPORATE_BOOTSTRAP_{k}_URL"] for k, n, _, _ in TARGETS if n == database)
        check_bootstrap_url(url, database)


@pytest.mark.parametrize("replacement", [
    "ep-rough-voice-b5vx4odv", "ep-withered-resonance-b59tusv3",
    "localhost", "attacker.example",
])
def test_reject_wrong_hosts_without_printing_secret(replacement):
    vals = bootstrap_values()
    url = vals["AXS_CORPORATE_BOOTSTRAP_CORE_URL"].replace(
        "ep-bitter-snow-b5sgxc4h.c-7.us-east-2.aws.neon.tech", replacement)
    with pytest.raises(RuntimeError) as err:
        check_bootstrap_url(url, "axs_corp_core_sbx")
    assert "synthetic-only" not in str(err.value)


@pytest.mark.parametrize("changed", [
    lambda s: s.replace("neondb_owner", "axs_core_app"),
    lambda s: s.replace("axs_corp_core_sbx", "neondb"),
    lambda s: s.replace("sslmode=require", "sslmode=disable"),
    lambda s: s.replace("postgresql+psycopg", "sqlite"),
    lambda s: s.replace("synthetic-only", ""),
])
def test_reject_wrong_owner_db_tls_scheme_password(changed):
    url = changed(bootstrap_values()["AXS_CORPORATE_BOOTSTRAP_CORE_URL"])
    with pytest.raises(RuntimeError):
        check_bootstrap_url(url, "axs_corp_core_sbx")


@pytest.mark.parametrize("which,min_expected", [("CORE", 20), ("GOV", 4), ("EVENT", 1)])
def test_schema_comes_from_actual_orm_models(which, min_expected):
    assert len(get_metadata(which).tables) >= min_expected
