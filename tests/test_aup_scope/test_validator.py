"""
Tests for AUP_SCOPE - Multi-tenancy and Access Level Validation

Coverage target: 70%+

Tests:
- Access level hierarchy
- Scope validation
- Multi-tenant isolation
- Role-based access control
"""

import pytest
from backend.db.core import AccessLevel, ScopeStatus, UserTenantScope, Usuario, Condominio, MSP
from backend.core.scope.validator import (
    nivel_suficiente,
    validar_scope,
    ACCESS_LEVEL_HIERARCHY
)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Access Level Hierarchy
# ═══════════════════════════════════════════════════════════════════════════

def test_jerarquia_access_levels():
    """
    Test: Verificar que la jerarquía de niveles es correcta.
    
    Order: MSP_ADMIN > ADMIN_CONDOMINIO > GUARDIA > RESIDENTE > LECTURA
    """
    # Assert
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.MSP_ADMIN] == 100
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.ADMIN_CONDOMINIO] == 80
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.GUARDIA] == 60
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.RESIDENTE] == 40
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.LECTURA] == 20
    
    # Verify ordering
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.MSP_ADMIN] > ACCESS_LEVEL_HIERARCHY[AccessLevel.ADMIN_CONDOMINIO]
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.ADMIN_CONDOMINIO] > ACCESS_LEVEL_HIERARCHY[AccessLevel.GUARDIA]
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.GUARDIA] > ACCESS_LEVEL_HIERARCHY[AccessLevel.RESIDENTE]
    assert ACCESS_LEVEL_HIERARCHY[AccessLevel.RESIDENTE] > ACCESS_LEVEL_HIERARCHY[AccessLevel.LECTURA]


def test_nivel_suficiente_mismo_nivel():
    """
    Test: Un nivel es suficiente para sí mismo.
    """
    # Assert
    assert nivel_suficiente(AccessLevel.ADMIN_CONDOMINIO, AccessLevel.ADMIN_CONDOMINIO) is True
    assert nivel_suficiente(AccessLevel.RESIDENTE, AccessLevel.RESIDENTE) is True


def test_nivel_suficiente_nivel_superior():
    """
    Test: Un nivel superior es suficiente para un nivel inferior requerido.
    """
    # Assert
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.ADMIN_CONDOMINIO) is True
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.GUARDIA) is True
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.RESIDENTE) is True
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.LECTURA) is True
    
    assert nivel_suficiente(AccessLevel.ADMIN_CONDOMINIO, AccessLevel.GUARDIA) is True
    assert nivel_suficiente(AccessLevel.ADMIN_CONDOMINIO, AccessLevel.RESIDENTE) is True
    
    assert nivel_suficiente(AccessLevel.GUARDIA, AccessLevel.RESIDENTE) is True


def test_nivel_suficiente_nivel_inferior():
    """
    Test: Un nivel inferior NO es suficiente para un nivel superior requerido.
    """
    # Assert
    assert nivel_suficiente(AccessLevel.RESIDENTE, AccessLevel.ADMIN_CONDOMINIO) is False
    assert nivel_suficiente(AccessLevel.RESIDENTE, AccessLevel.MSP_ADMIN) is False
    assert nivel_suficiente(AccessLevel.GUARDIA, AccessLevel.MSP_ADMIN) is False
    assert nivel_suficiente(AccessLevel.LECTURA, AccessLevel.RESIDENTE) is False


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Scope Validation
# ═══════════════════════════════════════════════════════════════════════════

