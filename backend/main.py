from fastapi import FastAPI
import logging
import os

from .db.connection import Base, engine
from .routers import (
    visitas_router,
    qr_router,
    evidencias_router,
    preregistro_router,
)

from .core.config import settings

logger = logging.getLogger("axs.startup")

app = FastAPI(title="AX-S MSP API")

# ============================================================
#   Inicialización de Base de Datos
# ============================================================

try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables checked/created successfully")
except Exception as exc:
    logger.warning("No se pudo crear/verificar tablas en la DB (se omite create_all)", exc_info=exc)


# ============================================================
#   Routers
# ============================================================

app.include_router(visitas_router.router)
app.include_router(qr_router.router)
app.include_router(evidencias_router.router)
app.include_router(preregistro_router.router)


# ============================================================
#   Debug Endpoint
# ============================================================

@app.get("/debug/db")
def debug_db():
    """Revisar si el backend sí está leyendo .env y qué DB está usando."""
    return {
        "db_url_from_env": os.getenv("DATABASE_URL", "(NO ENV FOUND)"),
        "db_url_from_settings": getattr(settings, "DATABASE_URL", "(NO SETTINGS LOADED)"),
        "env_file_loaded": "YES" if os.getenv("DATABASE_URL") else "NO"
    }


# ============================================================
#   Root
# ============================================================

@app.get("/")
def read_root():
    return {"ok": True, "service": "AX-S MSP API"}
