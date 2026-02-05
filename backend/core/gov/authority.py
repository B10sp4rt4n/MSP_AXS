"""
═══════════════════════════════════════════════════════════════════════════════
AUP_GOV: Funciones de Autoridad
═══════════════════════════════════════════════════════════════════════════════

Funciones estructurales para gestionar AUP_AUTHORITY.

NO contiene lógica de negocio.
SÍ contiene validación estructural de poder.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.db.gov import Authority, AuthorityType, GovStatus
from backend.db.core import Usuario, Condominio
from backend.core.gov import AuthorityType as GovAuthorityType


def crear_authority(
    db: Session,
    identity: Usuario,
    tipo: AuthorityType,
    tenant_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Authority:
    """
    Crea una AUP_AUTHORITY para una identidad.
    
    Axioma: Solo otra AUTHORITY puede crear nuevas authorities.
    Esta función es estructural; validación de quién puede llamarla
    se hace a nivel de endpoint.
    
    Args:
        db: Sesión de BD
        identity: AUP_IDENTITY que recibirá la autoridad
        tipo: GLOBAL o FIRST_TIER
        tenant_id: Requerido si tipo=FIRST_TIER
        metadata: Contexto adicional
    
    Returns:
        Authority creada
    
    Raises:
        ValueError: Si tipo=FIRST_TIER y no hay tenant_id
    """
    # Validación estructural
    if tipo == AuthorityType.FIRST_TIER and not tenant_id:
        raise ValueError("FIRST_TIER authority requiere tenant_id")
    
    if tipo == AuthorityType.GLOBAL and tenant_id:
        raise ValueError("GLOBAL authority no debe tener tenant_id")
    
    # Verificar que tenant existe si aplica
    if tenant_id:
        tenant = db.query(Condominio).filter(Condominio.condominio_id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} no existe")
    
    # Crear authority
    authority = Authority(
        authority_id=f"auth_{uuid.uuid4().hex[:16]}",
        identity_id=identity.usuario_id,
        tipo=tipo,
        tenant_id=tenant_id,
        estado=GovStatus.ACTIVO,
        metadata=metadata,
        created_at=datetime.utcnow()
    )
    
    db.add(authority)
    db.commit()
    db.refresh(authority)
    
    return authority


def obtener_authority(
    db: Session,
    identity_id: str,
    tipo: Optional[AuthorityType] = None,
    tenant_id: Optional[str] = None
) -> Optional[Authority]:
    """
    Obtiene la AUP_AUTHORITY de una identidad.
    
    Args:
        db: Sesión de BD
        identity_id: ID de la identidad
        tipo: Filtrar por tipo (opcional)
        tenant_id: Filtrar por tenant (opcional)
    
    Returns:
        Authority si existe y está ACTIVA, None si no existe
    """
    query = db.query(Authority).filter(
        Authority.identity_id == identity_id,
        Authority.estado == GovStatus.ACTIVO
    )
    
    if tipo:
        query = query.filter(Authority.tipo == tipo)
    
    if tenant_id:
        query = query.filter(Authority.tenant_id == tenant_id)
    
    return query.first()


def tiene_authority(
    db: Session,
    identity_id: str,
    tipo: AuthorityType,
    tenant_id: Optional[str] = None
) -> bool:
    """
    Verifica si una identidad tiene AUP_AUTHORITY activa.
    
    Args:
        db: Sesión de BD
        identity_id: ID de la identidad
        tipo: Tipo de autoridad requerida
        tenant_id: Tenant específico (si aplica)
    
    Returns:
        True si tiene authority activa, False si no
    """
    return obtener_authority(db, identity_id, tipo, tenant_id) is not None


def revocar_authority(
    db: Session,
    authority_id: str,
    revocada_por: str,
    motivo: Optional[str] = None
) -> Authority:
    """
    Revoca una AUP_AUTHORITY.
    
    Axioma: Todo poder es revocable.
    
    Args:
        db: Sesión de BD
        authority_id: ID de la autoridad a revocar
        revocada_por: ID de la identity que revoca (debe tener poder superior)
        motivo: Razón de la revocación
    
    Returns:
        Authority revocada
    
    Raises:
        HTTPException 404: Si authority no existe
        HTTPException 400: Si ya está revocada
    """
    authority = db.query(Authority).filter(Authority.authority_id == authority_id).first()
    
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Authority {authority_id} no encontrada"
        )
    
    if authority.estado == GovStatus.REVOCADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authority {authority_id} ya está revocada"
        )
    
    # Revocar
    authority.estado = GovStatus.REVOCADO
    authority.revoked_at = datetime.utcnow()
    
    if motivo:
        if not authority.metadata_json:
            authority.metadata_json = {}
        authority.metadata_json["revoked_by"] = revocada_por
        authority.metadata_json["revoked_reason"] = motivo
    
    db.commit()
    db.refresh(authority)
    
    return authority


def listar_authorities(
    db: Session,
    tipo: Optional[AuthorityType] = None,
    tenant_id: Optional[str] = None,
    estado: GovStatus = GovStatus.ACTIVO
) -> list[Authority]:
    """
    Lista authorities filtradas.
    
    Args:
        db: Sesión de BD
        tipo: Filtrar por tipo (opcional)
        tenant_id: Filtrar por tenant (opcional)
        estado: Filtrar por estado (default: ACTIVO)
    
    Returns:
        Lista de authorities
    """
    query = db.query(Authority).filter(Authority.estado == estado)
    
    if tipo:
        query = query.filter(Authority.tipo == tipo)
    
    if tenant_id:
        query = query.filter(Authority.tenant_id == tenant_id)
    
    return query.order_by(Authority.created_at.desc()).all()


__all__ = [
    "crear_authority",
    "obtener_authority",
    "tiene_authority",
    "revocar_authority",
    "listar_authorities",
]