def test_validar_scope_usuario_con_scope_activo(db_core_session):
    """
    Test: Usuario con SCOPE activo en tenant pasa validación.
    """
    # Arrange
    msp = MSP(msp_id="msp_001", nombre="MSP Test")
    db_core_session.add(msp)
    
    condo = Condominio(
        condominio_id="condo_001",
        msp_id="msp_001",
        nombre="Condominio Test",
    )
    db_core_session.add(condo)
    
    usuario = Usuario(
        usuario_id="user_001",
        nombre="Test",
        email="test@example.com",
        password_hash="hashed_password",
        rol="ADMIN",
        condominio_id="condo_001",
    )
    db_core_session.add(usuario)
    
    scope = UserTenantScope(
        usuario_id="user_001",
        tenant_id="condo_001",
        access_level=AccessLevel.ADMIN_CONDOMINIO,
        estado=ScopeStatus.ACTIVO
    )
    db_core_session.add(scope)
    db_core_session.commit()
    
    # Act
    result = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_001",
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    # Assert
    assert result is True


def test_validar_scope_usuario_sin_scope(db_core_session):
    """
    Test: Usuario sin SCOPE en tenant falla validación.
    
    Axioma AUP: Sin SCOPE activo → No existe operativamente.
    """
    # Arrange
    msp = MSP(msp_id="msp_002", nombre="MSP Test 2")
    db_core_session.add(msp)
    
    condo = Condominio(
        condominio_id="condo_002",
        msp_id="msp_002",
        nombre="Condominio Test 2",
    )
    db_core_session.add(condo)
    
    usuario = Usuario(
        usuario_id="user_002",
        nombre="Test",
        email="test2@example.com",
        password_hash="hashed_password",
        rol="RESIDENTE",
        condominio_id="condo_002",
    )
    db_core_session.add(usuario)
    db_core_session.commit()
    
    # Act (no scope created)
    result = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_002",
        required_level=AccessLevel.RESIDENTE
    )
    
    # Assert
    assert result is False


def test_validar_scope_usuario_scope_suspendido(db_core_session):
    """
    Test: Usuario con SCOPE suspendido falla validación.
    
    Axioma AUP: Solo SCOPE ACTIVO cuenta.
    """
    # Arrange
    msp = MSP(msp_id="msp_003", nombre="MSP Test 3")
    db_core_session.add(msp)
    
    condo = Condominio(
        condominio_id="condo_003",
        msp_id="msp_003",
        nombre="Condominio Test 3",
    )
    db_core_session.add(condo)
    
    usuario = Usuario(
        usuario_id="user_003",
        nombre="Test",
        email="test3@example.com",
        password_hash="hashed_password",
        rol="RESIDENTE",
        condominio_id="condo_003",
    )
    db_core_session.add(usuario)
    
    scope = UserTenantScope(
        usuario_id="user_003",
        tenant_id="condo_003",
        access_level=AccessLevel.RESIDENTE,
        estado=ScopeStatus.SUSPENDIDO  # ← Suspendido
    )
    db_core_session.add(scope)
    db_core_session.commit()
    
    # Act
    result = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_003",
        required_level=AccessLevel.RESIDENTE
    )
    
    # Assert
    assert result is False


def test_validar_scope_nivel_insuficiente(db_core_session):
    """
    Test: Usuario con SCOPE activo pero nivel insuficiente falla.
    """
    # Arrange
    msp = MSP(msp_id="msp_004", nombre="MSP Test 4")
    db_core_session.add(msp)
    
    condo = Condominio(
        condominio_id="condo_004",
        msp_id="msp_004",
        nombre="Condominio Test 4",
    )
    db_core_session.add(condo)
    
    usuario = Usuario(
        usuario_id="user_004",
        nombre="Test",
        email="test4@example.com",
        password_hash="hashed_password",
        rol="RESIDENTE",
        condominio_id="condo_004",
    )
    db_core_session.add(usuario)
    
    scope = UserTenantScope(
        usuario_id="user_004",
        tenant_id="condo_004",
        access_level=AccessLevel.LECTURA,  # ← Solo lectura
        estado=ScopeStatus.ACTIVO
    )
    db_core_session.add(scope)
    db_core_session.commit()
    
    # Act (requiere ADMIN pero solo tiene LECTURA)
    result = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_004",
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    # Assert
    assert result is False


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Multi-Tenant Isolation
# ═══════════════════════════════════════════════════════════════════════════

