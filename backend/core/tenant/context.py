"""
═══════════════════════════════════════════════════════════════════════════════
AUP_TENANT Context - Middleware de Contexto Obligatorio
═══════════════════════════════════════════════════════════════════════════════

FASE 6: Plan de Alineación - Infraestructura Semana 1

PROPÓSITO:
  Ejecutar `SET app.tenant_id` ANTES de cualquier query que dependa de RLS.

CONTRATO:
  - Si no hay tenant_id → 400 Bad Request
  - Si usuario no tiene scope → 403 Forbidden
  - Si SET falla → 500 Internal Error
  - Si todo OK → retorna tenant_id

AXIOMA:
  RLS en PostgreSQL evalúa current_setting('app.tenant_id') al momento del query.
  El SET debe ocurrir en la MISMA conexión que ejecutará queries.

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from backend.db.core import Usuario, get_core_db
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.validator import validar_scope
from backend.db.models import AccessLevel

logger = logging.getLogger("aup.tenant")


class TenantContextError(Exception):
    """Error al configurar contexto de tenant."""
    pass


def set_tenant_context(
    tenant_id: str,
    db: Session = Depends(get_core_db),
    current_user: Usuario = Depends(get_current_user)
) -> str:
    """
    ═══════════════════════════════════════════════════════════════════════
    MIDDLEWARE OBLIGATORIO: Configura contexto de tenant para RLS
    ═══════════════════════════════════════════════════════════════════════
    
    Este dependency DEBE usarse en todo endpoint que opere sobre datos
    de un tenant específico.
    
    Flujo:
      1. Validar que tenant_id no esté vacío
      2. Validar que usuario tiene scope ACTIVO en el tenant
      3. Ejecutar SET app.tenant_id = <tenant_id>
      4. Retornar tenant_id para uso en endpoint
    
    Args:
        tenant_id: ID del tenant (viene de path/query param)
        db: Sesión de base de datos
        current_user: Usuario autenticado (de get_current_user)
        
    Returns:
        tenant_id validado
        
    Raises:
        HTTPException 400: Si tenant_id está vacío
        HTTPException 403: Si usuario no tiene scope en el tenant
        HTTPException 500: Si SET falla
        
    USO EN ENDPOINTS:
        @router.get("/condominio/{condominio_id}/visitas")
        def listar_visitas(
            condominio_id: str,
            db: Session = Depends(get_db),
            current_user: Usuario = Depends(get_current_user),
            _tenant: str = Depends(set_tenant_context),  # <-- OBLIGATORIO
        ):
            # Aquí RLS ya está activo con el tenant correcto
            ...
    """
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 1: Validar que tenant_id no esté vacío
    # ─────────────────────────────────────────────────────────────────────
    if not tenant_id or not tenant_id.strip():
        logger.warning(
            f"TENANT-CONTEXT: tenant_id vacío - usuario={current_user.usuario_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id es requerido"
        )
    
    tenant_id = tenant_id.strip()
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 2: Validar que usuario tiene scope ACTIVO en el tenant
    # ─────────────────────────────────────────────────────────────────────
    # Usamos nivel LECTURA como mínimo (el endpoint puede requerir más)
    if not validar_scope(db, current_user, tenant_id, AccessLevel.LECTURA):
        logger.warning(
            f"TENANT-CONTEXT: sin scope - usuario={current_user.usuario_id} "
            f"tenant={tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin acceso al tenant {tenant_id}"
        )
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 3: Ejecutar SET app.tenant_id
    # ─────────────────────────────────────────────────────────────────────
    try:
        # Usar parámetro para evitar SQL injection
        db.execute(text("SET app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        logger.info(
            f"TENANT-CONTEXT: SET exitoso - usuario={current_user.usuario_id} "
            f"tenant={tenant_id}"
        )
    except Exception as e:
        logger.error(
            f"TENANT-CONTEXT: SET falló - usuario={current_user.usuario_id} "
            f"tenant={tenant_id} error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al configurar contexto de tenant"
        )
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 4: Retornar tenant_id para uso en endpoint
    # ─────────────────────────────────────────────────────────────────────
    return tenant_id


def get_tenant_from_request(
    condominio_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> Optional[str]:
    """
    Helper para extraer tenant_id de diferentes fuentes.
    
    Soporta:
      - condominio_id (nombre usado en rutas existentes)
      - tenant_id (nombre canónico)
    
    Returns:
        tenant_id o None si no está presente
    """
    return condominio_id or tenant_id


def require_tenant_context(required_level: AccessLevel = AccessLevel.LECTURA):
    """
    Factory para crear dependency con nivel de acceso específico.
    
    USO:
        @router.post("/condominio/{condominio_id}/visitas")
        def crear_visita(
            condominio_id: str,
            _tenant: str = Depends(require_tenant_context(AccessLevel.ADMIN_CONDOMINIO)),
        ):
            ...
    """
    def _dependency(
        tenant_id: str,
        db: Session = Depends(get_core_db),
        current_user: Usuario = Depends(get_current_user)
    ) -> str:
        # Validar tenant_id
        if not tenant_id or not tenant_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id es requerido"
            )
        
        tenant_id = tenant_id.strip()
        
        # Validar scope con nivel específico
        if not validar_scope(db, current_user, tenant_id, required_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requiere nivel {required_level.value} en tenant {tenant_id}"
            )
        
        # SET context
        try:
            db.execute(text("SET app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al configurar contexto de tenant"
            )
        
        return tenant_id
    
    return _dependency
