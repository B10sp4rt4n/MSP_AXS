import os
from pathlib import Path


class Settings:
    # No hardcodear una URL de producción. Preferir env var.
    # Si no existe `DATABASE_URL`, usar SQLite local para desarrollo.
    PROJECT_ROOT = Path(__file__).parents[2]
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{PROJECT_ROOT / 'axs_dev.db'}",
    )

    # Directorio de uploads (puede configurarse vía env)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "uploads"))

    # Engine parameters (configurables por entorno)
    ENGINE_POOL_SIZE: int = int(os.getenv("ENGINE_POOL_SIZE", "5"))
    ENGINE_MAX_OVERFLOW: int = int(os.getenv("ENGINE_MAX_OVERFLOW", "10"))
    ENGINE_POOL_TIMEOUT: int = int(os.getenv("ENGINE_POOL_TIMEOUT", "30"))
    ECHO_SQL: bool = os.getenv("ECHO_SQL", "false").lower() in ("1", "true", "yes")

    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
