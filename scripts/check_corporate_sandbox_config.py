"""Predeploy fail-closed for the dedicated AXS corporate sandbox.

This validates ONLY endpoint identity and security configuration; it does not
make network calls, read rows, print tokens or certify that credentials work.
The sandbox must never point to the production branch or Railway residential.
"""
import os
import base64
import re
from uuid import UUID
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
    phase = values.get("AXS_CORPORATE_SANDBOX_PHASE", "closed")
    if phase not in {"closed", "runtime"}:
        raise RuntimeError("Sandbox corporativo: fase desconocida")
    runtime = phase == "runtime"
    expected = {
        "APP_ENV": "development",
        "ENV": "development",
        "ENVIRONMENT": "production",  # Disable legacy /debug/db endpoint
        "AXS_CORPORATE_SANDBOX_ONLY": "true",
        "NEON_DEV_ENDPOINT": ENDPOINT,
        "AXS_CORPORATE_API_ENABLED": "true" if runtime else "false",
        "AXS_CORPORATE_PROVISIONING_ENABLED": "true" if runtime else "false",
        "ECHO_SQL": "false",
        "USE_CLOUDINARY": "false",
        "AXS_ID_PHOTOS_ENABLED": "false",
        "AXS_ARCO_CASES_ENABLED": "true" if runtime else "false",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise RuntimeError(f"Sandbox corporativo: configuración incorrecta ({key})")
    if any(values.get(key, "false").lower() != "false" for key in (
        "AXS_ALEXA_LINKING_ENABLED", "AXS_ID_RETENTION_SCHEMA_ENABLED", "AXS_ID_RETENTION_PILOT_ENABLED",
    )):
        raise RuntimeError("Sandbox corporativo: Alexa no está autorizada")
    if not runtime and values.get("DATABASE_CORPORATE_PROVISIONING_URL", "").strip():
        raise RuntimeError("Sandbox corporativo: credencial de aprovisionamiento no autorizada")
    for key, prefix in (("CLERK_SECRET_KEY", "sk_test_"), ("CLERK_PUBLISHABLE_KEY", "pk_test_")):
        if not values.get(key, "").startswith(prefix):
            raise RuntimeError(f"Sandbox corporativo: credencial Clerk de prueba ausente ({key})")
    if len(values.get("SECRET_KEY", "")) < 32:
        raise RuntimeError("Sandbox corporativo: secreto de sesión independiente requerido")
    destinations = dict(DATABASES)
    if runtime:
        destinations.update({
            "DATABASE_CORE_URL": ("axs_corp_core_sbx", "axs_corp_sandbox_core"),
            "DATABASE_URL": ("axs_corp_core_sbx", "axs_corp_sandbox_core"),
            "DATABASE_CORPORATE_PROVISIONING_URL": ("axs_corp_core_sbx", "axs_corporate_provisioner"),
        })
        try:
            UUID(values.get("AXS_CORPORATE_SANDBOX_RUN_ID", ""))
            pk = values["CLERK_PUBLISHABLE_KEY"].split("_", 2)[2]
            domain = base64.b64decode(pk + "=" * (-len(pk) % 4), validate=True).decode().removesuffix("$")
            if not re.fullmatch(r"[a-z0-9-]+[.]clerk[.]accounts[.]dev", domain):
                raise ValueError()
            if values.get("CLERK_JWT_PUBLIC_KEY", "").strip():
                raise ValueError()
            if values.get("CLERK_JWT_ISSUER") != "https://" + domain:
                raise ValueError()
            if values.get("CLERK_JWKS_URL", "https://" + domain + "/.well-known/jwks.json") != "https://" + domain + "/.well-known/jwks.json":
                raise ValueError()
            origins = values.get("ALLOWED_ORIGINS", "").split(",")
            for origin in origins:
                parsed_origin = urlsplit(origin)
                if (parsed_origin.scheme != "https" or not parsed_origin.hostname
                        or parsed_origin.path or parsed_origin.query or parsed_origin.fragment
                        or parsed_origin.username or parsed_origin.password or parsed_origin.port):
                    raise ValueError()
            if values.get("TESTING", "") not in ("", "0"):
                raise ValueError()
            if any(key.startswith("AXS_CORPORATE_BOOTSTRAP_") and value for key, value in values.items()):
                raise ValueError()
        except Exception as exc:
            raise RuntimeError("Sandbox corporativo: identidad de ensayo o configuración runtime inválida") from exc
    for key, (db, user) in destinations.items():
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
