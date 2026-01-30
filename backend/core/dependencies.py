"""
═══════════════════════════════════════════════════════════════════════════════
Dependencies Globales — Memoria AUP Declarada
═══════════════════════════════════════════════════════════════════════════════

NOTA: get_db() ahora apunta a AUP_CORE por defecto (backward compatibility).

Para usar dominios específicos:
- get_core_db() → Identidad y Alcance
- get_event_db() → Eventos inmutables
- get_gov_db() → Políticas y gobierno

MIGRACIÓN AUTH:
  Antes:  usuario = Depends(get_usuario_actual)
  Ahora:  usuario = Depends(get_current_user)

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session

# Importar conexiones por dominio AUP
from backend.db.core import get_core_db
from backend.db.event import get_event_db
from backend.db.gov import get_gov_db
from backend.db.core import Usuario

# Importar el nuevo sistema AUP
from .auth.dependencies import get_current_user, get_current_active_user


def get_db():
    """
    Dependency para obtener sesión de base de datos AUP_CORE.
    
    DEPRECADO: Usar get_core_db() explícitamente en nuevos routers.
    Mantenido por backward compatibility.
    """
    yield from get_core_db()


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

