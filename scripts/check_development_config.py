"""Validate development endpoints without opening connections or printing secrets."""
import os
from urllib.parse import urlsplit


def check(values):
    if values.get("APP_ENV") != "development":
        raise RuntimeError("APP_ENV debe ser development")
    endpoint = values.get("NEON_DEV_ENDPOINT", "")
    if not endpoint.startswith("ep-") or endpoint == "ep-rough-voice-b5vx4odv":
        raise RuntimeError("Endpoint de desarrollo ausente o de producción")
    expected = {
        "DATABASE_CORE_URL": "neondb",
        "DATABASE_URL": "neondb",
        "DATABASE_EVENT_URL": "aup_event",
        "DATABASE_GOV_URL": "aup_gov",
    }
    for name, database in expected.items():
        parsed = urlsplit(values.get(name, ""))
        host = (parsed.hostname or "").split(".")[0].removesuffix("-pooler")
        if (parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}
                or host != endpoint or parsed.path != "/" + database):
            raise RuntimeError(f"Conexión de desarrollo inválida: {name}")
    if values.get("ENVIRONMENT") != "production":
        raise RuntimeError("Mantener ENVIRONMENT=production para desactivar debug/db")


if __name__ == "__main__":
    check(os.environ)
    print("Development endpoints verified; no production connection")
