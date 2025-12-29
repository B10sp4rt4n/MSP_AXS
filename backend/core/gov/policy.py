"""
═══════════════════════════════════════════════════════════════════════════════
AUP_GOV: Funciones de Política
═══════════════════════════════════════════════════════════════════════════════

Funciones estructurales para gestionar y evaluar AUP_POLICY.

Axioma: La política precede a la operación (policy-first).
"""

import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.db.models import Policy, PolicyScope, GovStatus


def crear_policy(
    db: Session,
    nombre: str,
    ambito: PolicyScope,
    accion_objetivo: str,
    limites: dict[str, Any],
    target_tenant_id: Optional[str] = None,
    valida_desde: Optional[datetime] = None,
    valida_hasta: Optional[datetime] = None,
    metadata: Optional[dict] = None
) -> Policy:
    """
    Crea una AUP_POLICY.
    
    Axioma: La política precede a la operación.
    
    Ejemplos de límites:
      - {"max_count": 10} → máximo 10 de algo
      - {"max_dias_vigencia": 7} → máximo 7 días de vigencia
      - {"max_usuarios": 100} → máximo 100 usuarios
    
    Args:
        db: Sesión de BD
        nombre: Nombre declarativo de la política
        ambito: GLOBAL, TENANT o SCOPE
        accion_objetivo: Acción que gobierna (crear_tenant, generar_qr, etc.)
        limites: Diccionario con límites estructurales
        target_tenant_id: Requerido si ambito=TENANT
        valida_desde: Inicio de vigencia (default: ahora)
        valida_hasta: Fin de vigencia (default: sin fin)
        metadata: Contexto adicional
    
    Returns:
        Policy creada
    
    Raises:
        ValueError: Si ambito=TENANT y no hay target_tenant_id
    """
    # Validación estructural
    if ambito == PolicyScope.TENANT and not target_tenant_id:
        raise ValueError("TENANT policy requiere target_tenant_id")
    
    if ambito == PolicyScope.GLOBAL and target_tenant_id:
        raise ValueError("GLOBAL policy no debe tener target_tenant_id")
    
    policy = Policy(
        policy_id=f"pol_{uuid.uuid4().hex[:16]}",
        nombre=nombre,
        ambito=ambito,
        target_tenant_id=target_tenant_id,
        accion_objetivo=accion_objetivo,
        limites=limites,
        valida_desde=valida_desde or datetime.utcnow(),
        valida_hasta=valida_hasta,
        estado=GovStatus.ACTIVO,
        metadata=metadata,
        created_at=datetime.utcnow()
    )
    
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    return policy


def obtener_policies(
    db: Session,
    accion_objetivo: str,
    ambito: Optional[PolicyScope] = None,
    tenant_id: Optional[str] = None,
    estado: GovStatus = GovStatus.ACTIVO
) -> list[Policy]:
    """
    Obtiene políticas aplicables a una acción.
    
    Args:
        db: Sesión de BD
        accion_objetivo: Acción a evaluar
        ambito: Filtrar por ámbito (opcional)
        tenant_id: Filtrar por tenant (opcional)
        estado: Filtrar por estado (default: ACTIVO)
    
    Returns:
        Lista de policies ordenadas por prioridad (TENANT > GLOBAL)
    """
    now = datetime.utcnow()
    
    query = db.query(Policy).filter(
        Policy.accion_objetivo == accion_objetivo,
        Policy.estado == estado,
        Policy.valida_desde <= now
    )
    
    # Solo políticas vigentes
    query = query.filter(
        (Policy.valida_hasta.is_(None)) | (Policy.valida_hasta >= now)
    )
    
    if ambito:
        query = query.filter(Policy.ambito == ambito)
    
    if tenant_id:
        # Buscar políticas TENANT específicas + GLOBAL
        query = query.filter(
            (Policy.ambito == PolicyScope.GLOBAL) |
            ((Policy.ambito == PolicyScope.TENANT) & (Policy.target_tenant_id == tenant_id))
        )
    
    # Orden: TENANT primero, luego GLOBAL (prioridad)
    return query.order_by(
        Policy.ambito.desc(),  # TENANT > GLOBAL alfabéticamente
        Policy.created_at.desc()
    ).all()


