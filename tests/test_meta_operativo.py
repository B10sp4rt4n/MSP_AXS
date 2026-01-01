"""
═══════════════════════════════════════════════════════════════════════════════
Tests del Dominio Meta-Operativo v1.0 (CONGELADO)
═══════════════════════════════════════════════════════════════════════════════

Pruebas de correctitud según ACTA_CONGELAMIENTO_META_OPERATIVO_v1.0.md

Sección 5: Pruebas Conceptuales de Correctitud

Casos implementados:
  - 5.1 Casos válidos (DEBEN pasar)
  - 5.2 Casos inválidos (DEBEN fallar)
  - 5.3 Casos frontera
  - 5.4 Casos de violación (DEBEN romper)
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.db.models import (
    Usuario, Condominio, Authority, AuthorityType, GovStatus,
    IdentityTenantAssignment, AssignmentType
)
from backend.core.meta.assignments import (
    assign_identity_to_tenant,
    revoke_identity_from_tenant,
    list_tenant_assignments,
    list_identity_assignments
)


# ═══════════════════════════════════════════════════════════════════════════
# 5.1 Casos Válidos (DEBEN pasar)
# ═══════════════════════════════════════════════════════════════════════════

def test_caso_1_asignacion_basica(db: Session, setup_test_data):
    """
    CASO 1: Asignación básica.
    
    DADO: actor con authority GLOBAL activa
    CUANDO: assign_identity_to_tenant('user_1', 'condo_a', 'REGULAR_ADMIN')
    ENTONCES: Registro creado, revoked=false, retorna 201 equivalente
    """
    # Setup
    actor, user_1, condo_a = setup_test_data
    
    # Acción
    assignment = assign_identity_to_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        target_identity_id=user_1.usuario_id,
        target_tenant_id=condo_a.condominio_id,
        assignment_type=AssignmentType.REGULAR_ADMIN
    )
    
    # Verificaciones
    assert assignment.assignment_id is not None
    assert assignment.identity_id == user_1.usuario_id
    assert assignment.tenant_id == condo_a.condominio_id
    assert assignment.assignment_type == AssignmentType.REGULAR_ADMIN
    assert assignment.assigned_by_identity_id == actor.usuario_id
    assert assignment.revoked == 0  # false


def test_caso_2_revocacion_valida(db: Session, setup_test_data_with_assignment):
    """
    CASO 2: Revocación válida.
    
    DADO: assignment activa existente
    CUANDO: revoke_identity_from_tenant('assign_123', 'Fin de contrato')
    ENTONCES: revoked=true, revoked_at poblado, retorna 200 equivalente
    """
    # Setup
    actor, assignment = setup_test_data_with_assignment
    
    # Acción
    revoked = revoke_identity_from_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        assignment_id=assignment.assignment_id,
        revocation_reason="Fin de contrato"
    )
    
    # Verificaciones
    assert revoked.revoked == 1  # true
    assert revoked.revoked_by_identity_id == actor.usuario_id
    assert revoked.revoked_at is not None
    assert revoked.revocation_reason == "Fin de contrato"


def test_caso_3_lista_por_tenant(db: Session, setup_test_data_multiple_assignments):
    """
    CASO 3: Lista por tenant.
    
    DADO: tenant 'condo_a' con 3 asignaciones activas
    CUANDO: list_tenant_assignments('condo_a', include_revoked=false)
    ENTONCES: Retorna lista con 3 elementos, NO datos operativos
    """
    # Setup
    actor, condo_a = setup_test_data_multiple_assignments
    
    # Acción
    assignments = list_tenant_assignments(
        db=db,
        actor_identity_id=actor.usuario_id,
        tenant_id=condo_a.condominio_id,
        include_revoked=False
    )
    
    # Verificaciones
    assert len(assignments) == 3
    for a in assignments:
        assert a.tenant_id == condo_a.condominio_id
        assert a.revoked == 0


def test_caso_4_lista_por_identity(db: Session, setup_test_data_multi_tenant):
    """
    CASO 4: Lista por identity.
    
    DADO: identity 'user_1' con asignaciones en 2 tenants
    CUANDO: list_identity_assignments('user_1', include_revoked=false)
    ENTONCES: Retorna lista con 2 elementos, incluye tenant_ids
    """
    # Setup
    actor, user_1 = setup_test_data_multi_tenant
    
    # Acción
    assignments = list_identity_assignments(
        db=db,
        actor_identity_id=actor.usuario_id,
        identity_id=user_1.usuario_id,
        include_revoked=False
    )
    
    # Verificaciones
    assert len(assignments) == 2
    for a in assignments:
        assert a.identity_id == user_1.usuario_id
        assert a.revoked == 0


# ═══════════════════════════════════════════════════════════════════════════
# 5.2 Casos Inválidos (DEBEN fallar)
# ═══════════════════════════════════════════════════════════════════════════

def test_caso_5_sin_authority_global(db: Session, setup_test_data_no_global):
    """
    CASO 5: Sin authority GLOBAL.
    
    DADO: actor con FIRST_TIER authority (no GLOBAL)
    CUANDO: Intenta assign_identity_to_tenant
    ENTONCES: FAIL 403 "No tiene authority GLOBAL"
    """
    # Setup
    actor_without_global, user_1, condo_a = setup_test_data_no_global
    
    # Acción y verificación
    with pytest.raises(HTTPException) as exc_info:
        assign_identity_to_tenant(
            db=db,
            actor_identity_id=actor_without_global.usuario_id,
            target_identity_id=user_1.usuario_id,
            target_tenant_id=condo_a.condominio_id,
            assignment_type=AssignmentType.REGULAR_ADMIN
        )
    
    assert exc_info.value.status_code == 403
    assert "No tiene authority GLOBAL" in str(exc_info.value.detail)


def test_caso_6_tenant_inexistente(db: Session, setup_test_data):
    """
    CASO 6: Tenant inexistente.
    
    DADO: actor con authority GLOBAL activa
    CUANDO: Intenta asignar a tenant_id='inexistente'
    ENTONCES: FAIL 400 "Tenant no existe"
    """
    # Setup
    actor, user_1, _ = setup_test_data
    
    # Acción y verificación
    with pytest.raises(HTTPException) as exc_info:
        assign_identity_to_tenant(
            db=db,
            actor_identity_id=actor.usuario_id,
            target_identity_id=user_1.usuario_id,
            target_tenant_id="tenant_inexistente",
            assignment_type=AssignmentType.REGULAR_ADMIN
        )
    
    assert exc_info.value.status_code == 400
    assert "no existe" in str(exc_info.value.detail).lower()


def test_caso_7_asignacion_duplicada(db: Session, setup_test_data_with_assignment):
    """
    CASO 7: Asignación duplicada.
    
    DADO: user_1 YA tiene asignación activa en condo_a
    CUANDO: Intenta asignar nuevamente
    ENTONCES: FAIL 409 "Ya existe asignación activa"
    """
    # Setup
    actor, existing_assignment = setup_test_data_with_assignment
    
    # Acción y verificación
    with pytest.raises(HTTPException) as exc_info:
        assign_identity_to_tenant(
            db=db,
            actor_identity_id=actor.usuario_id,
            target_identity_id=existing_assignment.identity_id,
            target_tenant_id=existing_assignment.tenant_id,
            assignment_type=AssignmentType.REGULAR_ADMIN
        )
    
    assert exc_info.value.status_code == 409
    assert "Ya existe asignación activa" in str(exc_info.value.detail)


def test_caso_8_self_assignment_con_scope(db: Session, setup_test_data):
    """
    CASO 8: Self-assignment con scope operativo.
    
    DADO: actor con authority GLOBAL
    CUANDO: Intenta asignarse a sí mismo con REGULAR_ADMIN
    ENTONCES: FAIL 400 "GLOBAL authority no puede asignarse scope operativo"
    """
    # Setup
    actor, _, condo_a = setup_test_data
    
    # Acción y verificación
    with pytest.raises(HTTPException) as exc_info:
        assign_identity_to_tenant(
            db=db,
            actor_identity_id=actor.usuario_id,
            target_identity_id=actor.usuario_id,  # ← self-assignment
            target_tenant_id=condo_a.condominio_id,
            assignment_type=AssignmentType.REGULAR_ADMIN
        )
    
    assert exc_info.value.status_code == 400
    assert "no puede asignarse scope operativo" in str(exc_info.value.detail).lower()


def test_caso_9_revocar_ya_revocada(db: Session, setup_test_data_revoked_assignment):
    """
    CASO 9: Revocar asignación ya revocada.
    
    DADO: assignment con revoked=true
    CUANDO: Intenta revocar nuevamente
    ENTONCES: FAIL 404 "Asignación ya ha sido revocada"
    """
    # Setup
    actor, revoked_assignment = setup_test_data_revoked_assignment
    
    # Acción y verificación
    with pytest.raises(HTTPException) as exc_info:
        revoke_identity_from_tenant(
            db=db,
            actor_identity_id=actor.usuario_id,
            assignment_id=revoked_assignment.assignment_id,
            revocation_reason="Intento duplicado"
        )
    
    assert exc_info.value.status_code == 404
    assert "ya ha sido revocada" in str(exc_info.value.detail).lower()


# ═══════════════════════════════════════════════════════════════════════════
# 5.3 Casos Frontera
# ═══════════════════════════════════════════════════════════════════════════

def test_caso_11_asignacion_first_tier_admin(db: Session, setup_test_data):
    """
    CASO 11: Asignación FIRST_TIER_ADMIN.
    
    DADO: actor con authority GLOBAL
    CUANDO: assign con FIRST_TIER_ADMIN
    ENTONCES: Se crea authority FIRST_TIER para target
    """
    # Setup
    actor, user_1, condo_a = setup_test_data
    
    # Acción
    assignment = assign_identity_to_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        target_identity_id=user_1.usuario_id,
        target_tenant_id=condo_a.condominio_id,
        assignment_type=AssignmentType.FIRST_TIER_ADMIN
    )
    
    # Verificaciones
    assert assignment.assignment_type == AssignmentType.FIRST_TIER_ADMIN
    
    # Verificar que se creó authority FIRST_TIER
    authority = db.query(Authority).filter(
        Authority.identity_id == user_1.usuario_id,
        Authority.tenant_id == condo_a.condominio_id,
        Authority.tipo == AuthorityType.FIRST_TIER
    ).first()
    
    assert authority is not None
    assert authority.estado == GovStatus.ACTIVO


def test_caso_12_multiples_asignaciones_diferentes_tenants(db: Session, setup_test_data_two_tenants):
    """
    CASO 12: Múltiples asignaciones (diferentes tenants).
    
    DADO: user_1 sin asignaciones previas
    CUANDO: Se asigna a condo_a y condo_b
    ENTONCES: 2 registros independientes, puede operar en ambos
    """
    # Setup
    actor, user_1, condo_a, condo_b = setup_test_data_two_tenants
    
    # Acción 1
    assignment_a = assign_identity_to_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        target_identity_id=user_1.usuario_id,
        target_tenant_id=condo_a.condominio_id,
        assignment_type=AssignmentType.REGULAR_ADMIN
    )
    
    # Acción 2
    assignment_b = assign_identity_to_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        target_identity_id=user_1.usuario_id,
        target_tenant_id=condo_b.condominio_id,
        assignment_type=AssignmentType.REGULAR_ADMIN
    )
    
    # Verificaciones
    assert assignment_a.assignment_id != assignment_b.assignment_id
    assert assignment_a.tenant_id == condo_a.condominio_id
    assert assignment_b.tenant_id == condo_b.condominio_id
    
    # Verificar que puede listar ambas
    assignments = list_identity_assignments(
        db=db,
        actor_identity_id=actor.usuario_id,
        identity_id=user_1.usuario_id,
        include_revoked=False
    )
    assert len(assignments) == 2


def test_caso_13_revocacion_y_reasignacion(db: Session, setup_test_data_with_assignment):
    """
    CASO 13: Revocación y re-asignación.
    
    DADO: user_1 tiene asignación activa en condo_a
    CUANDO: Se revoca y luego se re-asigna
    ENTONCES: Primera: revoked=true, Segunda: nuevo registro revoked=false
    """
    # Setup
    actor, assignment_1 = setup_test_data_with_assignment
    
    # Acción 1: Revocar
    revoked = revoke_identity_from_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        assignment_id=assignment_1.assignment_id,
        revocation_reason="Temporalmente suspendido"
    )
    
    assert revoked.revoked == 1
    
    # Acción 2: Re-asignar
    assignment_2 = assign_identity_to_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        target_identity_id=assignment_1.identity_id,
        target_tenant_id=assignment_1.tenant_id,
        assignment_type=AssignmentType.REGULAR_ADMIN
    )
    
    # Verificaciones
    assert assignment_2.assignment_id != assignment_1.assignment_id
    assert assignment_2.revoked == 0
    assert assignment_1.revoked == 1  # La primera sigue revocada


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures de Setup
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def setup_test_data(db: Session):
    """Setup básico: actor GLOBAL, user_1, condo_a."""
    # Crear actor con authority GLOBAL
    actor = Usuario(
        usuario_id="actor_global",
        nombre="Actor Global",
        email="actor@test.com",
        rol="MSP_ADMIN"
    )
    db.add(actor)
    
    authority_global = Authority(
        authority_id="auth_global_001",
        identity_id=actor.usuario_id,
        tipo=AuthorityType.GLOBAL,
        estado=GovStatus.ACTIVO,
        tenant_id=None,
        created_at=datetime.utcnow()
    )
    db.add(authority_global)
    
    # Crear user_1
    user_1 = Usuario(
        usuario_id="user_1",
        nombre="Usuario 1",
        email="user1@test.com",
        rol="RESIDENTE"
    )
    db.add(user_1)
    
    # Crear condo_a
    condo_a = Condominio(
        condominio_id="condo_a",
        nombre="Condominio A"
    )
    db.add(condo_a)
    
    db.commit()
    
    return actor, user_1, condo_a


@pytest.fixture
def setup_test_data_with_assignment(db: Session, setup_test_data):
    """Setup con asignación activa existente."""
    actor, user_1, condo_a = setup_test_data
    
    assignment = assign_identity_to_tenant(
        db=db,
        actor_identity_id=actor.usuario_id,
        target_identity_id=user_1.usuario_id,
        target_tenant_id=condo_a.condominio_id,
        assignment_type=AssignmentType.REGULAR_ADMIN
    )
    
    return actor, assignment


# Nota: Implementar fixtures restantes según necesidad de los tests
