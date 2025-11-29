from fastapi import FastAPI

from .routers import (
    msp_router,
    condominios_router,
    visitas_router,
    qr_router,
    evidencias_router,
    preregistro_router,
)
from .db.connection import Base, engine

app = FastAPI(title="MSP AXS - Backend")


@app.on_event("startup")
def on_startup():
    # crear tablas si es necesario
    Base.metadata.create_all(bind=engine)


app.include_router(msp_router.router, prefix="/msp")
app.include_router(condominios_router.router, prefix="/condominios")
app.include_router(visitas_router.router, prefix="/visitas")
app.include_router(qr_router.router, prefix="/qr")
app.include_router(evidencias_router.router, prefix="/evidencias")
app.include_router(preregistro_router.router, prefix="/preregistro")


@app.get("/")
def read_root():
    return {"ok": True, "service": "MSP AXS Backend"}