def test_aislamiento_multi_tenant(db_core_session):
    """
    Test: Usuario con SCOPE en tenant A NO tiene acceso a tenant B.
    
    Axioma AUP: Aislamiento estricto entre tenants.
    """
    # Arrange
    msp = MSP(msp_id="msp_005", nombre="MSP Test 5")
    db_core_session.add(msp)
    
    condo_a = Condominio(
        condominio_id="condo_a",
        msp_id="msp_005",
        nombre="Condominio A",
    )
    condo_b = Condominio(
        condominio_id="condo_b",
        msp_id="msp_005",
        nombre="Condominio B",
    )
    db_core_session.add_all([condo_a, condo_b])
    
    usuario = Usuario(
        usuario_id="user_005",
        nombre="Test",
        email="test5@example.com",
        password_hash="hashed_password",
        rol="ADMIN",
        condominio_id="condo_a",
    )
    db_core_session.add(usuario)
    
    # Scope solo en condo_a
    scope_a = UserTenantScope(
        usuario_id="user_005",
        tenant_id="condo_a",
        access_level=AccessLevel.ADMIN_CONDOMINIO,
        estado=ScopeStatus.ACTIVO
    )
    db_core_session.add(scope_a)
    db_core_session.commit()
    
    # Act
    tiene_acceso_a = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_a",
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    tiene_acceso_b = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_b",
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    # Assert
    assert tiene_acceso_a is True
    assert tiene_acceso_b is False  # ← Aislamiento estricto


def test_usuario_multitenant_acceso_correcto(db_core_session):
    """
    Test: Usuario con SCOPE en múltiples tenants puede acceder a ambos.
    """
    # Arrange
    msp = MSP(msp_id="msp_006", nombre="MSP Test 6")
    db_core_session.add(msp)
    
    condo_x = Condominio(
        condominio_id="condo_x",
        msp_id="msp_006",
        nombre="Condominio X",
    )
    condo_y = Condominio(
        condominio_id="condo_y",
        msp_id="msp_006",
        nombre="Condominio Y",
    )
    db_core_session.add_all([condo_x, condo_y])
    
    usuario = Usuario(
        usuario_id="user_006",
        nombre="Test",
        email="test6@example.com",
        password_hash="hashed_password",
        rol="SUPER_ADMIN",
        condominio_id="condo_x",
    )
    db_core_session.add(usuario)
    
    # Scopes en ambos condominios
    scope_x = UserTenantScope(
        usuario_id="user_006",
        tenant_id="condo_x",
        access_level=AccessLevel.ADMIN_CONDOMINIO,
        estado=ScopeStatus.ACTIVO
    )
    scope_y = UserTenantScope(
        usuario_id="user_006",
        tenant_id="condo_y",
        access_level=AccessLevel.ADMIN_CONDOMINIO,
        estado=ScopeStatus.ACTIVO
    )
    db_core_session.add_all([scope_x, scope_y])
    db_core_session.commit()
    
    # Act
    tiene_acceso_x = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_x",
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    tiene_acceso_y = validar_scope(
        db=db_core_session,
        usuario=usuario,
        tenant_id="condo_y",
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    # Assert
    assert tiene_acceso_x is True
    assert tiene_acceso_y is True


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

def test_msp_admin_acceso_global(db_core_session):
    """
    Test: MSP_ADMIN con nivel MSP_ADMIN tiene acceso superior a todos.
    """
    # Arrange - verificar que MSP_ADMIN es el nivel más alto
    nivel_msp_admin = ACCESS_LEVEL_HIERARCHY[AccessLevel.MSP_ADMIN]
    
    # Assert
    assert nivel_msp_admin == 100  # Máximo valor
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.ADMIN_CONDOMINIO) is True
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.GUARDIA) is True
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.RESIDENTE) is True
    assert nivel_suficiente(AccessLevel.MSP_ADMIN, AccessLevel.LECTURA) is True
