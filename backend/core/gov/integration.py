"""
═══════════════════════════════════════════════════════════════════════════════
AUP_GOV: Integración con AUP_EVENT
═══════════════════════════════════════════════════════════════════════════════

Funciones que combinan operaciones de gobierno con registro de eventos.

Axioma: Toda acción de gobierno genera AUP_EVENT.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.models import Authority, Policy, Delegation, Usuario, AuthorityType, PolicyScope
from backend.core.gov.authority import crear_authority as _crear_authority, revocar_authority as _revocar_authority
from backend.core.gov.policy import crear_policy as _crear_policy, evaluar_politica as _evaluar_politica, revocar_policy as _revocar_policy
from backend.core.gov.delegation import delegar_poder as _delegar_poder, revocar_delegacion as _revocar_delegacion
from backend.core.event.registry import registrar_evento
from backend.core.event import EventEntity, EventAction, EventResult


def crear_authority_con_evento(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    identity: Usuario,
    tipo: AuthorityType,
    tenant_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Authority:
    """
    Crea AUP_AUTHORITY y registra AUP_EVENT.
    
    Args:
        db: Sesión de BD
        ejecutor: Usuario que ejecuta la acción (debe tener poder)
        session_token: JWT del ejecutor
        identity: Usuario que recibirá la autoridad
        tipo: GLOBAL o FIRST_TIER
        tenant_id: Tenant (si FIRST_TIER)
        metadata: Contexto adicional
    
    Returns:
        Authority creada
    """
    try:
        # Crear authority
        authority = _crear_authority(db, identity, tipo, tenant_id, metadata)
        
        # Registrar evento exitoso
        registrar_evento(
            db=db,
            identity=ejecutor,
            session_token=session_token,
            tenant_id=tenant_id or "sistema",
            entidad="authority",
            entidad_id=authority.authority_id,
            accion=EventAction.ASIGNAR.value,
            resultado=EventResult.EXITO.value,
            motivo=f"Authority {tipo.value} creada para {identity.usuario_id}",
            metadata={
                "target_identity": identity.usuario_id,
                "authority_type": tipo.value,
                "tenant_id": tenant_id
            }
        )
        
        return authority
        
    except Exception as e:
        # Registrar evento fallido
        registrar_evento(
            db=db,
            identity=ejecutor,
            session_token=session_token,
            tenant_id=tenant_id or "sistema",
            entidad="authority",
            entidad_id="pending",
            accion=EventAction.ASIGNAR.value,
            resultado=EventResult.ERROR.value,
            motivo=f"Error al crear authority: {str(e)}"
        )
        raise


def revocar_authority_con_evento(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    authority_id: str,
    motivo: Optional[str] = None
) -> Authority:
    """
    Revoca AUP_AUTHORITY y registra AUP_EVENT.
    
    Args:
        db: Sesión de BD
        ejecutor: Usuario que ejecuta la revocación
        session_token: JWT del ejecutor
        authority_id: ID de la autoridad a revocar
        motivo: Razón de revocación
    
    Returns:
        Authority revocada
    """
    authority = _revocar_authority(db, authority_id, ejecutor.usuario_id, motivo)
    
    # Registrar evento
    registrar_evento(
        db=db,
        identity=ejecutor,
        session_token=session_token,
        tenant_id=authority.tenant_id or "sistema",
        entidad="authority",
        entidad_id=authority_id,
        accion=EventAction.REVOCAR.value,
        resultado=EventResult.EXITO.value,
        motivo=motivo or "Authority revocada",
        metadata={
            "revoked_identity": authority.identity_id,
            "authority_type": authority.tipo.value
        }
    )
    
    return authority


def crear_policy_con_evento(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    nombre: str,
    ambito: PolicyScope,
    accion_objetivo: str,
    limites: dict,
    target_tenant_id: Optional[str] = None,
    valida_desde: Optional[datetime] = None,
    valida_hasta: Optional[datetime] = None,
    metadata: Optional[dict] = None
) -> Policy:
    """
    Crea AUP_POLICY y registra AUP_EVENT.
    
    Args:
        db: Sesión de BD
        ejecutor: Usuario que crea la política (debe tener authority)
        session_token: JWT del ejecutor
        nombre: Nombre de la política
        ambito: GLOBAL, TENANT o SCOPE
        accion_objetivo: Acción que gobierna
        limites: Límites estructurales
        target_tenant_id: Tenant (si TENANT)
        valida_desde: Inicio vigencia
        valida_hasta: Fin vigencia
        metadata: Contexto adicional
    
    Returns:
        Policy creada
    """
    try:
        # Crear policy
        policy = _crear_policy(
            db, nombre, ambito, accion_objetivo, limites,
            target_tenant_id, valida_desde, valida_hasta, metadata
        )
        
        # Registrar evento
        registrar_evento(
            db=db,
            identity=ejecutor,
            session_token=session_token,
            tenant_id=target_tenant_id or "sistema",
            entidad="policy",
            entidad_id=policy.policy_id,
            accion=EventAction.CREAR.value,
            resultado=EventResult.EXITO.value,
            motivo=f"Policy '{nombre}' creada",
            metadata={
                "ambito": ambito.value,
                "accion_objetivo": accion_objetivo,
                "limites": limites
            }
        )
        
        return policy
        
    except Exception as e:
        # Registrar evento fallido
        registrar_evento(
            db=db,
            identity=ejecutor,
            session_token=session_token,
            tenant_id=target_tenant_id or "sistema",
            entidad="policy",
            entidad_id="pending",
            accion=EventAction.CREAR.value,
            resultado=EventResult.ERROR.value,
            motivo=f"Error al crear policy: {str(e)}"
        )
        raise


def evaluar_politica_con_evento(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    accion: str,
    tenant_id: Optional[str] = None,
    valor_actual: Optional[any] = None,
    metadata: Optional[dict] = None
) -> tuple[bool, Optional[str]]:
    """
    Evalúa AUP_POLICY y registra AUP_EVENT.
    
    Args:
        db: Sesión de BD
        ejecutor: Usuario que solicita la acción
        session_token: JWT del ejecutor
        accion: Acción a evaluar
        tenant_id: Tenant donde ocurre
        valor_actual: Valor actual para comparar con límites
        metadata: Contexto adicional
    
    Returns:
        (permitido, motivo)
    """
    # Evaluar política
    permitido, motivo = _evaluar_politica(db, accion, tenant_id, valor_actual, metadata)
    
    # Registrar evento
    registrar_evento(
        db=db,
        identity=ejecutor,
        session_token=session_token,
        tenant_id=tenant_id or "sistema",
        entidad="policy",
        entidad_id=accion,
        accion=EventAction.VALIDAR.value,
        resultado=EventResult.PERMITIDO.value if permitido else EventResult.DENEGADO.value,
        motivo=motivo,
        metadata={
            "accion_evaluada": accion,
            "valor_actual": valor_actual,
            "permitido": permitido
        }
    )
    
    return (permitido, motivo)


def delegar_poder_con_evento(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    authority: Authority,
    permisos: list[str],
    target_identity_id: Optional[str] = None,
    target_scope_id: Optional[str] = None,
    valida_desde: Optional[datetime] = None,
    valida_hasta: Optional[datetime] = None,
    metadata: Optional[dict] = None
) -> Delegation:
    """
    Delega poder y registra AUP_EVENT.
    
    Args:
        db: Sesión de BD
        ejecutor: Usuario que delega (debe ser dueño de authority)
        session_token: JWT del ejecutor
        authority: Authority que delega
        permisos: Lista de permisos a delegar
        target_identity_id: Usuario que recibe
        target_scope_id: Scope que recibe
        valida_desde: Inicio vigencia
        valida_hasta: Fin vigencia
        metadata: Contexto adicional
    
    Returns:
        Delegation creada
    """
    try:
        # Delegar poder
        delegation = _delegar_poder(
            db, authority, permisos,
            target_identity_id, target_scope_id,
            valida_desde, valida_hasta, metadata
        )
        
        # Registrar evento
        registrar_evento(
            db=db,
            identity=ejecutor,
            session_token=session_token,
            tenant_id=authority.tenant_id or "sistema",
            entidad="delegation",
            entidad_id=delegation.delegation_id,
            accion=EventAction.DELEGAR_PODER.value,
            resultado=EventResult.EXITO.value,
            motivo=f"Poder delegado: {', '.join(permisos)}",
            metadata={
                "authority_id": authority.authority_id,
                "permisos": permisos,
                "target_identity": target_identity_id,
                "target_scope": target_scope_id,
                "valida_hasta": str(valida_hasta) if valida_hasta else None
            }
        )
        
        return delegation
        
    except Exception as e:
        # Registrar evento fallido
        registrar_evento(
            db=db,
            identity=ejecutor,
            session_token=session_token,
            tenant_id=authority.tenant_id or "sistema",
            entidad="delegation",
            entidad_id="pending",
            accion=EventAction.DELEGAR_PODER.value,
            resultado=EventResult.ERROR.value,
            motivo=f"Error al delegar poder: {str(e)}"
        )
        raise


def revocar_delegacion_con_evento(
    db: Session,
    ejecutor: Usuario,
    session_token: str,
    delegation_id: str,
    motivo: Optional[str] = None
) -> Delegation:
    """
    Revoca AUP_DELEGATION y registra AUP_EVENT.
    
    Args:
        db: Sesión de BD
        ejecutor: Usuario que revoca
        session_token: JWT del ejecutor
        delegation_id: ID de la delegación
        motivo: Razón de revocación
    
    Returns:
        Delegation revocada
    """
    delegation = _revocar_delegacion(db, delegation_id, ejecutor.usuario_id, motivo)
    
    # Registrar evento
    registrar_evento(
        db=db,
        identity=ejecutor,
        session_token=session_token,
        tenant_id="sistema",
        entidad="delegation",
        entidad_id=delegation_id,
        accion=EventAction.REVOCAR.value,
        resultado=EventResult.EXITO.value,
        motivo=motivo or "Delegación revocada",
        metadata={
            "permisos_revocados": delegation.permisos_delegados,
            "target_identity": delegation.target_identity_id,
            "target_scope": delegation.target_scope_id
        }
    )
    
    return delegation


__all__ = [
    "crear_authority_con_evento",
    "revocar_authority_con_evento",
    "crear_policy_con_evento",
    "evaluar_politica_con_evento",
    "delegar_poder_con_evento",
    "revocar_delegacion_con_evento",
]
