"""
AUP_CORE — Dominio de Identidad y Alcance

Exporta modelos, engine y session para AUP_CORE.
"""

from .engine import engine_core, Base_CORE
from .session import SessionLocal_CORE, get_core_db
from .models import (
    # Enums
    ScopeStatus,
    AccessLevel,
    # Modelos
    MSP,
    Condominio,
    Usuario,
    UserTenantScope,
    Caseta,
    Visita,
    Evidencia,
    QRCode,
)

__all__ = [
    # Engine y Session
    "engine_core",
    "Base_CORE",
    "SessionLocal_CORE",
    "get_core_db",
    # Enums
    "ScopeStatus",
    "AccessLevel",
    # Modelos
    "MSP",
    "Condominio",
    "Usuario",
    "UserTenantScope",
    "Caseta",
    "Visita",
    "Evidencia",
    "QRCode",
]
