"""
═══════════════════════════════════════════════════════════════════════════════
AUP_GOV: Funciones de Delegación
═══════════════════════════════════════════════════════════════════════════════

Funciones estructurales para gestionar AUP_DELEGATION.

Axiomas:
  1. Todo poder delegado es explícito
  2. Todo poder delegado es acotado
  3. Todo poder delegado es revocable
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.db.gov import Delegation, Authority, GovStatus
from backend.db.core import Usuario, UserTenantScope


def delegar_poder(
    db: Session,
    authority: Authority,
    permisos: list[str],
    target_identity_id: Optional[str] = None,
    target_scope_id: Optional[str] = None,
    valida_desde: Optional[datetime] = None,
    valida_hasta: Optional[datetime] = None,
    metadata: Optional[dict] = None
) -> Delegation:
    """
    Crea una AUP_DELEGATION.
    
    Axiomas:
      1. Todo poder delegado es explícito (lista de permisos)
      2. Todo poder delegado es acotado (vigencia temporal)
      3. Todo poder delegado es revocable
    
    Args:
        db: Sesión de BD
        authority: AUP_AUTHORITY que delega
        permisos: Lista de permisos a delegar (ej: ["crear_tenant", "asignar_scope"])
        target_identity_id: ID de usuario que recibe delegación
        target_scope_id: ID de scope que recibe delegación
        valida_desde: Inicio de vigencia (default: ahora)
        valida_hasta: Fin de vigencia (default: sin fin, pero recomendado)
        metadata: Contexto adicional
    
    Returns:
        Delegation creada
    
    Raises:
        ValueError: Si no se especifica target_identity_id ni target_scope_id
        ValueError: Si se especifican ambos (mutuamente excluyente)
        ValueError: Si permisos está vacío
    """
    # Validación estructural
    if not target_identity_id and not target_scope_id:
        raise ValueError("Debe especificar target_identity_id O target_scope_id")
    
    if target_identity_id and target_scope_id:
        raise ValueError("target_identity_id y target_scope_id son mutuamente excluyentes")
    
    if not permisos:
        raise ValueError("Debe especificar al menos un permiso a delegar")
    
    # Verificar que target existe
    if target_identity_id:
        target = db.query(Usuario).filter(Usuario.usuario_id == target_identity_id).first()
        if not target:
            raise ValueError(f"Usuario {target_identity_id} no existe")
    
    if target_scope_id:
        target = db.query(UserTenantScope).filter(UserTenantScope.id == target_scope_id).first()
        if not target:
            raise ValueError(f"Scope {target_scope_id} no existe")
    
    # Crear delegación
    delegation = Delegation(
        delegation_id=f"del_{uuid.uuid4().hex[:16]}",
        authority_id=authority.authority_id,
        target_identity_id=target_identity_id,
        target_scope_id=target_scope_id,
        permisos_delegados=permisos,
        valida_desde=valida_desde or datetime.utcnow(),
        valida_hasta=valida_hasta,
        estado=GovStatus.ACTIVO,
        metadata=metadata,
        created_at=datetime.utcnow()
    )
    
    db.add(delegation)
    db.commit()
    db.refresh(delegation)
    
    return delegation


def obtener_delegaciones(
    db: Session,
    authority_id: Optional[str] = None,
    target_identity_id: Optional[str] = None,
    target_scope_id: Optional[str] = None,
    estado: GovStatus = GovStatus.ACTIVO
) -> list[Delegation]:
    """
    Obtiene delegaciones filtradas.
    
    Args:
        db: Sesión de BD
        authority_id: Filtrar por autoridad que delegó (opcional)
        target_identity_id: Filtrar por identidad que recibió (opcional)
        target_scope_id: Filtrar por scope que recibió (opcional)
        estado: Filtrar por estado (default: ACTIVO)
    
    Returns:
        Lista de delegaciones vigentes
    """
    now = datetime.utcnow()
    
    query = db.query(Delegation).filter(
        Delegation.estado == estado,
        Delegation.valida_desde <= now
    )
    
    # Solo delegaciones vigentes
    query = query.filter(
        (Delegation.valida_hasta.is_(None)) | (Delegation.valida_hasta >= now)
    )
    
    if authority_id:
        query = query.filter(Delegation.authority_id == authority_id)
    
    if target_identity_id:
        query = query.filter(Delegation.target_identity_id == target_identity_id)
    
    if target_scope_id:
        query = query.filter(Delegation.target_scope_id == target_scope_id)
    
    return query.order_by(Delegation.created_at.desc()).all()


def tiene_permiso_delegado(
    db: Session,
    identity_id: str,
    permiso: str
) -> bool:
    """
    Verifica si una identidad tiene un permiso específico por delegación.
    
    Args:
        db: Sesión de BD
        identity_id: ID de la identidad
        permiso: Permiso a verificar (ej: "crear_tenant")
    
    Returns:
        True si tiene el permiso delegado y vigente
    """
    delegaciones = obtener_delegaciones(
        db,
        target_identity_id=identity_id,
        estado=GovStatus.ACTIVO
    )
    
    for delegacion in delegaciones:
        if permiso in delegacion.permisos_delegados:
            return True
    
    return False


def revocar_delegacion(
    db: Session,
    delegation_id: str,
    revocada_por: str,
    motivo: Optional[str] = None
) -> Delegation:
    """
    Revoca una AUP_DELEGATION.
    
    Axioma: Todo poder delegado es revocable.
    
    Args:
        db: Sesión de BD
        delegation_id: ID de la delegación
        revocada_por: ID de quien revoca
        motivo: Razón de revocación
    
    Returns:
        Delegation revocada
    
    Raises:
        HTTPException 404: Si delegation no existe
        HTTPException 400: Si ya está revocada
    """
    delegation = db.query(Delegation).filter(Delegation.delegation_id == delegation_id).first()
    
    if not delegation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delegation {delegation_id} no encontrada"
        )
    
    if delegation.estado == GovStatus.REVOCADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Delegation {delegation_id} ya está revocada"
        )
    
    # Revocar
    delegation.estado = GovStatus.REVOCADO
    delegation.revoked_at = datetime.utcnow()
    
    if not delegation.metadata_json:
        delegation.metadata_json = {}
    delegation.metadata_json["revoked_by"] = revocada_por
    delegation.metadata_json["revoked_reason"] = motivo
    
    db.commit()
    db.refresh(delegation)
    
    return delegation


def listar_delegaciones(
    db: Session,
    authority_id: Optional[str] = None,
    estado: GovStatus = GovStatus.ACTIVO
) -> list[Delegation]:
    """
    Lista todas las delegaciones de una autoridad.
    
    Args:
        db: Sesión de BD
        authority_id: Filtrar por autoridad (opcional)
        estado: Filtrar por estado (default: ACTIVO)
    
    Returns:
        Lista de delegaciones
    """
    query = db.query(Delegation).filter(Delegation.estado == estado)
    
    if authority_id:
        query = query.filter(Delegation.authority_id == authority_id)
    
    return query.order_by(Delegation.created_at.desc()).all()


__all__ = [
    "delegar_poder",
    "obtener_delegaciones",
    "tiene_permiso_delegado",
    "revocar_delegacion",
    "listar_delegaciones",
]
