"""
AUP_GOV — Motor de Base de Datos (Poder Explícito)

Responsabilidad: Conectar con aup_gov (políticas, autoridades, delegaciones)
Axioma: Si AUP_GOV falla → deny by default
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

# Variable de entorno específica para AUP_GOV
DATABASE_GOV_URL = os.getenv(
    "DATABASE_GOV_URL",
    "sqlite:///./axs_gov.db"  # Fallback para desarrollo local
)

# Motor SQLAlchemy para AUP_GOV
_is_sqlite = "sqlite" in DATABASE_GOV_URL
engine_gov = create_engine(
    DATABASE_GOV_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    poolclass=NullPool if _is_sqlite else None,
    pool_pre_ping=not _is_sqlite,  # Detecta conexiones muertas de Neon
    pool_recycle=300 if not _is_sqlite else -1,
    echo=False
)

# Base declarativa para modelos GOV
Base_GOV = declarative_base()
