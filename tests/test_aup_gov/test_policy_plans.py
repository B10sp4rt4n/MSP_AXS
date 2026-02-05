"""
Tests para AUP_GOV - Policy & Plans (Políticas y Planes Comerciales)

Módulos bajo test:
- backend.core.gov.policy
- backend.core.gov.plans

Funcionalidad probada:
- crear_policy() - Crear políticas de gobierno
- obtener_policies() - Query de políticas aplicables
- evaluar_politica() - Evaluador central policy-first
- crear_politicas_para_plan() - Composición de planes comerciales
- PLAN_POLICIES - Definiciones de planes FREE/PRO/ENTERPRISE

Axiomas AUP_GOV probados:
1. Política precede a operación (policy-first) ✓
2. Sin política → denegado (safe by default) ✓
3. Planes son composiciones de políticas ✓
4. Revocación inmediata ✓
"""

import pytest
from datetime import datetime, timedelta
from backend.core.gov.policy import (
    crear_policy,
    obtener_policies,
    evaluar_politica,
)
from backend.core.gov.plans import (
    PlanType,
    PLAN_POLICIES,
    crear_politicas_para_plan,
)
from backend.db.gov import Policy, PolicyScope, GovStatus


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Crear Políticas
# ═══════════════════════════════════════════════════════════════════════════

def test_crear_policy_global_valida(db_gov_session):
    """
    Test: Crear una política GLOBAL con límites estructurales.
    """
    # Act
    policy = crear_policy(
        db=db_gov_session,
        nombre="Límite Global de Tenants",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_tenant",
        limites={"max_count": 5},
        metadata={"plan": "FREE"}
    )
    
    # Assert
    assert policy is not None
    assert policy.policy_id.startswith("pol_")
    assert policy.nombre == "Límite Global de Tenants"
    assert policy.ambito == PolicyScope.GLOBAL
    assert policy.accion_objetivo == "crear_tenant"
    assert policy.limites == {"max_count": 5}
    assert policy.estado == GovStatus.ACTIVO
    assert policy.target_tenant_id is None  # GLOBAL no tiene tenant
    assert policy.metadata_json == {"plan": "FREE"}
    assert policy.valida_desde is not None


def test_crear_policy_tenant_requiere_target_tenant_id(db_gov_session):
    """
    Test: Política TENANT sin target_tenant_id falla (validación estructural).
    
    Axioma: TENANT policy requiere target_tenant_id.
    """
    # Act & Assert
    with pytest.raises(ValueError, match="TENANT policy requiere target_tenant_id"):
        crear_policy(
            db=db_gov_session,
            nombre="Política de Tenant sin ID",
            ambito=PolicyScope.TENANT,
            accion_objetivo="generar_qr",
            limites={"max_dias_vigencia": 7},
            target_tenant_id=None  # ← Error: TENANT sin target
        )


def test_crear_policy_global_no_debe_tener_target_tenant_id(db_gov_session):
    """
    Test: Política GLOBAL con target_tenant_id falla (validación estructural).
    
    Axioma: GLOBAL policy no debe tener target_tenant_id.
    """
    # Act & Assert
    with pytest.raises(ValueError, match="GLOBAL policy no debe tener target_tenant_id"):
        crear_policy(
            db=db_gov_session,
            nombre="Política Global con Tenant",
            ambito=PolicyScope.GLOBAL,
            accion_objetivo="crear_usuario",
            limites={"max_count": 100},
            target_tenant_id="tenant_001"  # ← Error: GLOBAL con tenant
        )


def test_crear_policy_tenant_valida(db_gov_session):
    """
    Test: Crear una política TENANT con target_tenant_id correcto.
    """
    # Act
    policy = crear_policy(
        db=db_gov_session,
        nombre="QR Vigencia Condominio A",
        ambito=PolicyScope.TENANT,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": 7},
        target_tenant_id="condo_001",
        metadata={"condominio": "Torre Norte"}
    )
    
    # Assert
    assert policy is not None
    assert policy.ambito == PolicyScope.TENANT
    assert policy.target_tenant_id == "condo_001"
    assert policy.limites == {"max_dias_vigencia": 7}


def test_crear_policy_con_vigencia_temporal(db_gov_session):
    """
    Test: Crear política con fechas de vigencia (valida_desde, valida_hasta).
    """
    # Arrange
    ahora = datetime.utcnow()
    en_30_dias = ahora + timedelta(days=30)
    
    # Act
    policy = crear_policy(
        db=db_gov_session,
        nombre="Promoción Temporal",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_visita",
        limites={"max_count": 1000},
        valida_desde=ahora,
        valida_hasta=en_30_dias,
        metadata={"promo": "Black Friday"}
    )
    
    # Assert
    assert policy.valida_desde == ahora
    assert policy.valida_hasta == en_30_dias
    assert (policy.valida_hasta - policy.valida_desde).days == 30


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Obtener Políticas
# ═══════════════════════════════════════════════════════════════════════════