def evaluar_politica(
    db: Session,
    accion: str,
    tenant_id: Optional[str] = None,
    valor_actual: Optional[Any] = None,
    metadata: Optional[dict] = None
) -> tuple[bool, Optional[str]]:
    """
    ═══════════════════════════════════════════════════════════════════════
    EVALUADOR CENTRAL DE AUP_POLICY
    ═══════════════════════════════════════════════════════════════════════
    
    Evalúa si una acción está permitida según políticas activas.
    
    Axioma: Policy-first. Si no hay política, por defecto se DENIEGA.
    
    Flujo:
      1. Buscar políticas aplicables (TENANT + GLOBAL)
      2. Evaluar límites de cada política
      3. Si alguna política DENIEGA → DENEGADO
      4. Si todas PERMITEN → PERMITIDO
      5. Si no hay políticas → DENEGADO (safe by default)
    
    Args:
        db: Sesión de BD
        accion: Acción a evaluar (crear_tenant, generar_qr, etc.)
        tenant_id: Tenant donde ocurre la acción (opcional)
        valor_actual: Valor actual a comparar con límites (ej: 5 tenants)
        metadata: Contexto adicional para evaluación
    
    Returns:
        (permitido: bool, motivo: str)
        
    Ejemplos:
        # Evaluar si puede crear tenant (límite: 5 tenants)
        permitido, motivo = evaluar_politica(
            db, "crear_tenant",
            tenant_id=None,
            valor_actual=4  # Tiene 4 tenants actualmente
        )
        # Si límite es 5 → (True, "Dentro del límite")
        # Si límite es 3 → (False, "Límite excedido: max 3")
    """
    # Buscar políticas aplicables
    policies = obtener_policies(
        db,
        accion_objetivo=accion,
        tenant_id=tenant_id,
        estado=GovStatus.ACTIVO
    )
    
    # Si no hay políticas → DENEGADO por defecto (safe)
    if not policies:
        return (False, f"No hay política definida para acción '{accion}'")
    
    # Evaluar cada política
    for policy in policies:
        limites = policy.limites
        
        # Evaluar límite "max_count"
        if "max_count" in limites and valor_actual is not None:
            if valor_actual >= limites["max_count"]:
                return (
                    False,
                    f"Límite excedido: máximo {limites['max_count']} (actual: {valor_actual})"
                )
        
        # Evaluar límite "max_dias_vigencia"
        if "max_dias_vigencia" in limites and metadata:
            dias_solicitados = metadata.get("dias_vigencia")
            if dias_solicitados and dias_solicitados > limites["max_dias_vigencia"]:
                return (
                    False,
                    f"Vigencia excedida: máximo {limites['max_dias_vigencia']} días (solicitado: {dias_solicitados})"
                )
        
        # Evaluar límite "max_usuarios"
        if "max_usuarios" in limites and valor_actual is not None:
            if valor_actual >= limites["max_usuarios"]:
                return (
                    False,
                    f"Límite de usuarios excedido: máximo {limites['max_usuarios']}"
                )
    
    # Si todas las políticas pasaron → PERMITIDO
    return (True, "Acción permitida por políticas")


def revocar_policy(
    db: Session,
    policy_id: str,
    revocada_por: str,
    motivo: Optional[str] = None
) -> Policy:
    """
    Revoca una AUP_POLICY.
    
    Args:
        db: Sesión de BD
        policy_id: ID de la política
        revocada_por: ID de quien revoca
        motivo: Razón de revocación
    
    Returns:
        Policy revocada
    
    Raises:
        HTTPException 404: Si policy no existe
    """
    policy = db.query(Policy).filter(Policy.policy_id == policy_id).first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} no encontrada"
        )
    
    policy.estado = GovStatus.REVOCADO
    
    if not policy.metadata:
        policy.metadata = {}
    policy.metadata["revoked_by"] = revocada_por
    policy.metadata["revoked_reason"] = motivo
    policy.metadata["revoked_at"] = datetime.utcnow().isoformat()
    
    db.commit()
    db.refresh(policy)
    
    return policy


def listar_policies(
    db: Session,
    ambito: Optional[PolicyScope] = None,
    accion_objetivo: Optional[str] = None,
    estado: GovStatus = GovStatus.ACTIVO
) -> list[Policy]:
    """
    Lista policies filtradas.
    
    Args:
        db: Sesión de BD
        ambito: Filtrar por ámbito (opcional)
        accion_objetivo: Filtrar por acción (opcional)
        estado: Filtrar por estado (default: ACTIVO)
    
    Returns:
        Lista de policies
    """
    query = db.query(Policy).filter(Policy.estado == estado)
    
    if ambito:
        query = query.filter(Policy.ambito == ambito)
    
    if accion_objetivo:
        query = query.filter(Policy.accion_objetivo == accion_objetivo)
    
    return query.order_by(Policy.created_at.desc()).all()


__all__ = [
    "crear_policy",
    "obtener_policies",
    "evaluar_politica",
    "revocar_policy",
    "listar_policies",
]
