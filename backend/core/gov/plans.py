"""
═══════════════════════════════════════════════════════════════════════════════
AUP_GOV: Planes Comerciales como Composiciones de Políticas
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

Un PLAN COMERCIAL NO es un feature ni un rol.
Es una COMPOSICIÓN de políticas AUP_GOV.

Axiomas:
  1. Cambiar de plan = cambiar políticas (NO código)
  2. El plan se audita históricamente vía AUP_EVENT
  3. El downgrade es inmediato y trazable
  4. Sin política activa = denegado (safe by default)

═══════════════════════════════════════════════════════════════════════════════
ESTRUCTURA DE PLANES
═══════════════════════════════════════════════════════════════════════════════

PLAN FREE (Entrada):
  Objetivo: Probar sistema con restricciones máximas
  Monetización: $0/mes
  
  Límites:
    - max_tenants: 1
    - max_usuarios_por_tenant: 20
    - max_qr_vigencia_dias: 3
    - max_visitas_mes: 50
    - delegacion_permitida: False
  
  Operaciones bloqueadas:
    - Crear segundo tenant
    - QR con vigencia > 3 días
    - Más de 20 usuarios en tenant
    - Más de 50 visitas/mes
    - Delegar poder

PLAN PRO (Producción):
  Objetivo: Uso productivo con límites razonables
  Monetización: $49/mes por tenant
  
  Límites:
    - max_tenants: 5
    - max_usuarios_por_tenant: 100
    - max_qr_vigencia_dias: 7
    - max_visitas_mes: 500
    - delegacion_permitida: True
    - delegacion_max_dias: 30
  
  Operaciones bloqueadas:
    - Crear 6to tenant
    - QR con vigencia > 7 días
    - Más de 100 usuarios en tenant
    - Más de 500 visitas/mes
    - Delegación > 30 días

PLAN ENTERPRISE (Sin Límites Operativos):
  Objetivo: Clientes grandes con personalización
  Monetización: $499/mes + custom
  
  Límites:
    - max_tenants: 50
    - max_usuarios_por_tenant: 1000
    - max_qr_vigencia_dias: 30
    - max_visitas_mes: 10000
    - delegacion_permitida: True
    - delegacion_max_dias: 365
    - politicas_personalizadas: True
  
  Operaciones bloqueadas:
    - Solo límites de seguridad extremos

═══════════════════════════════════════════════════════════════════════════════
"""

from enum import Enum
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.db.gov import Policy, PolicyScope, GovStatus
from backend.db.core import Usuario
from backend.core.gov.policy import crear_policy
from backend.core.event.registry import registrar_evento
from backend.core.event import EventEntity, EventAction, EventResult


class PlanType(str, Enum):
    """
    Tipos de planes comerciales.
    
    Declaración AUP: Un plan es un identificador de composición de políticas.
    """
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ═══════════════════════════════════════════════════════════════════════════
# DEFINICIONES DE POLÍTICAS POR PLAN
# ═══════════════════════════════════════════════════════════════════════════

PLAN_POLICIES = {
    PlanType.FREE: {
        "max_tenants": 1,
        "max_usuarios": 20,
        "max_qr_vigencia": 3,
        "max_visitas_mes": 50,
        "delegacion_permitida": False,
        "descripcion": "Plan gratuito con límites de prueba"
    },
    
    PlanType.PRO: {
        "max_tenants": 5,
        "max_usuarios": 100,
        "max_qr_vigencia": 7,
        "max_visitas_mes": 500,
        "delegacion_permitida": True,
        "delegacion_max_dias": 30,
        "descripcion": "Plan profesional para producción"
    },
    
    PlanType.ENTERPRISE: {
        "max_tenants": 50,
        "max_usuarios": 1000,
        "max_qr_vigencia": 30,
        "max_visitas_mes": 10000,
        "delegacion_permitida": True,
        "delegacion_max_dias": 365,
        "politicas_personalizadas": True,
        "descripcion": "Plan empresarial sin límites operativos"
    }
}