def test_obtener_policies_por_accion(db_gov_session):
    """
    Test: Obtener políticas aplicables a una acción específica.
    """
    # Arrange: Crear varias políticas
    crear_policy(
        db=db_gov_session,
        nombre="QR Global",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": 30}
    )
    
    crear_policy(
        db=db_gov_session,
        nombre="Tenants Global",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_tenant",
        limites={"max_count": 10}
    )
    
    crear_policy(
        db=db_gov_session,
        nombre="QR Tenant A",
        ambito=PolicyScope.TENANT,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": 7},
        target_tenant_id="tenant_a"
    )
    
    # Act: Buscar políticas de "generar_qr"
    policies_qr = obtener_policies(
        db=db_gov_session,
        accion_objetivo="generar_qr"
    )
    
    # Assert
    assert len(policies_qr) == 2  # QR Global + QR Tenant A
    assert all(p.accion_objetivo == "generar_qr" for p in policies_qr)
    # Debe estar ordenado: TENANT primero
    assert policies_qr[0].ambito == PolicyScope.TENANT
    assert policies_qr[1].ambito == PolicyScope.GLOBAL


def test_obtener_policies_por_tenant_incluye_global(db_gov_session):
    """
    Test: Al filtrar por tenant, obtiene políticas TENANT + GLOBAL.
    
    Axioma: Políticas GLOBAL aplican a todos los tenants.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Usuarios Global",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_usuario",
        limites={"max_count": 100}
    )
    
    crear_policy(
        db=db_gov_session,
        nombre="Usuarios Tenant A",
        ambito=PolicyScope.TENANT,
        accion_objetivo="crear_usuario",
        limites={"max_count": 50},
        target_tenant_id="tenant_a"
    )
    
    crear_policy(
        db=db_gov_session,
        nombre="Usuarios Tenant B",
        ambito=PolicyScope.TENANT,
        accion_objetivo="crear_usuario",
        limites={"max_count": 20},
        target_tenant_id="tenant_b"
    )
    
    # Act: Buscar políticas de "crear_usuario" para tenant_a
    policies = obtener_policies(
        db=db_gov_session,
        accion_objetivo="crear_usuario",
        tenant_id="tenant_a"
    )
    
    # Assert: Debe obtener GLOBAL + tenant_a (NO tenant_b)
    assert len(policies) == 2
    assert any(p.ambito == PolicyScope.GLOBAL for p in policies)
    assert any(p.target_tenant_id == "tenant_a" for p in policies)
    assert not any(p.target_tenant_id == "tenant_b" for p in policies)


def test_obtener_policies_solo_activas(db_gov_session):
    """
    Test: Solo obtiene políticas ACTIVAS (no revocadas ni suspendidas).
    """
    # Arrange
    policy_activa = crear_policy(
        db=db_gov_session,
        nombre="Activa",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_visita",
        limites={"max_count": 100}
    )
    
    policy_revocada = crear_policy(
        db=db_gov_session,
        nombre="Revocada",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_visita",
        limites={"max_count": 50}
    )
    
    # Revocar segunda política
    policy_revocada.estado = GovStatus.REVOCADO
    db_gov_session.commit()
    
    # Act
    policies = obtener_policies(
        db=db_gov_session,
        accion_objetivo="crear_visita",
        estado=GovStatus.ACTIVO
    )
    
    # Assert
    assert len(policies) == 1
    assert policies[0].nombre == "Activa"
    assert policies[0].estado == GovStatus.ACTIVO


def test_obtener_policies_respeta_vigencia_temporal(db_gov_session):
    """
    Test: Solo obtiene políticas vigentes (dentro de valida_desde/valida_hasta).
    """
    # Arrange
    ahora = datetime.utcnow()
    hace_1_dia = ahora - timedelta(days=1)
    en_1_dia = ahora + timedelta(days=1)
    
    # Política vigente (ya empezó, no ha terminado)
    crear_policy(
        db=db_gov_session,
        nombre="Política Vigente",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_qr",
        limites={"max_count": 10},
        valida_desde=hace_1_dia,
        valida_hasta=en_1_dia
    )
    
    # Política futura (aún no empezó)
    crear_policy(
        db=db_gov_session,
        nombre="Política Futura",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_qr",
        limites={"max_count": 5},
        valida_desde=en_1_dia,  # Empieza mañana
        valida_hasta=None
    )
    
    # Política expirada (ya terminó)
    crear_policy(
        db=db_gov_session,
        nombre="Política Expirada",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_qr",
        limites={"max_count": 20},
        valida_desde=hace_1_dia - timedelta(days=30),
        valida_hasta=hace_1_dia  # Terminó ayer
    )
    
    # Act
    policies = obtener_policies(
        db=db_gov_session,
        accion_objetivo="crear_qr"
    )
    
    # Assert: Solo debe retornar la política vigente
    assert len(policies) == 1
    assert policies[0].nombre == "Política Vigente"


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Evaluar Políticas
# ═══════════════════════════════════════════════════════════════════════════

def test_evaluar_politica_dentro_del_limite(db_gov_session):
    """
    Test: Evaluar política con valor dentro del límite → PERMITIDO.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Max 5 Tenants",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_tenant",
        limites={"max_count": 5}
    )
    
    # Act: Usuario tiene 3 tenants, límite es 5
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="crear_tenant",
        valor_actual=3
    )
    
    # Assert
    assert permitido is True
    assert motivo == "Acción permitida por políticas"


