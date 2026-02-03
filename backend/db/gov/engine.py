"""
AUP_GOV — Motor de Base de Datos (Poder Explícito)

Responsabilidad: Conectar con aup_gov (políticas, autoridades, delegaciones)
Axioma: Si AUP_GOV falla → deny by default
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

# Cargar variables de entorno
load_dotenv()

# Variable de entorno específica para AUP_GOV
DATABASE_GOV_URL = os.getenv(
    "DATABASE_GOV_URL",
    "sqlite:///./axs_gov.db"  # Fallback para desarrollo local
)

# Motor SQLAlchemy para AUP_GOV
engine_gov = create_engine(
    DATABASE_GOV_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_GOV_URL else {},
    poolclass=NullPool if "sqlite" in DATABASE_GOV_URL else None,
    pool_pre_ping=False if "sqlite" in DATABASE_GOV_URL else True,
    pool_recycle=300 if "sqlite" not in DATABASE_GOV_URL else -1,
    echo=False
)

# Base declarativa para modelos GOV
Base_GOV = declarative_base()