def crear_politicas_para_plan(
    db: Session,
    plan_type: PlanType,
    target_identity_id: str,
    target_tenant_id: Optional[str] = None
) -> list[Policy]:
    """
    Crea el conjunto de políticas que definen un plan comercial.
    
    Axioma: Un plan es la suma de sus políticas, nada más.
    
    Args:
        db: Sesión de BD
        plan_type: Tipo de plan (FREE, PRO, ENTERPRISE)
        target_identity_id: Usuario al que se aplica
        target_tenant_id: Tenant específico (opcional, si None = todos)
    
    Returns:
        Lista de políticas creadas
    
    Ejemplos:
        # Asignar Plan Pro a usuario
        policies = crear_politicas_para_plan(
            db, PlanType.PRO,
            target_identity_id="user_abc",
            target_tenant_id=None  # Aplica a todos sus tenants
        )
    """
    config = PLAN_POLICIES[plan_type]
    policies = []
    
    # POLÍTICA 1: Límite de tenants
    policy_tenants = crear_policy(
        db=db,
        nombre=f"Plan {plan_type.value.upper()} - Tenants",
        ambito=PolicyScope.GLOBAL if not target_tenant_id else PolicyScope.TENANT,
        accion_objetivo="crear_tenant",
        limites={"max_count": config["max_tenants"]},
        target_tenant_id=target_tenant_id,
        metadata={
            "plan_type": plan_type.value,
            "target_identity": target_identity_id,
            "descripcion": f"Máximo {config['max_tenants']} condominios"
        }
    )
    policies.append(policy_tenants)
    
    # POLÍTICA 2: Límite de usuarios por tenant
    policy_usuarios = crear_policy(
        db=db,
        nombre=f"Plan {plan_type.value.upper()} - Usuarios",
        ambito=PolicyScope.GLOBAL if not target_tenant_id else PolicyScope.TENANT,
        accion_objetivo="crear_usuario",
        limites={"max_usuarios": config["max_usuarios"]},
        target_tenant_id=target_tenant_id,
        metadata={
            "plan_type": plan_type.value,
            "target_identity": target_identity_id,
            "descripcion": f"Máximo {config['max_usuarios']} usuarios por tenant"
        }
    )
    policies.append(policy_usuarios)
    
    # POLÍTICA 3: Vigencia máxima de QR
    policy_qr = crear_policy(
        db=db,
        nombre=f"Plan {plan_type.value.upper()} - QR Vigencia",
        ambito=PolicyScope.GLOBAL if not target_tenant_id else PolicyScope.TENANT,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": config["max_qr_vigencia"]},
        target_tenant_id=target_tenant_id,
        metadata={
            "plan_type": plan_type.value,
            "target_identity": target_identity_id,
            "descripcion": f"QR válidos hasta {config['max_qr_vigencia']} días"
        }
    )
    policies.append(policy_qr)
    
    # POLÍTICA 4: Límite de visitas mensuales
    policy_visitas = crear_policy(
        db=db,
        nombre=f"Plan {plan_type.value.upper()} - Visitas Mensuales",
        ambito=PolicyScope.GLOBAL if not target_tenant_id else PolicyScope.TENANT,
        accion_objetivo="crear_visita",
        limites={"max_count": config["max_visitas_mes"]},
        target_tenant_id=target_tenant_id,
        metadata={
            "plan_type": plan_type.value,
            "target_identity": target_identity_id,
            "descripcion": f"Máximo {config['max_visitas_mes']} visitas/mes"
        }
    )
    policies.append(policy_visitas)
    
    # POLÍTICA 5: Delegación (si permitida)
    if config.get("delegacion_permitida", False):
        policy_delegacion = crear_policy(
            db=db,
            nombre=f"Plan {plan_type.value.upper()} - Delegación",
            ambito=PolicyScope.GLOBAL if not target_tenant_id else PolicyScope.TENANT,
            accion_objetivo="delegar_poder",
            limites={"max_dias_vigencia": config.get("delegacion_max_dias", 30)},
            target_tenant_id=target_tenant_id,
            metadata={
                "plan_type": plan_type.value,
                "target_identity": target_identity_id,
                "descripcion": f"Delegación hasta {config.get('delegacion_max_dias')} días"
            }
        )
        policies.append(policy_delegacion)
    else:
        # Plan Free: Bloquear delegación completamente
        policy_no_delegacion = crear_policy(
            db=db,
            nombre=f"Plan {plan_type.value.upper()} - Sin Delegación",
            ambito=PolicyScope.GLOBAL if not target_tenant_id else PolicyScope.TENANT,
            accion_objetivo="delegar_poder",
            limites={"max_count": 0},  # Cero delegaciones permitidas
            target_tenant_id=target_tenant_id,
            metadata={
                "plan_type": plan_type.value,
                "target_identity": target_identity_id,
                "descripcion": "Delegación no permitida en plan Free"
            }
        )
        policies.append(policy_no_delegacion)
    
    return policies


