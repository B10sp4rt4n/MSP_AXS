"""
AUP_GOV — Dominio de Poder Explícito

Exporta modelos, engine y session para AUP_GOV.
"""

from .engine import engine_gov, Base_GOV
from .session import SessionLocal_GOV, get_gov_db
from .models import (
    # Enums
    AuthorityType,
    PolicyScope,
    GovStatus,
    # Modelos
    Authority,
    Policy,
    Delegation,
)

__all__ = [
    # Engine y Session
    "engine_gov",
    "Base_GOV",
    "SessionLocal_GOV",
    "get_gov_db",
    # Enums
    "AuthorityType",
    "PolicyScope",
    "GovStatus",
    # Modelos
    "Authority",
    "Policy",
    "Delegation",
]
