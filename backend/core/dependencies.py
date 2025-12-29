"""
═══════════════════════════════════════════════════════════════════════════════
Dependencies Globales - MIGRADO A AUP_SESSION
═══════════════════════════════════════════════════════════════════════════════

DEPRECADO: get_usuario_actual con X-User-Id
NUEVO: Usar backend.core.auth.dependencies.get_current_user

MIGRACIÓN:
  Antes:  usuario = Depends(get_usuario_actual)
  Ahora:  usuario = Depends(get_current_user)  # desde auth.dependencies

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.connection import SessionLocal
from ..db.models import Usuario

# Importar el nuevo sistema AUP
from .auth.dependencies import get_current_user, get_current_active_user


def get_db():
    """
    Dependency para obtener sesión de base de datos.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# DEPRECADO - Mantener temporalmente para compatibilidad hacia atrás
# ═══════════════════════════════════════════════════════════════════════════
def get_usuario_actual(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    """
    ⚠️  DEPRECADO - NO USAR EN CÓDIGO NUEVO
    
    Este método es INSEGURO (cualquiera puede falsificar X-User-Id).
    
    Migrar a:
        from backend.core.auth.dependencies import get_current_user
        usuario = Depends(get_current_user)
    """
    usuario = db.query(Usuario).filter(Usuario.usuario_id == x_user_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return usuario


# ═══════════════════════════════════════════════════════════════════════════
# NUEVO SISTEMA AUP - Usar en todo código nuevo
# ═══════════════════════════════════════════════════════════════════════════
# Exportar para facilitar imports
__all__ = [
    "get_db",
    "get_current_user",          # ← USAR ESTE
    "get_current_active_user",   # ← O ESTE
    "get_usuario_actual",        # ← DEPRECADO, solo retrocompatibilidad
]

