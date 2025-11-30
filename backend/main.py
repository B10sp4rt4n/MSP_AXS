from fastapi import FastAPI
import logging
from .db.connection import Base, engine
from .routers import (
    visitas_router,
    qr_router,
    evidencias_router,
    preregistro_router,
)

logger = logging.getLogger("axs.startup")


app = FastAPI(title="AX-S MSP API")


# Intentar crear tablas si la conexión DB está operativa (útil en local).
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables checked/created successfully")
except Exception as exc:
    # Loggear el error y continuar el arranque; la app puede funcionar en modo degradado
    logger.warning("No se pudo crear/verificar tablas en la DB (se omite create_all)", exc_info=exc)


app.include_router(visitas_router.router)
app.include_router(qr_router.router)
app.include_router(evidencias_router.router)
app.include_router(preregistro_router.router)


@app.get("/")
def read_root():
    return {"ok": True, "service": "AX-S MSP API"}
