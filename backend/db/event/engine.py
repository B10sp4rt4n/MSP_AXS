"""
AUP_EVENT — Motor de Base de Datos (Verdad Histórica)

Responsabilidad: Conectar con aup_event (eventos inmutables)
Axioma: Append-only, nunca UPDATE/DELETE
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

# Variable de entorno específica para AUP_EVENT
DATABASE_EVENT_URL = os.getenv(
    "DATABASE_EVENT_URL",
    "sqlite:///./axs_event.db"  # Fallback para desarrollo local
)

# Motor SQLAlchemy para AUP_EVENT
engine_event = create_engine(
    DATABASE_EVENT_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_EVENT_URL else {},
    poolclass=NullPool if "sqlite" in DATABASE_EVENT_URL else None,
    pool_pre_ping=False if "sqlite" in DATABASE_EVENT_URL else True,
    pool_recycle=300 if "sqlite" not in DATABASE_EVENT_URL else -1,
    echo=False
)

# Base declarativa para modelos EVENT
Base_EVENT = declarative_base()