def asignar_plan_con_evento(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    target_user: Usuario,
    plan_type: PlanType,
    tenant_id: Optional[str] = None
) -> tuple[list[Policy], dict]:
    """
    Asigna un plan comercial a un usuario.
    
    Axiomas aplicados:
      1. Revocar políticas anteriores del mismo tipo
      2. Crear nuevas políticas del plan solicitado
      3. Registrar AUP_EVENT de cambio de plan
      4. Efecto inmediato (no requiere cache flush)
    
    Args:
        db: Sesión de BD
        ejecutor: Usuario que ejecuta el cambio (admin)
        session_token: JWT del ejecutor
        target_user: Usuario que recibe el plan
        plan_type: Tipo de plan (FREE, PRO, ENTERPRISE)
        tenant_id: Tenant específico (opcional)
    
    Returns:
        (policies_creadas, summary)
    """
    # 1. Revocar políticas anteriores con mismo target
    from backend.core.gov.policy import obtener_policies
    
<<<<<<< HEAD
    politicas_anteriores = db.query(Policy).filter(
        Policy.metadata_json["target_identity"].astext == target_user.usuario_id,
        Policy.estado == GovStatus.ACTIVO
    ).all()
=======
    # Obtener todas las policies activas y filtrar en Python (compatible SQLite/PostgreSQL)
    todas_activas = db.query(Policy).filter(Policy.estado == GovStatus.ACTIVO).all()
    politicas_anteriores = [
        pol for pol in todas_activas
        if pol.metadata_json and pol.metadata_json.get("target_identity") == target_user.usuario_id
    ]
>>>>>>> main
    
    plan_anterior = None
    for pol in politicas_anteriores:
        if pol.metadata and pol.metadata.get("plan_type"):
            plan_anterior = pol.metadata.get("plan_type")
        pol.estado = GovStatus.REVOCADO
        pol.metadata = pol.metadata or {}
        pol.metadata["revoked_at"] = datetime.utcnow().isoformat()
        pol.metadata["revoked_by"] = ejecutor.usuario_id
    
    db.commit()
    
    # 2. Crear políticas del nuevo plan
    nuevas_policies = crear_politicas_para_plan(
        db=db,
        plan_type=plan_type,
        target_identity_id=target_user.usuario_id,
        target_tenant_id=tenant_id
    )
    
    # 3. Registrar evento de cambio de plan
    registrar_evento(
        db=db,
        identity=ejecutor,
        session_token=session_token,
        tenant_id=tenant_id or "sistema",
        entidad=EventEntity.POLICY.value,
        entidad_id=f"plan_change_{target_user.usuario_id}",
        accion=EventAction.ASIGNAR.value,
        resultado=EventResult.EXITO.value,
        motivo=f"Plan cambiado: {plan_anterior or 'ninguno'} → {plan_type.value}",
        metadata={
            "target_user": target_user.usuario_id,
            "plan_anterior": plan_anterior,
            "plan_nuevo": plan_type.value,
            "politicas_revocadas": len(politicas_anteriores),
            "politicas_creadas": len(nuevas_policies),
            "limites": PLAN_POLICIES[plan_type]
        }
    )
    
    summary = {
        "plan_anterior": plan_anterior,
        "plan_nuevo": plan_type.value,
        "politicas_revocadas": len(politicas_anteriores),
        "politicas_creadas": len(nuevas_policies),
        "limites": PLAN_POLICIES[plan_type],
        "efecto": "inmediato"
    }
    
    return (nuevas_policies, summary)


def obtener_plan_actual(
    db: Session,
    usuario_id: str
) -> Optional[dict]:
    """
    Obtiene el plan comercial actual de un usuario.
    
    Axioma: El plan es la composición de políticas activas.
    
    Args:
        db: Sesión de BD
        usuario_id: ID del usuario
    
    Returns:
        Diccionario con plan actual o None si no tiene plan
    """