def test_evaluar_politica_limite_excedido(db_gov_session):
    """
    Test: Evaluar política con valor que excede límite → DENEGADO.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Max 5 Tenants",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_tenant",
        limites={"max_count": 5}
    )
    
    # Act: Usuario tiene 5 tenants, quiere crear 6to
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="crear_tenant",
        valor_actual=5  # Ya llegó al límite
    )
    
    # Assert
    assert permitido is False
    assert "Límite excedido" in motivo
    assert "5" in motivo


def test_evaluar_politica_sin_politica_definida_deniega(db_gov_session):
    """
    Test: Evaluar acción sin política definida → DENEGADO (safe by default).
    
    Axioma AUP_GOV: Sin política → denegado.
    """
    # Arrange: NO crear ninguna política
    
    # Act
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="accion_sin_politica"
    )
    
    # Assert
    assert permitido is False
    assert "No hay política definida" in motivo


def test_evaluar_politica_tenant_especifica_tiene_prioridad(db_gov_session):
    """
    Test: Política TENANT tiene prioridad sobre GLOBAL.
    """
    # Arrange
    # Global: permite hasta 100 usuarios
    crear_policy(
        db=db_gov_session,
        nombre="Usuarios Global",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_usuario",
        limites={"max_count": 100}
    )
    
    # Tenant A: solo permite 20 usuarios (más restrictivo)
    crear_policy(
        db=db_gov_session,
        nombre="Usuarios Tenant A",
        ambito=PolicyScope.TENANT,
        accion_objetivo="crear_usuario",
        limites={"max_count": 20},
        target_tenant_id="tenant_a"
    )
    
    # Act: Evaluar para tenant_a con 25 usuarios actuales
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="crear_usuario",
        tenant_id="tenant_a",
        valor_actual=20  # Llegó al límite del tenant
    )
    
    # Assert: Debe denegar por límite de tenant (20), no por global (100)
    assert permitido is False
    assert "20" in motivo  # Límite de tenant


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Planes Comerciales
# ═══════════════════════════════════════════════════════════════════════════

def test_plan_policies_definiciones():
    """
    Test: PLAN_POLICIES tiene definiciones correctas para FREE, PRO, ENTERPRISE.
    """
    # Assert FREE
    assert PlanType.FREE in PLAN_POLICIES
    assert PLAN_POLICIES[PlanType.FREE]["max_tenants"] == 1
    assert PLAN_POLICIES[PlanType.FREE]["max_usuarios"] == 20
    assert PLAN_POLICIES[PlanType.FREE]["delegacion_permitida"] is False
    
    # Assert PRO
    assert PlanType.PRO in PLAN_POLICIES
    assert PLAN_POLICIES[PlanType.PRO]["max_tenants"] == 5
    assert PLAN_POLICIES[PlanType.PRO]["max_usuarios"] == 100
    assert PLAN_POLICIES[PlanType.PRO]["delegacion_permitida"] is True
    
    # Assert ENTERPRISE
    assert PlanType.ENTERPRISE in PLAN_POLICIES
    assert PLAN_POLICIES[PlanType.ENTERPRISE]["max_tenants"] == 50
    assert PLAN_POLICIES[PlanType.ENTERPRISE]["max_usuarios"] == 1000


def test_crear_politicas_para_plan_free(db_gov_session):
    """
    Test: Crear políticas para Plan FREE.
    
    Debe crear 5 políticas: tenants, usuarios, qr, visitas, no_delegacion.
    """
    # Act
    policies = crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.FREE,
        target_identity_id="user_001"
    )
    
    # Assert
    assert len(policies) == 5
    
    # Verificar política de tenants
    policy_tenants = next(p for p in policies if p.accion_objetivo == "crear_tenant")
    assert policy_tenants.limites["max_count"] == 1
    
    # Verificar política de usuarios
    policy_usuarios = next(p for p in policies if p.accion_objetivo == "crear_usuario")
    assert policy_usuarios.limites["max_usuarios"] == 20
    
    # Verificar política de QR
    policy_qr = next(p for p in policies if p.accion_objetivo == "generar_qr")
    assert policy_qr.limites["max_dias_vigencia"] == 3
    
    # Verificar política de visitas
    policy_visitas = next(p for p in policies if p.accion_objetivo == "crear_visita")
    assert policy_visitas.limites["max_count"] == 50
    
    # Verificar política de delegación (bloqueada)
    policy_delegacion = next(p for p in policies if p.accion_objetivo == "delegar_poder")
    assert policy_delegacion.limites["max_count"] == 0  # FREE no permite delegación


def test_crear_politicas_para_plan_pro(db_gov_session):
    """
    Test: Crear políticas para Plan PRO.
    
    Plan PRO permite delegación con límite de 30 días.
    """
    # Act
    policies = crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.PRO,
        target_identity_id="user_002"
    )
    
    # Assert
    assert len(policies) == 5
    
    # Verificar límites PRO
    policy_tenants = next(p for p in policies if p.accion_objetivo == "crear_tenant")
    assert policy_tenants.limites["max_count"] == 5
    
    policy_usuarios = next(p for p in policies if p.accion_objetivo == "crear_usuario")
    assert policy_usuarios.limites["max_usuarios"] == 100
    
    # Verificar delegación permitida
    policy_delegacion = next(p for p in policies if p.accion_objetivo == "delegar_poder")
    assert policy_delegacion.limites["max_dias_vigencia"] == 30


def test_crear_politicas_para_plan_enterprise(db_gov_session):
    """
    Test: Crear políticas para Plan ENTERPRISE.
    
    Plan ENTERPRISE tiene límites más altos.
    """
    # Act
    policies = crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.ENTERPRISE,
        target_identity_id="user_003"
    )
    
    # Assert
    assert len(policies) == 5
    
    # Verificar límites ENTERPRISE
    policy_tenants = next(p for p in policies if p.accion_objetivo == "crear_tenant")
    assert policy_tenants.limites["max_count"] == 50
    
    policy_usuarios = next(p for p in policies if p.accion_objetivo == "crear_usuario")
    assert policy_usuarios.limites["max_usuarios"] == 1000
    
    policy_qr = next(p for p in policies if p.accion_objetivo == "generar_qr")
    assert policy_qr.limites["max_dias_vigencia"] == 30
    
    policy_delegacion = next(p for p in policies if p.accion_objetivo == "delegar_poder")
    assert policy_delegacion.limites["max_dias_vigencia"] == 365


def test_crear_politicas_para_plan_metadata_correcta(db_gov_session):
    """
    Test: Políticas creadas tienen metadata correcta con plan_type y target_identity.
    """
    # Act
    policies = crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.PRO,
        target_identity_id="user_pro_001"
    )
    
    # Assert: Todas las políticas tienen metadata correcta
    for policy in policies:
        assert policy.metadata_json is not None
        assert policy.metadata_json["plan_type"] == "pro"
        assert policy.metadata_json["target_identity"] == "user_pro_001"
        assert "descripcion" in policy.metadata_json


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Axiomas AUP_GOV
# ═══════════════════════════════════════════════════════════════════════════

def test_axioma_policy_first_sin_politica_deniega(db_gov_session):
    """
    Test: Axioma AUP_GOV - Sin política definida → denegado (policy-first).
    """
    # Act: Intentar acción sin política
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="accion_no_definida"
    )
    
    # Assert
    assert permitido is False
    assert "No hay política" in motivo


def test_axioma_planes_son_composiciones_de_politicas(db_gov_session):
    """
    Test: Axioma AUPGOV - Un plan es una composición de políticas, nada más.
    
    Cambiar de plan = cambiar políticas (NO código).
    """
    # Arrange: Usuario con Plan FREE
    policies_free = crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.FREE,
        target_identity_id="user_downgrade"
    )
    
    # Assert: Plan FREE tiene 5 políticas
    assert len(policies_free) == 5
    
    # Act: Revocar políticas FREE (downgrade)
    for policy in policies_free:
        policy.estado = GovStatus.REVOCADO
    db_gov_session.commit()
    
    # Upgrade a PRO
    policies_pro = crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.PRO,
        target_identity_id="user_downgrade"
    )
    
    # Assert: Ahora tiene políticas PRO
    assert len(policies_pro) == 5
    
    # Verificar que políticas cambiaron
    policy_tenants_pro = next(p for p in policies_pro if p.accion_objetivo == "crear_tenant")
    assert policy_tenants_pro.limites["max_count"] == 5  # PRO permite 5 tenants
    assert policy_tenants_pro.estado == GovStatus.ACTIVO


def test_axioma_revocacion_inmediata(db_gov_session):
    """
    Test: Axioma AUP_GOV - Revocación es inmediata (sin cache).
    """
    # Arrange: Crear política activa
    policy = crear_policy(
        db=db_gov_session,
        nombre="Política Revocable",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_test",
        limites={"max_count": 10}
    )
    
    # Act 1: Evaluar mientras está activa
    permitido_antes, _ = evaluar_politica(
        db=db_gov_session,
        accion="crear_test",
        valor_actual=5
    )
    
    # Assert: Debe permitir (está activa)
    assert permitido_antes is True
    
    # Act 2: Revocar política
    policy.estado = GovStatus.REVOCADO
    db_gov_session.commit()
    
    # Act 3: Evaluar inmediatamente después de revocar
    permitido_despues, motivo = evaluar_politica(
        db=db_gov_session,
        accion="crear_test",
        valor_actual=5
    )
    
    # Assert: Debe denegar (revocada inmediatamente)
    assert permitido_despues is False
    assert "No hay política" in motivo  # Ya no hay política activa


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Evaluación de Políticas - Casos adicionales
# ═══════════════════════════════════════════════════════════════════════════

def test_evaluar_politica_max_dias_vigencia_permitido(db_gov_session):
    """
    Test: Evaluar política con max_dias_vigencia dentro del límite.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Límite QR 7 días",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": 7}
    )
    
    # Act: Solicitar QR con 5 días de vigencia
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="generar_qr",
        metadata={"dias_vigencia": 5}
    )
    
    # Assert
    assert permitido is True
    assert "permitida" in motivo.lower()


