from fastapi import HTTPException
from passlib.context import CryptContext
import warnings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verificar_rol(usuario, roles_permitidos: list[str]):
    """
    ⛔ DEPRECADO — NO USAR EN CÓDIGO NUEVO
    
    Fecha de deprecación: 2026-01-01
    Fecha de muerte: 2026-04-01
    
    Esta función viola FASE 1 (ESPECIFICACION_CAMPO_ROL.md):
      - El campo `rol` es metadata descriptiva, NO autorización
      - La autorización debe basarse en AUP_SCOPE y AUP_GOV
    
    REEMPLAZO:
        from backend.core.scope.validator import validar_scope
        from backend.db.models import AccessLevel
        
        # En lugar de:
        #   verificar_rol(usuario, ["ADMIN_CONDOMINIO", "GUARDIA"])
        
        # Usar:
        #   if not validar_scope(db, usuario, tenant_id, AccessLevel.GUARDIA):
        #       raise HTTPException(403, "Sin scope válido")
    
    Documentación completa: docs/ESPECIFICACION_CAMPO_ROL.md
    Plan de migración: docs/FASE6_PLAN_ALINEACION.md
    """
    warnings.warn(
        "verificar_rol() está DEPRECADO desde 2026-01-01. "
        "Fecha de muerte: 2026-04-01. "
        "Usar validar_scope() según FASE 1. "
        "Ver docs/ESPECIFICACION_CAMPO_ROL.md",
        DeprecationWarning,
        stacklevel=2
    )
    if usuario.rol not in roles_permitidos:
        raise HTTPException(status_code=403, detail="Acceso denegado")
