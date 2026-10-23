"""Configuration-only tests: no DB, Clerk, Railway or network access."""
import pytest
from scripts.check_corporate_sandbox_config import check, ENDPOINT


def safe_config():
    base = {
        "APP_ENV": "development", "ENV": "development",
        "ENVIRONMENT": "production",
        "AXS_CORPORATE_SANDBOX_ONLY": "true",
        "NEON_DEV_ENDPOINT": ENDPOINT,
        "AXS_CORPORATE_API_ENABLED": "false",
        "AXS_CORPORATE_PROVISIONING_ENABLED": "false",
        "ECHO_SQL": "false",
        "USE_CLOUDINARY": "false",
        "AXS_ID_PHOTOS_ENABLED": "false",
        "AXS_ARCO_CASES_ENABLED": "false",
        "CLERK_SECRET_KEY": "sk_test_" + "k" * 40,
        "CLERK_PUBLISHABLE_KEY": "pk_test_" + "p" * 40,
        "SECRET_KEY": "sandbox-" + "s" * 48,
    }
    host = f"{ENDPOINT}.c-7.us-east-2.aws.neon.tech"
    urls = {
        "DATABASE_CORE_URL": ("neondb", "axs_core_app"),
        "DATABASE_URL": ("neondb", "axs_core_app"),
        "DATABASE_GOV_URL": ("aup_gov", "axs_corp_sandbox_gov"),
        "DATABASE_EVENT_URL": ("aup_event", "axs_corp_sandbox_event"),
    }
    for k, (db, user) in urls.items():
        base[k] = f"postgresql://{user}:synthetic-password@{host}/{db}?sslmode=require"
    return base


def test_sandbox_accepts_exact_isolated_endpoints_without_connecting():
    check(safe_config())


@pytest.mark.parametrize("key,bad_value", [
    ("APP_ENV", "production"),
    ("ENVIRONMENT", "development"),
    ("AXS_CORPORATE_SANDBOX_ONLY", "false"),
    ("NEON_DEV_ENDPOINT", "ep-rough-voice-b5vx4odv"),
    ("AXS_CORPORATE_API_ENABLED", "true"),
    ("AXS_CORPORATE_PROVISIONING_ENABLED", "true"),
    ("ECHO_SQL", "true"),
    ("USE_CLOUDINARY", "true"),
    ("AXS_ID_PHOTOS_ENABLED", "true"),
    ("AXS_ARCO_CASES_ENABLED", "true"),
    ("AXS_ALEXA_LINKING_ENABLED", "true"),
    ("DATABASE_CORPORATE_PROVISIONING_URL", "postgresql://fake:secret@host/neondb"),
    ("CLERK_SECRET_KEY", "sk_live_" + "k"*30),
    ("CLERK_PUBLISHABLE_KEY", "pk_live_" + "p"*30),
    ("SECRET_KEY", "short"),
])
def test_sandbox_rejects_unsafe_flags_and_credentials(key, bad_value):
    vals = safe_config()
    vals[key] = bad_value
    with pytest.raises(RuntimeError) as exc:
        check(vals)
    assert "synthetic-password" not in str(exc.value)
    assert "sk_live_" not in str(exc.value)


@pytest.mark.parametrize("key", [
    "DATABASE_CORE_URL", "DATABASE_URL", "DATABASE_GOV_URL", "DATABASE_EVENT_URL",
])
def test_sandbox_rejects_missing_url_without_credentials_in_error(key):
    vals = safe_config()
    vals.pop(key)
    with pytest.raises(RuntimeError) as exc:
        check(vals)
    assert "synthetic-password" not in str(exc.value)


@pytest.mark.parametrize("key", [
    "DATABASE_CORE_URL", "DATABASE_URL", "DATABASE_GOV_URL", "DATABASE_EVENT_URL",
])
def test_sandbox_rejects_any_cross_branch_connection(key):
    vals = safe_config()
    vals[key] = vals[key].replace(ENDPOINT, "ep-withered-resonance-b59tusv3")
    with pytest.raises(RuntimeError) as exc:
        check(vals)
    assert "synthetic-password" not in str(exc.value)


@pytest.mark.parametrize("key", [
    "DATABASE_CORE_URL", "DATABASE_GOV_URL", "DATABASE_EVENT_URL",
])
def test_sandbox_rejects_privileged_owner_connection(key):
    vals = safe_config()
    expected = {
        "DATABASE_CORE_URL": "axs_core_app",
        "DATABASE_GOV_URL": "axs_corp_sandbox_gov",
        "DATABASE_EVENT_URL": "axs_corp_sandbox_event",
    }
    vals[key] = vals[key].replace(expected[key], "neondb_owner")
    with pytest.raises(RuntimeError):
        check(vals)


@pytest.mark.parametrize("mutation", [
    lambda s: s.replace("?sslmode=require", "?sslmode=disable"),
    lambda s: s.replace("@", "@attacker.example/redirect@"),
    lambda s: s.replace("/aup_gov?", "/neondb?"),
    lambda s: s.replace("postgresql://", "sqlite://"),
])
def test_sandbox_rejects_unsafe_url_variants(mutation):
    vals = safe_config()
    vals["DATABASE_GOV_URL"] = mutation(vals["DATABASE_GOV_URL"])
    with pytest.raises(RuntimeError):
        check(vals)


def test_sandbox_rejects_core_alias_mismatch_even_on_same_branch():
    vals = safe_config()
    vals["DATABASE_URL"] = vals["DATABASE_URL"].replace("synthetic-password", "different-password")
    with pytest.raises(RuntimeError):
        check(vals)


def test_sandbox_accepts_pooler_of_exact_branch():
    vals = safe_config()
    for key in ("DATABASE_CORE_URL", "DATABASE_URL", "DATABASE_GOV_URL", "DATABASE_EVENT_URL"):
        vals[key] = vals[key].replace(ENDPOINT + ".", ENDPOINT + "-pooler.")
    check(vals)
