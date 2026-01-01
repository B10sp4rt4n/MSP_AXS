"""
═══════════════════════════════════════════════════════════════════════════════
AUP_SCOPE Validator - Validación Estructural de Alcance
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

  Este módulo implementa la validación estructural de AUP_SCOPE.
  
  NO contiene lógica de negocio.
  SÍ contiene validación estructural pura.
  
AXIOMA APLICADO:
  El sistema NO infiere alcance, lo VALIDA explícitamente.

FUNCIÓN CENTRAL:
  validar_scope(identity, tenant_id, required_level) -> bool
  
  Esta función responde UNA pregunta:
    ¿Existe un AUP_SCOPE activo que autorice esta identidad
     en este tenant con al menos este nivel de acceso?

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from backend.db.models import UserTenantScope, Usuario, AccessLevel, ScopeStatus

logger = logging.getLogger("axs.scope")


# ═══════════════════════════════════════════════════════════════════════════
# Jerarquía de Access Levels
# ═══════════════════════════════════════════════════════════════════════════

# Orden jerárquico de niveles de acceso (mayor a menor)
ACCESS_LEVEL_HIERARCHY = {
    AccessLevel.MSP_ADMIN: 100,
    AccessLevel.ADMIN_CONDOMINIO: 80,
    AccessLevel.GUARDIA: 60,
    AccessLevel.RESIDENTE: 40,
    AccessLevel.LECTURA: 20,
}


def nivel_suficiente(nivel_actual: AccessLevel, nivel_requerido: AccessLevel) -> bool:
    """
    Verifica si un nivel de acceso es suficiente para el requerido.
    
    Jerarquía:
      MSP_ADMIN > ADMIN_CONDOMINIO > GUARDIA > RESIDENTE > LECTURA
    
    Args:
        nivel_actual: Nivel que posee la identidad
        nivel_requerido: Nivel mínimo necesario
        
    Returns:
        True si nivel_actual >= nivel_requerido
    """
    return ACCESS_LEVEL_HIERARCHY.get(nivel_actual, 0) >= ACCESS_LEVEL_HIERARCHY.get(nivel_requerido, 0)


# ═══════════════════════════════════════════════════════════════════════════
# Validador Central de AUP_SCOPE
# ═══════════════════════════════════════════════════════════════════════════

def validar_scope(
    db: Session,
    usuario: Usuario,
    tenant_id: str,
    required_level: AccessLevel
) -> bool:
    """
    ═══════════════════════════════════════════════════════════════════════
    VALIDADOR ESTRUCTURAL DE AUP_SCOPE
    ═══════════════════════════════════════════════════════════════════════
    
    Valida si una AUP_IDENTITY tiene AUP_SCOPE válido en un AUP_TENANT.
    
    AXIOMAS APLICADOS:
      1. Sin AUP_SCOPE activo → No existe operativamente
      2. No se infiere alcance, se valida explícitamente
      3. El nivel de acceso debe ser suficiente
    
    Flujo:
      1. Buscar AUP_SCOPE para (usuario_id, tenant_id)
      2. Verificar estado = ACTIVO
      3. Verificar access_level >= required_level
      4. Retornar true/false (NO lanza excepciones)
    
    Args:
        db: Sesión de base de datos
        usuario: AUP_IDENTITY (objeto Usuario)
        tenant_id: AUP_TENANT objetivo (condominio_id)
        required_level: Nivel mínimo de acceso requerido
        
    Returns:
        True: Scope válido encontrado
        False: No existe scope o es insuficiente
        
    IMPORTANTE:
      Esta función NO lanza excepciones.
      El caller decide qué hacer con false (403, 404, etc.)
    """
    
    # Buscar AUP_SCOPE activo
    scope = db.query(UserTenantScope).filter(
        UserTenantScope.usuario_id == usuario.usuario_id,
        UserTenantScope.tenant_id == tenant_id,
        UserTenantScope.estado == ScopeStatus.ACTIVO
    ).first()
    
    if not scope:
        logger.warning(
            f"AUP_SCOPE no encontrado: usuario={usuario.usuario_id} "
            f"tenant={tenant_id} required={required_level.value}"
        )
        return False
    
    # Verificar jerarquía de acceso
    if not nivel_suficiente(scope.access_level, required_level):
        logger.warning(
            f"AUP_SCOPE insuficiente: usuario={usuario.usuario_id} "
            f"tenant={tenant_id} tiene={scope.access_level.value} "
            f"requiere={required_level.value}"
        )
        return False
    
    logger.info(
        f"AUP_SCOPE validado: usuario={usuario.usuario_id} "
        f"tenant={tenant_id} nivel={scope.access_level.value}"
    )
    return True


def obtener_scopes_usuario(
    db: Session,
    usuario_id: str
) -> List[UserTenantScope]:
    """
    Obtiene todos los AUP_SCOPE activos de una identidad.
    
    Útil para:
      - Listar tenants a los que tiene acceso
      - UI: mostrar condominios disponibles
      - Auditoría: ver alcance completo del usuario
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID de la AUP_IDENTITY
        
    Returns:
        Lista de AUP_SCOPE activos
    """
    return db.query(UserTenantScope).filter(
        UserTenantScope.usuario_id == usuario_id,
        UserTenantScope.estado == ScopeStatus.ACTIVO
    ).all()


def obtener_scope_especifico(
    db: Session,
    usuario_id: str,
    tenant_id: str
) -> Optional[UserTenantScope]:
    """
    Obtiene el AUP_SCOPE específico de un usuario en un tenant.
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID de la AUP_IDENTITY
        tenant_id: ID del AUP_TENANT
        
    Returns:
        UserTenantScope si existe (cualquier estado), None si no existe
    """
    return db.query(UserTenantScope).filter(
        UserTenantScope.usuario_id == usuario_id,
        UserTenantScope.tenant_id == tenant_id
    ).first()


def obtener_scope_usuario_en_tenant(
    db: Session,
    usuario_id: str,
    tenant_id: str
) -> Optional[UserTenantScope]:
    """
    Alias para obtener_scope_especifico (compatibilidad).
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID de la AUP_IDENTITY
        tenant_id: ID del AUP_TENANT
        
    Returns:
        UserTenantScope si existe, None si no existe
    """
    return obtener_scope_especifico(db, usuario_id, tenant_id)


# ═══════════════════════════════════════════════════════════════════════════
# Helper: Requerir Scope (lanza HTTPException si falla)
# ═══════════════════════════════════════════════════════════════════════════

def requerir_scope(
    db: Session,
    usuario: Usuario,
    tenant_id: str,
    required_level: AccessLevel,
    mensaje_error: Optional[str] = None
) -> None:
    """
    Versión estricta de validar_scope que lanza HTTPException si falla.
    
    Uso en endpoints:
        requerir_scope(db, usuario, condominio_id, AccessLevel.RESIDENTE)
        # Si llega aquí, tiene scope válido
    
    Args:
        db: Sesión de base de datos
        usuario: AUP_IDENTITY
        tenant_id: AUP_TENANT
        required_level: Nivel mínimo requerido
        mensaje_error: Mensaje personalizado (opcional)
        
    Raises:
        HTTPException 403: Si no tiene scope válido
    """
    if not validar_scope(db, usuario, tenant_id, required_level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=mensaje_error or f"Sin acceso al recurso solicitado en este condominio"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Helpers de Creación/Revocación (Para admin)
# ═══════════════════════════════════════════════════════════════════════════

def crear_scope(
    db: Session,
    usuario_id: str,
    tenant_id: str,
    access_level: AccessLevel
) -> UserTenantScope:
    """
    Crea un nuevo AUP_SCOPE.
    
    IMPORTANTE: Esta función NO valida si el usuario existe.
    El caller debe validar prerequisitos.
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID de AUP_IDENTITY
        tenant_id: ID de AUP_TENANT
        access_level: Nivel de acceso a otorgar
        
    Returns:
        UserTenantScope creado
    """
    scope = UserTenantScope(
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        access_level=access_level,
        estado=ScopeStatus.ACTIVO
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    
    logger.info(
        f"AUP_SCOPE creado: usuario={usuario_id} "
        f"tenant={tenant_id} nivel={access_level.value}"
    )
    return scope


def revocar_scope(
    db: Session,
    scope_id: int
) -> None:
    """
    Revoca un AUP_SCOPE existente.
    
    Args:
        db: Sesión de base de datos
        scope_id: ID del scope a revocar
    """
    from datetime import datetime
    
    scope = db.query(UserTenantScope).filter(UserTenantScope.id == scope_id).first()
    if scope:
        scope.estado = ScopeStatus.REVOCADO
        scope.revoked_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            f"AUP_SCOPE revocado: id={scope_id} "
            f"usuario={scope.usuario_id} tenant={scope.tenant_id}"
        )