def test_evaluar_politica_max_dias_vigencia_excedido(db_gov_session):
    """
    Test: Evaluar política con max_dias_vigencia excedido.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Límite QR 7 días",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": 7}
    )
    
    # Act: Solicitar QR con 10 días de vigencia (excede límite)
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="generar_qr",
        metadata={"dias_vigencia": 10}
    )
    
    # Assert
    assert permitido is False
    assert "Vigencia excedida" in motivo
    assert "máximo 7 días" in motivo


def test_evaluar_politica_max_usuarios_permitido(db_gov_session):
    """
    Test: Evaluar política con max_usuarios dentro del límite.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Límite Usuarios Tenant",
        ambito=PolicyScope.TENANT,
        target_tenant_id="tenant_001",
        accion_objetivo="crear_usuario",
        limites={"max_usuarios": 50}
    )
    
    # Act: Crear usuario cuando hay 30 actuales
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="crear_usuario",
        tenant_id="tenant_001",
        valor_actual=30
    )
    
    # Assert
    assert permitido is True
    assert "permitida" in motivo.lower()


def test_evaluar_politica_max_usuarios_excedido(db_gov_session):
    """
    Test: Evaluar política con max_usuarios excedido.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Límite Usuarios Tenant",
        ambito=PolicyScope.TENANT,
        target_tenant_id="tenant_001",
        accion_objetivo="crear_usuario",
        limites={"max_usuarios": 50}
    )
    
    # Act: Crear usuario cuando ya hay 50 (límite alcanzado)
    permitido, motivo = evaluar_politica(
        db=db_gov_session,
        accion="crear_usuario",
        tenant_id="tenant_001",
        valor_actual=50
    )
    
    # Assert
    assert permitido is False
    assert "Límite de usuarios excedido" in motivo
    assert "máximo 50" in motivo


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Revocar Políticas
# ═══════════════════════════════════════════════════════════════════════════

def test_revocar_policy_exitoso(db_gov_session):
    """
    Test: Revocar una política existente y verificar estado REVOCADO.
    """
    from backend.core.gov.policy import revocar_policy
    
    # Arrange: Crear política activa
    policy = crear_policy(
        db=db_gov_session,
        nombre="Política a Revocar",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="test_accion",
        limites={"max_count": 10}
    )
    
    assert policy.estado == GovStatus.ACTIVO
    
    # Act: Revocar política
    policy_revocada = revocar_policy(
        db=db_gov_session,
        policy_id=policy.policy_id,
        revocada_por="admin_001",
        motivo="Cambio de plan comercial"
    )
    
    # Assert
    assert policy_revocada.estado == GovStatus.REVOCADO
    assert policy_revocada.metadata_json["revoked_by"] == "admin_001"
    assert policy_revocada.metadata_json["revoked_reason"] == "Cambio de plan comercial"
    assert "revoked_at" in policy_revocada.metadata_json


def test_revocar_policy_no_encontrada(db_gov_session):
    """
    Test: Revocar política que no existe debe lanzar HTTPException 404.
    """
    from backend.core.gov.policy import revocar_policy
    from fastapi import HTTPException
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        revocar_policy(
            db=db_gov_session,
            policy_id="pol_inexistente",
            revocada_por="admin_001"
        )
    
    assert exc_info.value.status_code == 404
    assert "pol_inexistente" in str(exc_info.value.detail)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Listar Políticas
# ═══════════════════════════════════════════════════════════════════════════

def test_listar_policies_sin_filtros(db_gov_session):
    """
    Test: Listar todas las políticas activas sin filtros.
    """
    from backend.core.gov.policy import listar_policies
    
    # Arrange: Crear varias políticas
    crear_policy(
        db=db_gov_session,
        nombre="Policy 1",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="accion_1",
        limites={"max_count": 10}
    )
    crear_policy(
        db=db_gov_session,
        nombre="Policy 2",
        ambito=PolicyScope.TENANT,
        target_tenant_id="tenant_001",
        accion_objetivo="accion_2",
        limites={"max_count": 5}
    )
    
    # Act: Listar todas las políticas activas
    policies = listar_policies(db=db_gov_session)
    
    # Assert
    assert len(policies) >= 2
    assert all(p.estado == GovStatus.ACTIVO for p in policies)


def test_listar_policies_filtro_ambito(db_gov_session):
    """
    Test: Listar políticas filtradas por ámbito.
    """
    from backend.core.gov.policy import listar_policies
    
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Global Policy",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="accion_global",
        limites={"max_count": 100}
    )
    crear_policy(
        db=db_gov_session,
        nombre="Tenant Policy",
        ambito=PolicyScope.TENANT,
        target_tenant_id="tenant_001",
        accion_objetivo="accion_tenant",
        limites={"max_count": 10}
    )
    
    # Act: Listar solo políticas GLOBAL
    policies_global = listar_policies(
        db=db_gov_session,
        ambito=PolicyScope.GLOBAL
    )
    
    # Assert
    assert len(policies_global) >= 1
    assert all(p.ambito == PolicyScope.GLOBAL for p in policies_global)


def test_listar_policies_filtro_accion_objetivo(db_gov_session):
    """
    Test: Listar políticas filtradas por acción objetivo.
    """
    from backend.core.gov.policy import listar_policies
    
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Policy Accion X",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="accion_x",
        limites={"max_count": 10}
    )
    crear_policy(
        db=db_gov_session,
        nombre="Policy Accion Y",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="accion_y",
        limites={"max_count": 20}
    )
    
    # Act: Listar solo políticas para accion_x
    policies = listar_policies(
        db=db_gov_session,
        accion_objetivo="accion_x"
    )
    
    # Assert
    assert len(policies) >= 1
    assert all(p.accion_objetivo == "accion_x" for p in policies)


def test_obtener_policies_filtro_ambito(db_gov_session):
    """
    Test: obtener_policies con filtro por ámbito específico.
    """
    # Arrange
    crear_policy(
        db=db_gov_session,
        nombre="Global Policy",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="test_accion",
        limites={"max_count": 100}
    )
    crear_policy(
        db=db_gov_session,
        nombre="Tenant Policy",
        ambito=PolicyScope.TENANT,
        target_tenant_id="tenant_001",
        accion_objetivo="test_accion",
        limites={"max_count": 10}
    )
    
    # Act: Obtener solo políticas TENANT
    policies = obtener_policies(
        db=db_gov_session,
        accion_objetivo="test_accion",
        ambito=PolicyScope.TENANT
    )
    
    # Assert
    assert len(policies) >= 1
    assert all(p.ambito == PolicyScope.TENANT for p in policies)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Asignar Plan con Evento
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_asignar_plan_con_evento_crea_evento(db_gov_session, db_session, db_event_session):
    """
    Test: asignar_plan_con_evento registra evento AUP_EVENT.
    """
    from backend.core.gov.plans import asignar_plan_con_evento
    from backend.db.core.models import Usuario
    from backend.db.event import Event
    
    # Arrange: Crear usuarios
    admin = Usuario(
        usuario_id="admin_001",
        email="admin@test.com",
        nombre="Admin",
        apellido="Test",
        rol="ADMIN",
        hashed_password="hash"
    )
    target = Usuario(
        usuario_id="user_001",
        email="user@test.com",
        nombre="User",
        apellido="Test",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    db_session.add_all([admin, target])
    db_session.commit()
    
    # Act: Asignar plan con evento
    policies, summary = asignar_plan_con_evento(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_token_admin",
        target_user=target,
        plan_type=PlanType.PRO,
        tenant_id="tenant_test"
    )
    
    # Assert: Evento registrado
    eventos = db_event_session.query(Event).filter(
        Event.identity_id == admin.usuario_id
    ).all()
    
    assert len(eventos) >= 1
    evento = eventos[-1]  # Último evento
    assert evento.accion == "asignar"
    assert "plan_change" in evento.entidad_id
    assert evento.resultado == "exito"


@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_asignar_plan_con_evento_revoca_plan_anterior(db_gov_session, db_session, db_event_session):
    """
    Test: asignar_plan_con_evento revoca políticas del plan anterior.
    """
    from backend.core.gov.plans import asignar_plan_con_evento, crear_politicas_para_plan
    from backend.db.core.models import Usuario
    
    # Arrange: Usuario con plan Free existente
    user = Usuario(
        usuario_id="user_002",
        email="user2@test.com",
        nombre="User",
        apellido="Two",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_002",
        email="admin2@test.com",
        nombre="Admin",
        apellido="Two",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    # Crear plan Free inicial
    policies_free = crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.FREE,
        target_identity_id=user.usuario_id
    )
    assert all(p.estado == GovStatus.ACTIVO for p in policies_free)
    
    # Act: Cambiar a plan Pro
    policies_pro, summary = asignar_plan_con_evento(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user,
        plan_type=PlanType.PRO
    )
    
    # Assert: Políticas Free revocadas
    db_gov_session.refresh(policies_free[0])
    assert all(p.estado == GovStatus.REVOCADO for p in policies_free)
    
    # Assert: Summary correcto
    assert summary["plan_anterior"] == "free"
    assert summary["plan_nuevo"] == "pro"
    assert summary["politicas_revocadas"] >= 5


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Obtener Plan Actual
# ═══════════════════════════════════════════════════════════════════════════

def test_obtener_plan_actual_sin_plan(db_gov_session):
    """
    Test: obtener_plan_actual retorna None si usuario no tiene plan.
    """
    from backend.core.gov.plans import obtener_plan_actual
    
    # Act
    plan = obtener_plan_actual(db=db_gov_session, usuario_id="usuario_sin_plan")
    
    # Assert
    assert plan is None


def test_obtener_plan_actual_con_plan_activo(db_gov_session):
    """
    Test: obtener_plan_actual retorna plan si usuario tiene políticas activas.
    """
    from backend.core.gov.plans import obtener_plan_actual, crear_politicas_para_plan
    
    # Arrange: Crear plan Pro para usuario
    usuario_id = "user_plan_test"
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.PRO,
        target_identity_id=usuario_id
    )
    
    # Act
    plan = obtener_plan_actual(db=db_gov_session, usuario_id=usuario_id)
    
    # Assert
    assert plan is not None
    assert plan["plan_type"] == "pro"
    assert plan["politicas_activas"] >= 5
    assert "max_tenants" in plan["limites"]


def test_obtener_plan_actual_extrae_limites_correctamente(db_gov_session):
    """
    Test: obtener_plan_actual extrae límites de políticas correctamente.
    """
    from backend.core.gov.plans import obtener_plan_actual, crear_politicas_para_plan
    
    # Arrange
    usuario_id = "user_limites_test"
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.ENTERPRISE,
        target_identity_id=usuario_id
    )
    
    # Act
    plan = obtener_plan_actual(db=db_gov_session, usuario_id=usuario_id)
    
    # Assert
    limites = plan["limites"]
    assert limites["max_tenants"] == 50  # Enterprise
    assert limites["max_usuarios"] == 1000
    assert limites["max_qr_vigencia"] == 30
    assert limites["max_visitas_mes"] == 10000


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Upgrade Plan
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_upgrade_plan_de_free_a_pro(db_gov_session, db_session, db_event_session):
    """
    Test: upgrade_plan de FREE a PRO.
    """
    from backend.core.gov.plans import upgrade_plan, crear_politicas_para_plan
    from backend.db.core.models import Usuario
    
    # Arrange: Usuario con plan Free
    user = Usuario(
        usuario_id="user_upgrade_1",
        email="upgrade1@test.com",
        nombre="Upgrade",
        apellido="One",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_upgrade_1",
        email="admin_upgrade1@test.com",
        nombre="Admin",
        apellido="Upgrade",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.FREE,
        target_identity_id=user.usuario_id
    )
    
    # Act: Upgrade
    result = upgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "upgrade_exitoso"
    assert result["plan_anterior"] == "free"
    assert result["plan_nuevo"] == "pro"


@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_upgrade_plan_de_pro_a_enterprise(db_gov_session, db_session, db_event_session):
    """
    Test: upgrade_plan de PRO a ENTERPRISE.
    """
    from backend.core.gov.plans import upgrade_plan, crear_politicas_para_plan
    from backend.db.core.models import Usuario
    
    # Arrange
    user = Usuario(
        usuario_id="user_upgrade_2",
        email="upgrade2@test.com",
        nombre="Upgrade",
        apellido="Two",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_upgrade_2",
        email="admin_upgrade2@test.com",
        nombre="Admin",
        apellido="Two",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.PRO,
        target_identity_id=user.usuario_id
    )
    
    # Act
    result = upgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "upgrade_exitoso"
    assert result["plan_anterior"] == "pro"
    assert result["plan_nuevo"] == "enterprise"


@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_upgrade_plan_sin_plan_asigna_free(db_gov_session, db_session, db_event_session):
    """
    Test: upgrade_plan sin plan previo asigna FREE.
    """
    from backend.core.gov.plans import upgrade_plan
    from backend.db.core.models import Usuario
    
    # Arrange: Usuario sin plan
    user = Usuario(
        usuario_id="user_upgrade_3",
        email="upgrade3@test.com",
        nombre="Upgrade",
        apellido="Three",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_upgrade_3",
        email="admin_upgrade3@test.com",
        nombre="Admin",
        apellido="Three",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    # Act
    result = upgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "upgrade_exitoso"
    assert result["plan_nuevo"] == "free"


@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_upgrade_plan_ya_en_enterprise(db_gov_session, db_session, db_event_session):
    """
    Test: upgrade_plan estando en ENTERPRISE no hace nada.
    """
    from backend.core.gov.plans import upgrade_plan, crear_politicas_para_plan
    from backend.db.core.models import Usuario
    
    # Arrange: Usuario con Enterprise
    user = Usuario(
        usuario_id="user_upgrade_4",
        email="upgrade4@test.com",
        nombre="Upgrade",
        apellido="Four",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_upgrade_4",
        email="admin_upgrade4@test.com",
        nombre="Admin",
        apellido="Four",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.ENTERPRISE,
        target_identity_id=user.usuario_id
    )
    
    # Act
    result = upgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "ya_en_plan_maximo"
    assert result["plan_actual"] == "enterprise"


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Downgrade Plan
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_downgrade_plan_de_enterprise_a_pro(db_gov_session, db_session, db_event_session):
    """
    Test: downgrade_plan de ENTERPRISE a PRO.
    """
    from backend.core.gov.plans import downgrade_plan, crear_politicas_para_plan
    from backend.db.core.models import Usuario
    
    # Arrange
    user = Usuario(
        usuario_id="user_downgrade_1",
        email="downgrade1@test.com",
        nombre="Downgrade",
        apellido="One",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_downgrade_1",
        email="admin_downgrade1@test.com",
        nombre="Admin",
        apellido="One",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.ENTERPRISE,
        target_identity_id=user.usuario_id
    )
    
    # Act
    result = downgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "downgrade_inmediato"
    assert result["plan_anterior"] == "enterprise"
    assert result["plan_nuevo"] == "pro"


@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_downgrade_plan_de_pro_a_free(db_gov_session, db_session, db_event_session):
    """
    Test: downgrade_plan de PRO a FREE.
    """
    from backend.core.gov.plans import downgrade_plan, crear_politicas_para_plan
    from backend.db.core.models import Usuario
    
    # Arrange
    user = Usuario(
        usuario_id="user_downgrade_2",
        email="downgrade2@test.com",
        nombre="Downgrade",
        apellido="Two",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_downgrade_2",
        email="admin_downgrade2@test.com",
        nombre="Admin",
        apellido="Two",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.PRO,
        target_identity_id=user.usuario_id
    )
    
    # Act
    result = downgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "downgrade_inmediato"
    assert result["plan_anterior"] == "pro"
    assert result["plan_nuevo"] == "free"


@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_downgrade_plan_ya_en_free(db_gov_session, db_session, db_event_session):
    """
    Test: downgrade_plan estando en FREE no hace nada.
    """
    from backend.core.gov.plans import downgrade_plan, crear_politicas_para_plan
    from backend.db.core.models import Usuario
    
    # Arrange
    user = Usuario(
        usuario_id="user_downgrade_3",
        email="downgrade3@test.com",
        nombre="Downgrade",
        apellido="Three",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_downgrade_3",
        email="admin_downgrade3@test.com",
        nombre="Admin",
        apellido="Three",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    crear_politicas_para_plan(
        db=db_gov_session,
        plan_type=PlanType.FREE,
        target_identity_id=user.usuario_id
    )
    
    # Act
    result = downgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "ya_en_plan_minimo"
    assert result["plan_actual"] == "free"


@pytest.mark.skip(reason="Requiere fixture Usuario completo")
def test_downgrade_plan_sin_plan(db_gov_session, db_session, db_event_session):
    """
    Test: downgrade_plan sin plan previo retorna error.
    """
    from backend.core.gov.plans import downgrade_plan
    from backend.db.core.models import Usuario
    
    # Arrange: Usuario sin plan
    user = Usuario(
        usuario_id="user_downgrade_4",
        email="downgrade4@test.com",
        nombre="Downgrade",
        apellido="Four",
        rol="RESIDENTE",
        hashed_password="hash"
    )
    admin = Usuario(
        usuario_id="admin_downgrade_4",
        email="admin_downgrade4@test.com",
        nombre="Admin",
        apellido="Four",
        rol="ADMIN",
        hashed_password="hash"
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    # Act
    result = downgrade_plan(
        db=db_gov_session,
        ejecutor=admin,
        session_token="session_admin",
        target_user=user
    )
    
    # Assert
    assert result["status"] == "sin_plan"
