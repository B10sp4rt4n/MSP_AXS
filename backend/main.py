"""
═══════════════════════════════════════════════════════════════════════════════
MSP_AXS Backend - MIGRADO A AUP_SESSION
═══════════════════════════════════════════════════════════════════════════════

SISTEMA DE AUTENTICACIÓN:
  - AUP_IDENTITY: Usuario en base de datos
  - AUP_CREDENTIAL: Password hash (bcrypt)
  - AUP_SESSION: JWT con identity_id + role
  
ENDPOINTS PÚBLICOS:
  - POST /auth/login: crear AUP_SESSION
  - GET /: health check
  
ENDPOINTS PROTEGIDOS:
  - Todos los demás requieren: Authorization: Bearer <token>

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import FastAPI
import logging
import os

from .db.connection import Base, engine
from .routers import (
    visitas_router,
    qr_router,
    evidencias_router,
    preregistro_router,
    auth_router,  # ← Router de autenticación AUP
    condominios_router,  # ← Router con gobierno integrado
)

from .core.config import settings

logger = logging.getLogger("axs.startup")

app = FastAPI(
    title="AX-S MSP API",
    description="Sistema de gestión de accesos con arquitectura AUP completa (SESSION + SCOPE + EVENT + GOV)",
    version="3.0.0-aup-gov"
)

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

# Router de autenticación (público)
app.include_router(auth_router.router)

# Routers protegidos (requieren AUP_SESSION)
app.include_router(visitas_router.router)
app.include_router(qr_router.router)
app.include_router(evidencias_router.router)
app.include_router(preregistro_router.router)
app.include_router(condominios_router.router)


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
    """Health check endpoint (público)."""
    return {
        "ok": True,
        "service": "AX-S MSP API",
        "version": "3.0.0-aup-gov",
        "auth_system": "AUP_SESSION (JWT)",
        "login_endpoint": "/auth/login",
        "gov_integrated": True,
        "architecture": "AUP (SESSION + SCOPE + EVENT + GOV)"
    }
