"""
═══════════════════════════════════════════════════════════════════════════════
Validaciones del Dominio Meta-Operativo v1.0 (CONGELADO)
═══════════════════════════════════════════════════════════════════════════════

Funciones de validación que DEBEN FALLAR DURO ante violaciones.

Norma: ACTA_CONGELAMIENTO_META_OPERATIVO_v1.0.md sección 3 y 5.1

NO suavizar errores.
NO permitir excepciones.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.db.models import Usuario, Condominio, Authority, AuthorityType, GovStatus
from backend.db.models import IdentityTenantAssignment


def validate_global_authority(db: Session, actor_identity_id: str) -> None:
    """
    VALIDACIÓN 1: Authority GLOBAL activa.
    
    El actor DEBE tener authority de tipo GLOBAL y estado ACTIVO.
    
    Norma: Sección 5.1 VALIDACIÓN 1
    
    Fallo: 403 si no cumple.
    
    Args:
        db: Sesión de BD
        actor_identity_id: ID de la identidad que ejecuta la acción
    
    Raises:
        HTTPException(403): Si no tiene authority GLOBAL activa
    """
    authority = db.query(Authority).filter(
        Authority.identity_id == actor_identity_id,
        Authority.tipo == AuthorityType.GLOBAL,
        Authority.estado == GovStatus.ACTIVO
    ).first()
    
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene authority GLOBAL para acciones meta-operativas"
        )


def validate_identity_exists(db: Session, identity_id: str) -> Usuario:
    """
    VALIDACIÓN 3: Identidad existe.
    
    Norma: Sección 5.1 VALIDACIÓN 3 (parte de invariante 4)
    
    Fallo: 400 si no existe.
    
    Args:
        db: Sesión de BD
        identity_id: ID de la identidad a validar
    
    Returns:
        Usuario si existe
    
    Raises:
        HTTPException(400): Si la identidad no existe
    """
    identity = db.query(Usuario).filter(
        Usuario.usuario_id == identity_id
    ).first()
    
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Identidad {identity_id} no encontrada"
        )
    
    return identity


def validate_tenant_exists(db: Session, tenant_id: str) -> Condominio:
    """
    VALIDACIÓN 3: Tenant existe.
    
    Norma: Sección 5.1 VALIDACIÓN 3
    
    Fallo: 400 si no existe.
    
    Args:
        db: Sesión de BD
        tenant_id: ID del tenant a validar
    
    Returns:
        Condominio si existe
    
    Raises:
        HTTPException(400): Si el tenant no existe
    """
    tenant = db.query(Condominio).filter(
        Condominio.condominio_id == tenant_id
    ).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant {tenant_id} no existe"
        )
    
    return tenant


def validate_no_active_assignment(
    db: Session,
    identity_id: str,
    tenant_id: str
) -> None:
    """
    VALIDACIÓN 4: No duplicados activos.
    
    Norma: Sección 5.1 VALIDACIÓN 4
    
    Fallo: 409 si existe asignación activa.
    
    Args:
        db: Sesión de BD
        identity_id: ID de la identidad
        tenant_id: ID del tenant
    
    Raises:
        HTTPException(409): Si ya existe asignación activa
    """
    existing = db.query(IdentityTenantAssignment).filter(
        IdentityTenantAssignment.identity_id == identity_id,
        IdentityTenantAssignment.tenant_id == tenant_id,
        IdentityTenantAssignment.revoked == 0  # false
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe asignación activa para identidad {identity_id} en tenant {tenant_id}"
        )


def validate_no_self_assignment_with_scope(
    actor_identity_id: str,
    target_identity_id: str,
    assignment_type: str
) -> None:
    """
    VALIDACIÓN 2: No self-assignment operativo.
    
    GLOBAL authority no puede asignarse scope operativo a sí misma.
    
    Norma: Sección 5.1 VALIDACIÓN 2
    
    Fallo: 400 si actor == target y assignment implica scope operativo.
    
    Args:
        actor_identity_id: Quién ejecuta
        target_identity_id: A quién se asigna
        assignment_type: Tipo de asignación
    
    Raises:
        HTTPException(400): Si es self-assignment con scope operativo
    """
    if actor_identity_id == target_identity_id:
        if assignment_type in ["REGULAR_ADMIN", "OPERATOR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GLOBAL authority no puede asignarse scope operativo a sí misma"
            )


def validate_assignment_exists_and_not_revoked(
    db: Session,
    assignment_id: str
) -> IdentityTenantAssignment:
    """
    VALIDACIÓN 5: Asignación existe y no está revocada.
    
    Norma: Sección 5.1 VALIDACIÓN 5
    
    Fallo: 404 si no existe o ya está revocada.
    
    Args:
        db: Sesión de BD
        assignment_id: ID de la asignación
    
    Returns:
        IdentityTenantAssignment si existe y no está revocada
    
    Raises:
        HTTPException(404): Si no existe o ya está revocada
    """
    assignment = db.query(IdentityTenantAssignment).filter(
        IdentityTenantAssignment.assignment_id == assignment_id,
        IdentityTenantAssignment.revoked == 0  # false
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o ya ha sido revocada"
        )
    
    return assignment
