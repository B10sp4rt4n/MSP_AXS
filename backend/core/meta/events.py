"""
═══════════════════════════════════════════════════════════════════════════════
Eventos del Dominio Meta-Operativo v1.0 (CONGELADO)
═══════════════════════════════════════════════════════════════════════════════

Registro de eventos meta-operativos en AUP_EVENT.

Norma: ACTA_CONGELAMIENTO_META_OPERATIVO_v1.0.md sección 4

CRÍTICO: tenant_id DEBE ser NULL en todos los eventos meta.

El dominio meta NO opera dentro de ningún tenant.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.core.event.registry import registrar_evento
from backend.db.models import Usuario, IdentityTenantAssignment
from backend.core.meta import META_EVENT_ENTITY, META_EVENT_TENANT_ID, MetaAction


def registrar_evento_meta_assign(
    db: Session,
    actor: Usuario,
    session_token: str,
    assignment: IdentityTenantAssignment
) -> None:
    """
    Registra evento META_ASSIGN.
    
    Norma: Sección 4.1 del acta de congelamiento.
    
    tenant_id = NULL (crítico: no hay contexto de tenant en acciones meta)
    
    Args:
        db: Sesión de BD
        actor: Identidad que ejecuta la asignación
        session_token: JWT completo para hash
        assignment: Asignación creada
    """
    registrar_evento(
        db=db,
        identity=actor,
        session_token=session_token,
        tenant_id=META_EVENT_TENANT_ID,  # NULL - NO hay tenant activo
        entidad=META_EVENT_ENTITY,
        entidad_id=assignment.assignment_id,
        accion=MetaAction.ASSIGN.value,
        resultado="PERMITIDO",
        motivo="Asignación meta-operativa",
        metadata={
            "target_identity_id": assignment.identity_id,
            "target_tenant_id": assignment.tenant_id,
            "assignment_type": assignment.assignment_type.value
        }
    )


def registrar_evento_meta_revoke(
    db: Session,
    actor: Usuario,
    session_token: str,
    assignment: IdentityTenantAssignment
) -> None:
    """
    Registra evento META_REVOKE.
    
    Norma: Sección 4.2 del acta de congelamiento.
    
    tenant_id = NULL (crítico: no hay contexto de tenant en acciones meta)
    
    Args:
        db: Sesión de BD
        actor: Identidad que ejecuta la revocación
        session_token: JWT completo para hash
        assignment: Asignación revocada
    """
    registrar_evento(
        db=db,
        identity=actor,
        session_token=session_token,
        tenant_id=META_EVENT_TENANT_ID,  # NULL - NO hay tenant activo
        entidad=META_EVENT_ENTITY,
        entidad_id=assignment.assignment_id,
        accion=MetaAction.REVOKE.value,
        resultado="PERMITIDO",
        motivo=assignment.revocation_reason or "Revocación meta-operativa",
        metadata={
            "target_identity_id": assignment.identity_id,
            "target_tenant_id": assignment.tenant_id,
            "revocation_reason": assignment.revocation_reason
        }
    )


def registrar_evento_meta_list(
    db: Session,
    actor: Usuario,
    session_token: str,
    query_type: str,
    filter_value: str,
    include_revoked: bool,
    result_count: int
) -> None:
    """
    Registra evento META_LIST.
    
    Norma: Sección 4.3 del acta de congelamiento.
    
    tenant_id = NULL (crítico: no hay contexto de tenant en acciones meta)
    
    Args:
        db: Sesión de BD
        actor: Identidad que ejecuta la consulta
        session_token: JWT completo para hash
        query_type: Tipo de consulta (BY_TENANT | BY_IDENTITY)
        filter_value: Valor del filtro (tenant_id o identity_id)
        include_revoked: Si se incluyeron revocadas
        result_count: Cantidad de resultados
    """
    registrar_evento(
        db=db,
        identity=actor,
        session_token=session_token,
        tenant_id=META_EVENT_TENANT_ID,  # NULL - NO hay tenant activo
        entidad=META_EVENT_ENTITY,
        entidad_id="LIST_QUERY",
        accion=MetaAction.LIST.value,
        resultado="PERMITIDO",
        motivo="Consulta meta-operativa",
        metadata={
            "query_type": query_type,
            "filter_value": filter_value,
            "include_revoked": include_revoked,
            "result_count": result_count
        }
    )


def registrar_evento_meta_denegado(
    db: Session,
    actor_identity_id: str,
    session_token: str,
    accion: str,
    motivo: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Registra evento meta DENEGADO.
    
    Para cuando una acción meta falla validaciones.
    
    Norma: Sección 4 del acta de congelamiento.
    
    tenant_id = NULL (crítico)
    
    Args:
        db: Sesión de BD
        actor_identity_id: ID de la identidad que intentó la acción
        session_token: JWT completo para hash
        accion: Acción intentada (ASSIGN | REVOKE | LIST)
        motivo: Razón del fallo
        metadata: Contexto adicional
    """
    from backend.db.models import Usuario
    
    actor = db.query(Usuario).filter(
        Usuario.usuario_id == actor_identity_id
    ).first()
    
    if not actor:
        # Si el actor no existe, no podemos registrar evento
        return
    
    registrar_evento(
        db=db,
        identity=actor,
        session_token=session_token,
        tenant_id=META_EVENT_TENANT_ID,  # NULL - NO hay tenant activo
        entidad=META_EVENT_ENTITY,
        entidad_id="FAILED_ACTION",
        accion=accion,
        resultado="DENEGADO",
        motivo=motivo,
        metadata=metadata or {}
    )