<<<<<<< HEAD
    # Buscar políticas activas del usuario
    policies = db.query(Policy).filter(
        Policy.metadata_json["target_identity"].astext == usuario_id,
        Policy.estado == GovStatus.ACTIVO
    ).all()
=======
    # Buscar políticas activas del usuario (compatible SQLite/PostgreSQL)
    todas_activas = db.query(Policy).filter(Policy.estado == GovStatus.ACTIVO).all()
    policies = [
        pol for pol in todas_activas
        if pol.metadata_json and pol.metadata_json.get("target_identity") == usuario_id
    ]
>>>>>>> main
    
    if not policies:
        return None
    
    # Extraer tipo de plan de metadata
    plan_type = None
    for pol in policies:
        if pol.metadata_json and pol.metadata_json.get("plan_type"):
            plan_type = pol.metadata_json["plan_type"]
            break
    
    if not plan_type:
        return None
    
    # Extraer límites de las políticas
    limites = {}
    for pol in policies:
        if "max_count" in pol.limites:
            if pol.accion_objetivo == "crear_tenant":
                limites["max_tenants"] = pol.limites["max_count"]
            elif pol.accion_objetivo == "crear_visita":
                limites["max_visitas_mes"] = pol.limites["max_count"]
        
        if "max_usuarios" in pol.limites:
            limites["max_usuarios"] = pol.limites["max_usuarios"]
        
        if "max_dias_vigencia" in pol.limites:
            if pol.accion_objetivo == "generar_qr":
                limites["max_qr_vigencia"] = pol.limites["max_dias_vigencia"]
            elif pol.accion_objetivo == "delegar_poder":
                limites["delegacion_max_dias"] = pol.limites["max_dias_vigencia"]
    
    return {
        "plan_type": plan_type,
        "politicas_activas": len(policies),
        "limites": limites,
        "descripcion": PLAN_POLICIES[PlanType(plan_type)]["descripcion"]
    }


def upgrade_plan(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    target_user: Usuario,
    tenant_id: Optional[str] = None
) -> dict:
    """
    Upgrade automático al siguiente plan.
    
    Flujo: FREE → PRO → ENTERPRISE
    
    Axioma: Upgrade = revocar políticas restrictivas + crear políticas permisivas.
    """
    plan_actual = obtener_plan_actual(db, target_user.usuario_id)
    
    if not plan_actual:
        # Sin plan → asignar Free
        nuevo_plan = PlanType.FREE
    elif plan_actual["plan_type"] == PlanType.FREE.value:
        nuevo_plan = PlanType.PRO
    elif plan_actual["plan_type"] == PlanType.PRO.value:
        nuevo_plan = PlanType.ENTERPRISE
    else:
        # Ya en Enterprise, no hay upgrade
        return {
            "status": "ya_en_plan_maximo",
            "plan_actual": plan_actual["plan_type"]
        }
    
    _, summary = asignar_plan_con_evento(
        db, ejecutor, session_token, target_user, nuevo_plan, tenant_id
    )
    
    return {
        "status": "upgrade_exitoso",
        **summary
    }


def downgrade_plan(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    target_user: Usuario,
    tenant_id: Optional[str] = None
) -> dict:
    """
    Downgrade inmediato al plan inferior.
    
    Flujo: ENTERPRISE → PRO → FREE
    
    Axioma: Downgrade = revocar políticas permisivas + crear políticas restrictivas.
    Efecto: INMEDIATO (operaciones en curso pueden fallar).
    """
    plan_actual = obtener_plan_actual(db, target_user.usuario_id)
    
    if not plan_actual:
        return {
            "status": "sin_plan",
            "mensaje": "Usuario no tiene plan asignado"
        }
    
    if plan_actual["plan_type"] == PlanType.ENTERPRISE.value:
        nuevo_plan = PlanType.PRO
    elif plan_actual["plan_type"] == PlanType.PRO.value:
        nuevo_plan = PlanType.FREE
    else:
        # Ya en Free, no hay downgrade
        return {
            "status": "ya_en_plan_minimo",
            "plan_actual": plan_actual["plan_type"]
        }
    
    _, summary = asignar_plan_con_evento(
        db, ejecutor, session_token, target_user, nuevo_plan, tenant_id
    )
    
    return {
        "status": "downgrade_inmediato",
        "advertencia": "Límites reducidos. Operaciones en curso pueden fallar.",
        **summary
    }
