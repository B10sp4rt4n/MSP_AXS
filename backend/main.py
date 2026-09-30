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

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parents[1] / ".env")  # cargar antes de cualquier engine

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import asyncio
from contextlib import suppress

_log_level = logging.DEBUG if os.getenv("ENVIRONMENT") != "production" else logging.INFO
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reducir verbosidad de librerías de terceros
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

# ✅ AUP: Importar engines y bases separadas por dominio
from .db.core import Base_CORE, engine_core
from .db.event import Base_EVENT, engine_event
from .db.gov import Base_GOV, engine_gov

from .routers import (
    visitas_router,
    qr_router,
    evidencias_router,
    preregistro_router,
    auth_router,  # ← Router de autenticación AUP
    condominios_router,  # ← Router con gobierno integrado
    canario_router,  # ← 🐤 Router canario AUP
    msp_router,  # ← Router de MSPs
    meta,  # ← Router meta-operativo v1.0 (CONGELADO)
    webhooks_router,  # ← Clerk webhook
)

from .core.config import settings
from .core.aup_runtime_blocks import AUPSessionGuard  # ← Middleware BLOQUEO AUP-01

logger = logging.getLogger("axs.startup")

app = FastAPI(
    title="AX-S MSP API",
    description="Sistema de gestión de accesos con arquitectura AUP completa (SESSION + SCOPE + EVENT + GOV)",
    version="3.0.0-aup-gov"
)


@app.on_event("startup")
async def iniciar_auditoria():
    # Los tests controlan explícitamente el envío y no usan conexiones reales.
    if os.getenv("TESTING") == "1" or engine_core.dialect.name != "postgresql":
        return
    from backend.services.event_outbox import ejecutar_worker
    from backend.db.core.session import SessionLocal_CORE
    from backend.db.event.session import SessionLocal_EVENT
    app.state.audit_worker = asyncio.create_task(ejecutar_worker(SessionLocal_CORE, SessionLocal_EVENT))
    logger.info("Auditoría durable: worker iniciado")


@app.on_event("shutdown")
async def detener_auditoria():
    task = getattr(app.state, "audit_worker", None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

# ============================================================
#   🌍 CORS: Permitir requests desde cualquier origen
# ============================================================
# Necesario para GitHub Codespaces y otros entornos de desarrollo
# AUP-01 se agrega primero (será el middleware interno)
# CORS se agrega después (será el más externo, envuelve todo incluyendo errores AUP)
app.add_middleware(AUPSessionGuard)
logger.info("🔒 AUP-01 ACTIVADO: Middleware de SESSION activo")

_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://frontend-next-psi-ashen.vercel.app,https://frontend-next-salvador-ruiz-esparzas-projects.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"🌍 CORS ACTIVADO: {_allowed_origins}")

# ============================================================
#   Inicialización de Bases de Datos (Separadas)
# ============================================================

try:
    # ✅ Crear tablas en AUP_CORE
    Base_CORE.metadata.create_all(bind=engine_core)
    logger.info("✅ AUP_CORE: Tablas verificadas/creadas")
    
    # ✅ Crear tablas en AUP_EVENT
    Base_EVENT.metadata.create_all(bind=engine_event)
    logger.info("✅ AUP_EVENT: Tablas verificadas/creadas")
    
    # ✅ Crear tablas en AUP_GOV
    Base_GOV.metadata.create_all(bind=engine_gov)
    logger.info("✅ AUP_GOV: Tablas verificadas/creadas")
    
except Exception as exc:
    logger.warning("⚠ No se pudieron crear/verificar todas las tablas", exc_info=exc)


# ============================================================
#   Routers
# ============================================================

# Router de autenticación (público)

# 🐤 Router canario AUP (demostrador)
app.include_router(canario_router.router)
app.include_router(auth_router.router)

# Routers protegidos (requieren AUP_SESSION)
app.include_router(msp_router.router)
app.include_router(visitas_router.router)
app.include_router(qr_router.router)
app.include_router(evidencias_router.router)
app.include_router(preregistro_router.router)
app.include_router(condominios_router.router)

# ✅ Router Meta-Operativo v1.0 (CONGELADO)
# NO usa middleware de tenant (dominio separado)
app.include_router(meta.router)

# Clerk webhook (público — no requiere AUP_SESSION)
app.include_router(webhooks_router.router)


# ============================================================
#   Debug Endpoint
# ============================================================

if os.getenv("ENVIRONMENT") != "production":
    @app.get("/debug/db")
    def debug_db():
        """Solo disponible fuera de producción."""
        return {
            "db_url_from_env": os.getenv("DATABASE_URL", "(NO ENV FOUND)"),
            "env_file_loaded": "YES" if os.getenv("DATABASE_URL") else "NO"
        }


# ============================================================
#   Frontend Estático (Deployment)
# ============================================================

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info("✅ Frontend estático montado en /static")
    
    @app.get("/")
    async def serve_frontend():
        """Servir frontend HTML para piloto."""
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    @app.get("/admin.html")
    async def serve_admin():
        """Servir panel administrativo."""
        return FileResponse(os.path.join(static_dir, "admin.html"))
else:
    @app.get("/")
    def read_root():
        """Health check endpoint (público) - solo si no hay frontend."""
        return {
            "ok": True,
            "service": "AX-S MSP API",
            "version": "3.0.0-aup-gov",
            "auth_system": "AUP_SESSION (JWT)",
            "login_endpoint": "/auth/login",
            "gov_integrated": True,
            "architecture": "AUP (SESSION + SCOPE + EVENT + GOV)"
        }


# ============================================================
#   Health Check (para Railway/monitoring)
# ============================================================

@app.get("/health")
def health_check():
    """Endpoint de salud para deployment."""
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "aup_blocks_active": True,
        "version": "3.0.0-aup-gov"
    }
