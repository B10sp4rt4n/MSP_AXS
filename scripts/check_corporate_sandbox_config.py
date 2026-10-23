"""Predeploy fail-closed for the dedicated AXS corporate sandbox.

This validates ONLY endpoint identity and security configuration; it does not
make network calls, read rows, print tokens or certify that credentials work.
The sandbox must never point to the production branch or Railway residential.
"""
import os
from urllib.parse import parse_qs, urlsplit

ENDPOINT = "ep-bitter-snow-b5sgxc4h"
HOSTS = {
    f"{ENDPOINT}.c-7.us-east-2.aws.neon.tech",
    f"{ENDPOINT}-pooler.c-7.us-east-2.aws.neon.tech",
}
DATABASES = {
    "DATABASE_CORE_URL": ("axs_corp_core_sbx", "axs_core_app"),
    "DATABASE_URL": ("axs_corp_core_sbx", "axs_core_app"),
    "DATABASE_GOV_URL": ("axs_corp_gov_sbx", "axs_corp_sandbox_gov"),
    "DATABASE_EVENT_URL": ("axs_corp_event_sbx", "axs_corp_sandbox_event"),
}
SCHEMES = {"postgresql", "postgres", "postgresql+psycopg", "postgresql+psycopg2"}


def check(values: dict) -> None:
    """Raise a sanitized error on any invalid or incomplete configuration."""
    expected = {
        "APP_ENV": "development",
        "ENV": "development",
        "ENVIRONMENT": "production",  # Disable legacy /debug/db endpoint
        "AXS_CORPORATE_SANDBOX_ONLY": "true",
        "NEON_DEV_ENDPOINT": ENDPOINT,
        "AXS_CORPORATE_API_ENABLED": "false",
        "AXS_CORPORATE_PROVISIONING_ENABLED": "false",
        "ECHO_SQL": "false",
        "USE_CLOUDINARY": "false",
        "AXS_ID_PHOTOS_ENABLED": "false",
        "AXS_ARCO_CASES_ENABLED": "false",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise RuntimeError(f"Sandbox corporativo: configuración incorrecta ({key})")
    if values.get("AXS_ALEXA_LINKING_ENABLED", "false").lower() == "true":
        raise RuntimeError("Sandbox corporativo: Alexa no está autorizada")
    if values.get("DATABASE_CORPORATE_PROVISIONING_URL", "").strip():
        raise RuntimeError("Sandbox corporativo: credencial de aprovisionamiento no autorizada")
    for key, prefix in (("CLERK_SECRET_KEY", "sk_test_"), ("CLERK_PUBLISHABLE_KEY", "pk_test_")):
        if not values.get(key, "").startswith(prefix):
            raise RuntimeError(f"Sandbox corporativo: credencial Clerk de prueba ausente ({key})")
    if len(values.get("SECRET_KEY", "")) < 32:
        raise RuntimeError("Sandbox corporativo: secreto de sesión independiente requerido")
    for key, (db, user) in DATABASES.items():
        try:
            parsed = urlsplit(values.get(key, ""))
            query = parse_qs(parsed.query)
            secure_tls = query.get("sslmode", [None])[-1] in ("require", "verify-ca", "verify-full")
            if (
                parsed.scheme not in SCHEMES
                or parsed.hostname not in HOSTS
                or parsed.path != "/" + db
                or parsed.username != user
                or not parsed.password
                or parsed.fragment
                or parsed.port not in (None, 5432)
                or not secure_tls
            ):
                raise ValueError()
        except (ValueError, TypeError) as exc:
            raise RuntimeError(f"Sandbox corporativo: destino de base inválido ({key})") from exc
    if values["DATABASE_URL"] != values["DATABASE_CORE_URL"]:
        raise RuntimeError("Sandbox corporativo: DATABASE_URL debe coincidir con CORE")


if __name__ == "__main__":
    check(os.environ)
    print("AXS corporate sandbox configuration verified (no connections opened)")
