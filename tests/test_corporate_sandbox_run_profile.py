"""A new run changes only fixed databases/roles; old certificates remain immutable."""
import pytest
from scripts.check_corporate_sandbox_config import check
from scripts.corporate_sandbox_targets import LEGACY, INTEGRATED, sandbox_targets, render_sandbox_sql
from scripts.prepare_integrated_sandbox_bundle import permission_scripts
from tests.test_corporate_sandbox_runtime import runtime_config


def integrated_config():
    values = runtime_config()
    values["AXS_CORPORATE_SANDBOX_RUN_PROFILE"] = "integrated-20261114"
    for key in ("DATABASE_CORE_URL", "DATABASE_URL", "DATABASE_GOV_URL", "DATABASE_EVENT_URL", "DATABASE_CORPORATE_PROVISIONING_URL"):
        values[key] = render_sandbox_sql(values[key], INTEGRATED)
    return values


def test_new_run_uses_only_named_fresh_destinations():
    check(integrated_config())
    assert set(LEGACY.databases.values()).isdisjoint(INTEGRATED.databases.values())
    assert set(LEGACY.roles.values()).isdisjoint(INTEGRATED.roles.values())


@pytest.mark.parametrize("key", ["DATABASE_CORE_URL", "DATABASE_URL", "DATABASE_GOV_URL", "DATABASE_EVENT_URL", "DATABASE_CORPORATE_PROVISIONING_URL"])
def test_new_run_rejects_any_legacy_connection(key):
    values = integrated_config()
    values[key] = runtime_config()[key]
    with pytest.raises(RuntimeError):
        check(values)


@pytest.mark.parametrize("profile", ["", "other", "../../production", "20261115"])
def test_unknown_profiles_are_not_general_destination_overrides(profile):
    values = integrated_config()
    values["AXS_CORPORATE_SANDBOX_RUN_PROFILE"] = profile
    with pytest.raises(RuntimeError):
        check(values)


def test_new_profile_requires_runtime_and_legacy_default_is_preserved():
    assert sandbox_targets({}) == LEGACY
    values = integrated_config()
    values["AXS_CORPORATE_SANDBOX_PHASE"] = "closed"
    with pytest.raises(RuntimeError):
        check(values)


@pytest.mark.parametrize("domain", ["CORE", "GOV", "EVENT"])
def test_rendered_permissions_keep_certificate_expiry_and_no_login(domain):
    sql = "\n".join(permission_scripts(domain))
    assert "interval '24 hours'" in sql
    assert "NOLOGIN NOINHERIT" in sql
    assert INTEGRATED.databases[domain] in sql
    assert LEGACY.databases[domain] not in sql.replace(INTEGRATED.databases[domain], "")
    assert "20261114_20261114" not in sql
