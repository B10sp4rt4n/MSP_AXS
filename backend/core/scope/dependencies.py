"""
═══════════════════════════════════════════════════════════════════════════════
AUP_SCOPE Dependencies - Integración con FastAPI
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

  Este módulo conecta la validación de AUP_SCOPE con el sistema de
  dependency injection de FastAPI.
  
PRINCIPIO:
  Los endpoints NO deben llamar validar_scope() directamente.
  Usan dependencies que lo hacen transparentemente.

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, get_db
from backend.db.core import Usuario, AccessLevel
from .validator import requerir_scope


# ═══════════════════════════════════════════════════════════════════════════
# Factory de Dependencies para AUP_SCOPE
# ═══════════════════════════════════════════════════════════════════════════

def require_scope_for_tenant(
    required_level: AccessLevel,
    tenant_param: str = "condominio_id"
) -> Callable:
    """
    Factory que crea un dependency para validar AUP_SCOPE.
    
    CONCEPTO AUP:
      El tenant objetivo se extrae de:
        - Path parameter (ej: /condominio/{condominio_id}/...)
        - Query parameter (ej: ?condominio_id=...)
        - Body (ej: request body con condominio_id)
      
      El usuario se obtiene de AUP_SESSION (get_current_user).
      
      Se valida: ¿Tiene scope válido en ese tenant?
    
    USO:
        @router.get("/condominio/{condominio_id}/visitas")
        def get_visitas(
            condominio_id: str,
            _scope: None = Depends(require_scope_for_tenant(AccessLevel.RESIDENTE))
        ):
            # Si llega aquí, tiene scope válido
            return visitas
    
    Args:
        required_level: Nivel mínimo de acceso requerido
        tenant_param: Nombre del parámetro que contiene tenant_id
        
    Returns:
        Dependency function
    """
    
    def scope_dependency(
        tenant_id: str,  # Será inyectado desde path/query param
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """
        Dependency generado que valida AUP_SCOPE.
        
        AXIOMA APLICADO:
          Sin AUP_SCOPE válido → 403 Forbidden
        """
        requerir_scope(
            db=db,
            usuario=current_user,
            tenant_id=tenant_id,
            required_level=required_level,
            mensaje_error=f"Sin acceso de nivel {required_level.value} en este condominio"
        )
        # Si no lanza excepción, scope es válido
        return None
    
    # Modificar signature para que FastAPI sepa de dónde sacar tenant_id
    # Esto permite que funcione tanto con path param como query param
    scope_dependency.__signature__ = scope_dependency.__signature__.replace(
        parameters=[
            p.replace(name=tenant_param) if p.name == 'tenant_id' else p
            for p in scope_dependency.__signature__.parameters.values()
        ]
    )
    
    return scope_dependency


# ═══════════════════════════════════════════════════════════════════════════
# Dependencies Pre-configurados (Shortcuts)
# ═══════════════════════════════════════════════════════════════════════════

# Residente o superior
RequireResidenteScope = require_scope_for_tenant(AccessLevel.RESIDENTE)

# Guardia o superior
RequireGuardiaScope = require_scope_for_tenant(AccessLevel.GUARDIA)

# Admin de condominio o superior
RequireAdminCondominioScope = require_scope_for_tenant(AccessLevel.ADMIN_CONDOMINIO)

# MSP Admin
RequireMSPAdminScope = require_scope_for_tenant(AccessLevel.MSP_ADMIN)


# ═══════════════════════════════════════════════════════════════════════════
# Dependency Alternativo: Validar scope del usuario actual sin tenant explícito
# ═══════════════════════════════════════════════════════════════════════════

def validate_user_owns_resource_in_tenant(
    usuario: Usuario,
    resource_tenant_id: str,
    db: Session,
    required_level: AccessLevel = AccessLevel.RESIDENTE
) -> None:
    """
    Valida que el usuario tenga scope en el tenant del recurso.
    
    USO:
        # Cuando el tenant_id viene del recurso, no del path
        visita = obtener_visita(db, visita_id)
        validate_user_owns_resource_in_tenant(
            usuario=current_user,
            resource_tenant_id=visita.condominio_id,
            db=db,
            required_level=AccessLevel.RESIDENTE
        )
    
    Args:
        usuario: AUP_IDENTITY actual
        resource_tenant_id: Tenant al que pertenece el recurso
        db: Sesión BD
        required_level: Nivel mínimo requerido
        
    Raises:
        HTTPException 403: Si no tiene scope
    """
    requerir_scope(
        db=db,
        usuario=usuario,
        tenant_id=resource_tenant_id,
        required_level=required_level,
        mensaje_error="Sin acceso al recurso solicitado"
    )
