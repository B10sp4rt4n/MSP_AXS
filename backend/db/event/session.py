"""
AUP_EVENT — Sesión de Base de Datos

Responsabilidad: Proveer sesiones para escritura de eventos (append-only)
"""

from sqlalchemy.orm import sessionmaker, Session
from .engine import engine_event

# SessionLocal para AUP_EVENT
SessionLocal_EVENT = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_event
)


def get_event_db() -> Session:
    """
    Dependency para FastAPI que provee sesión de AUP_EVENT.
    
    Axioma: Solo se usa para INSERT (append-only).
    
    Uso en routers:
        event_db: Session = Depends(get_event_db)
    """
    db = SessionLocal_EVENT()
    try:
        yield db
    finally:
        db.close()
