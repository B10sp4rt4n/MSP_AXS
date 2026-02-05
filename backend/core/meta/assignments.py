"""
═══════════════════════════════════════════════════════════════════════════════
Acciones del Dominio Meta-Operativo v1.0 (CONGELADO)
═══════════════════════════════════════════════════════════════════════════════

Implementación de las 4 acciones meta-operativas permitidas.

Norma: ACTA_CONGELAMIENTO_META_OPERATIVO_v1.0.md sección 3

ALCANCE CERRADO:
  - assign_identity_to_tenant()
  - revoke_identity_from_tenant()
  - list_tenant_assignments()
  - list_identity_assignments()

NO existen otras funciones.
NO se aceptan variaciones.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.db.models import IdentityTenantAssignment, UserTenantScope, AccessLevel
from backend.db.models import Authority, AuthorityType, GovStatus, ScopeStatus
from backend.core.meta import AssignmentType
from backend.core.meta.validators import (
    validate_global_authority,
    validate_identity_exists,
    validate_tenant_exists,
    validate_no_active_assignment,
    validate_no_self_assignment_with_scope,
    validate_assignment_exists_and_not_revoked
)


def assign_identity_to_tenant(
    db: Session,
    actor_identity_id: str,
    target_identity_id: str,
    target_tenant_id: str,
    assignment_type: AssignmentType
) -> IdentityTenantAssignment:
    """
    Acción: ASSIGN_IDENTITY_TO_TENANT.
    
    Crea relación Identity → Tenant de forma auditable.
    
    Norma: Sección 3.1 del acta de congelamiento.
    
    Precondiciones (DEBEN cumplirse):
      1. actor tiene authority GLOBAL activa
      2. target_identity existe
      3. target_tenant existe
      4. NO existe asignación activa previa
      5. Si assignment_type implica scope operativo: target ≠ actor
    
    Postcondiciones (garantizadas si éxito):
      1. Registro creado en identity_tenant_assignments
      2. Si assignment_type=FIRST_TIER_ADMIN: se crea authority FIRST_TIER
      3. Si assignment_type implica scope: se crea user_tenant_scope
    
    Args:
        db: Sesión de BD
        actor_identity_id: Quién ejecuta (debe tener authority GLOBAL)
        target_identity_id: A quién se asigna
        target_tenant_id: En qué tenant
        assignment_type: Tipo de asignación
    
    Returns:
        IdentityTenantAssignment creada
    
    Raises:
        HTTPException(403): Si actor no tiene authority GLOBAL
        HTTPException(400): Si target_identity no existe, tenant no existe,
                           o self-assignment inválido
        HTTPException(409): Si ya existe asignación activa
    """
    # Precondición 1: Authority GLOBAL
    validate_global_authority(db, actor_identity_id)
    
    # Precondición 2: Target identity existe
    target_identity = validate_identity_exists(db, target_identity_id)
    
    # Precondición 3: Target tenant existe
    target_tenant = validate_tenant_exists(db, target_tenant_id)
    
    # Precondición 4: No duplicados
    validate_no_active_assignment(db, target_identity_id, target_tenant_id)
    
    # Precondición 5: No self-assignment con scope operativo
    validate_no_self_assignment_with_scope(
        actor_identity_id,
        target_identity_id,
        assignment_type.value
    )
    
    # Crear asignación
    assignment = IdentityTenantAssignment(
        assignment_id=f"assign_{uuid.uuid4().hex[:16]}",
        identity_id=target_identity_id,
        tenant_id=target_tenant_id,
        assignment_type=assignment_type,
        assigned_by_identity_id=actor_identity_id,
        assigned_at=datetime.utcnow(),
        revoked=0,  # false
        revoked_by_identity_id=None,
        revoked_at=None,
        revocation_reason=None
    )
    
    db.add(assignment)
    
    # Sincronización con estructuras operativas
    if assignment_type == AssignmentType.FIRST_TIER_ADMIN:
        # Crear authority FIRST_TIER
        authority = Authority(
            authority_id=f"auth_{uuid.uuid4().hex[:16]}",
            identity_id=target_identity_id,
            tipo=AuthorityType.FIRST_TIER,
            tenant_id=target_tenant_id,
            estado=GovStatus.ACTIVO,
            metadata={"created_by_meta_assignment": assignment.assignment_id},
            created_at=datetime.utcnow()
        )
        db.add(authority)
    
    if assignment_type in [AssignmentType.REGULAR_ADMIN, AssignmentType.OPERATOR]:
        # Crear scope operativo
        access_level = (
            AccessLevel.ADMIN_CONDOMINIO 
            if assignment_type == AssignmentType.REGULAR_ADMIN 
            else AccessLevel.GUARDIA
        )
        
        scope = UserTenantScope(
            usuario_id=target_identity_id,
            tenant_id=target_tenant_id,
            access_level=access_level,
            estado=ScopeStatus.ACTIVO,
            created_at=datetime.utcnow()
        )
        db.add(scope)
    
    db.commit()
    db.refresh(assignment)
    
    return assignment


def revoke_identity_from_tenant(
    db: Session,
    actor_identity_id: str,
    assignment_id: str,
    revocation_reason: Optional[str] = None
) -> IdentityTenantAssignment:
    """
    Acción: REVOKE_IDENTITY_FROM_TENANT.
    
    Revoca relación Identity → Tenant de forma auditable.
    
    Norma: Sección 3.2 del acta de congelamiento.
    
    Precondiciones:
      1. actor tiene authority GLOBAL activa
      2. assignment_id existe
      3. Asignación NO está ya revocada
    
    Postcondiciones:
      1. Campo revoked = true (1)
      2. Campos revoked_by_identity_id, revoked_at poblados
      3. Si existe scope operativo: marcado como REVOCADO
      4. Si existe authority FIRST_TIER: marcada como REVOCADO
    
    Args:
        db: Sesión de BD
        actor_identity_id: Quién ejecuta (debe tener authority GLOBAL)
        assignment_id: ID de la asignación a revocar
        revocation_reason: Motivo de revocación (opcional)
    
    Returns:
        IdentityTenantAssignment revocada
    
    Raises:
        HTTPException(403): Si actor no tiene authority GLOBAL
        HTTPException(404): Si assignment no existe o ya está revocada
    """
    # Precondición 1: Authority GLOBAL
    validate_global_authority(db, actor_identity_id)
    
    # Precondiciones 2 y 3: Assignment existe y no está revocada
    assignment = validate_assignment_exists_and_not_revoked(db, assignment_id)
    
    # Revocar asignación
    assignment.revoked = 1  # true
    assignment.revoked_by_identity_id = actor_identity_id
    assignment.revoked_at = datetime.utcnow()
    assignment.revocation_reason = revocation_reason
    
    # Sincronización: revocar estructuras operativas
    # 1. Revocar scope operativo si existe
    scope = db.query(UserTenantScope).filter(
        UserTenantScope.usuario_id == assignment.identity_id,
        UserTenantScope.tenant_id == assignment.tenant_id,
        UserTenantScope.estado == ScopeStatus.ACTIVO
    ).first()
    
    if scope:
        scope.estado = ScopeStatus.REVOCADO
    
    # 2. Revocar authority FIRST_TIER si existe
    authority = db.query(Authority).filter(
        Authority.identity_id == assignment.identity_id,
        Authority.tenant_id == assignment.tenant_id,
        Authority.tipo == AuthorityType.FIRST_TIER,
        Authority.estado == GovStatus.ACTIVO
    ).first()
    
    if authority:
        authority.estado = GovStatus.REVOCADO
        authority.revoked_at = datetime.utcnow()
    
    db.commit()
    db.refresh(assignment)
    
    return assignment


def list_tenant_assignments(
    db: Session,
    actor_identity_id: str,
    tenant_id: str,
    include_revoked: bool = False
) -> List[IdentityTenantAssignment]:
    """
    Acción: LIST_TENANT_ASSIGNMENTS.
    
    Lista asignaciones de un tenant específico.
    
    Norma: Sección 3.3 del acta de congelamiento.
    
    Precondiciones:
      1. actor tiene authority GLOBAL activa
      2. tenant_id proporcionado
    
    Límites:
      - Retorna SOLO registros de identity_tenant_assignments
      - NO retorna datos operativos del tenant
    
    Args:
        db: Sesión de BD
        actor_identity_id: Quién ejecuta (debe tener authority GLOBAL)
        tenant_id: Tenant a consultar
        include_revoked: Si incluir asignaciones revocadas
    
    Returns:
        Lista de asignaciones
    
    Raises:
        HTTPException(403): Si actor no tiene authority GLOBAL
    """
    # Precondición 1: Authority GLOBAL
    validate_global_authority(db, actor_identity_id)
    
    # Consulta
    query = db.query(IdentityTenantAssignment).filter(
        IdentityTenantAssignment.tenant_id == tenant_id
    )
    
    if not include_revoked:
        query = query.filter(IdentityTenantAssignment.revoked == 0)
    
    return query.all()


def list_identity_assignments(
    db: Session,
    actor_identity_id: str,
    identity_id: str,
    include_revoked: bool = False
) -> List[IdentityTenantAssignment]:
    """
    Acción: LIST_IDENTITY_ASSIGNMENTS.
    
    Lista asignaciones de una identidad específica.
    
    Norma: Sección 3.4 del acta de congelamiento.
    
    Precondiciones:
      1. actor tiene authority GLOBAL activa
      2. identity_id proporcionado
    
    Límites:
      - Retorna SOLO registros de identity_tenant_assignments
      - NO retorna datos operativos de ningún tenant
    
    Args:
        db: Sesión de BD
        actor_identity_id: Quién ejecuta (debe tener authority GLOBAL)
        identity_id: Identidad a consultar
        include_revoked: Si incluir asignaciones revocadas
    
    Returns:
        Lista de asignaciones
    
    Raises:
        HTTPException(403): Si actor no tiene authority GLOBAL
    """
    # Precondición 1: Authority GLOBAL
    validate_global_authority(db, actor_identity_id)
    
    # Consulta
    query = db.query(IdentityTenantAssignment).filter(
        IdentityTenantAssignment.identity_id == identity_id
    )
    
    if not include_revoked:
        query = query.filter(IdentityTenantAssignment.revoked == 0)
    
    return query.all()
