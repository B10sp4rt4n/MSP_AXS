"""
AUP_CORE — Motor de Base de Datos (Identidad y Alcance)

Responsabilidad: Conectar con aup_core (identidades, alcances, operaciones)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

# Variable de entorno específica para AUP_CORE
DATABASE_CORE_URL = os.getenv(
    "DATABASE_CORE_URL",
    "sqlite:///./axs_core.db"  # Fallback para desarrollo local
)

# Motor SQLAlchemy para AUP_CORE
engine_core = create_engine(
    DATABASE_CORE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_CORE_URL else {},
    poolclass=NullPool if "sqlite" in DATABASE_CORE_URL else None,
    echo=False  # Cambiar a True para debug
)

# Base declarativa para modelos CORE
Base_CORE = declarative_base()
