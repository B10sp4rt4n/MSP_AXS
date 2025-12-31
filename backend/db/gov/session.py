"""
AUP_GOV — Sesión de Base de Datos

Responsabilidad: Proveer sesiones para consulta/modificación de políticas
"""

from sqlalchemy.orm import sessionmaker, Session
from .engine import engine_gov

# SessionLocal para AUP_GOV
SessionLocal_GOV = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_gov
)


def get_gov_db() -> Session:
    """
    Dependency para FastAPI que provee sesión de AUP_GOV.
    
    Axioma: Si esta conexión falla, operación se deniega (default deny).
    
    Uso en routers:
        gov_db: Session = Depends(get_gov_db)
    """
    db = SessionLocal_GOV()
    try:
        yield db
    finally:
        db.close()
