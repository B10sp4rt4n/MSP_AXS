from . import msp_router
from . import condominios_router
from . import visitas_router
from . import qr_router
from . import evidencias_router
from . import preregistro_router
from . import auth_router
from . import canario_router
from . import meta_router  # ← Dominio Meta-Operativo v1.0 (CONGELADO)

__all__ = [
    "msp_router",
    "condominios_router",
    "visitas_router",
    "qr_router",
    "evidencias_router",
    "preregistro_router",
    "auth_router",
    "canario_router",
    "meta_router",
]
