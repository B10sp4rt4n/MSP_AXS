from .msp_router import router as msp_router
from .condominios_router import router as condominios_router
from .visitas_router import router as visitas_router
from .qr_router import router as qr_router
from .evidencias_router import router as evidencias_router
from .preregistro_router import router as preregistro_router

__all__ = [
    "msp_router",
    "condominios_router",
    "visitas_router",
    "qr_router",
    "evidencias_router",
    "preregistro_router",
]
