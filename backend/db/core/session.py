"""
AUP_CORE — Sesión de Base de Datos

Responsabilidad: Proveer sesiones para operaciones en aup_core
"""

from sqlalchemy.orm import sessionmaker, Session
from .engine import engine_core

# SessionLocal para AUP_CORE
SessionLocal_CORE = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_core
)


def get_core_db() -> Session:
    """
    Dependency para FastAPI que provee sesión de AUP_CORE.
    
    Uso en routers:
        db: Session = Depends(get_core_db)
    """
    db = SessionLocal_CORE()
    try:
        yield db
    finally:
        db.close()
