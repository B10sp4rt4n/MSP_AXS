"""
AUP_EVENT — Dominio de Verdad Histórica

Exporta modelos, engine y session para AUP_EVENT.
"""

from .engine import engine_event, Base_EVENT
from .session import SessionLocal_EVENT, get_event_db
from .models import Event

__all__ = [
    # Engine y Session
    "engine_event",
    "Base_EVENT",
    "SessionLocal_EVENT",
    "get_event_db",
    # Modelos
    "Event",
]
