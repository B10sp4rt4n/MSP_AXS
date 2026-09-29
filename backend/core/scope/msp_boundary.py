"""Autorización por proveedor y condominio para las rutas operativas."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.core import (
    AccessLevel, Condominio, MSPMembership, ScopeStatus, UserTenantScope, Usuario, Visita,
)
from backend.db.gov import Authority, AuthorityType, GovStatus
from backend.core.scope.validator import nivel_suficiente


def is_platform_operator(db_gov: Session, usuario: Usuario) -> bool:
    return db_gov.query(Authority.authority_id).filter(
        Authority.identity_id == usuario.usuario_id,
        Authority.tipo == AuthorityType.GLOBAL,
        Authority.estado == GovStatus.ACTIVO,
    ).first() is not None


def active_msp_ids(db: Session, usuario: Usuario) -> list[str]:
    if usuario.rol != "MSP_ADMIN":
        return []
    return [row[0] for row in db.query(MSPMembership.msp_id).filter(
        MSPMembership.usuario_id == usuario.usuario_id,
        MSPMembership.estado == "activo",
    ).all()]


def require_platform_operator(db_gov: Session, usuario: Usuario) -> None:
    if not is_platform_operator(db_gov, usuario):
        raise HTTPException(403, "Requiere autoridad de operador AX-S")


def require_msp_admin(db: Session, db_gov: Session, usuario: Usuario, msp_id: str) -> None:
    if is_platform_operator(db_gov, usuario):
        return
    if msp_id not in active_msp_ids(db, usuario):
        raise HTTPException(403, "Sin administración de este proveedor")


def require_condominio(
    db: Session, db_gov: Session, usuario: Usuario, condominio_id: str,
    level: AccessLevel,
) -> Condominio:
    condo = db.query(Condominio).filter(
        Condominio.condominio_id == condominio_id,
    ).first()
    if not condo:
        raise HTTPException(404, "Condominio no encontrado")
    if is_platform_operator(db_gov, usuario):
        return condo
    if condo.msp_id in active_msp_ids(db, usuario):
        return condo
    scopes = db.query(UserTenantScope).filter(
        UserTenantScope.usuario_id == usuario.usuario_id,
        UserTenantScope.tenant_id == condominio_id,
        UserTenantScope.estado == ScopeStatus.ACTIVO,
    ).all()
    if not any(nivel_suficiente(scope.access_level, level) for scope in scopes):
        raise HTTPException(403, "Sin acceso al condominio")
    return condo


def require_visita(
    db: Session, db_gov: Session, usuario: Usuario, visita_id: str,
    level: AccessLevel, *, own_unit: bool = False,
    condominio_id: str | None = None,
) -> Visita:
    # RLS impide descubrir el tenant leyendo la visita sin contexto. El tenant
    # proviene del usuario o de un parámetro explícito previamente autorizado.
    tenant_id = condominio_id or usuario.condominio_id
    if not tenant_id:
        raise HTTPException(400, "condominio_id requerido para esta operación")
    require_condominio(db, db_gov, usuario, tenant_id, level)
    from backend.core.tenant.context import _set_postgres_tenant
    _set_postgres_tenant(db, tenant_id)
    visita = db.query(Visita).filter(
        Visita.visita_id == visita_id, Visita.condominio_id == tenant_id,
    ).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    if own_unit and not (is_platform_operator(db_gov, usuario) or
                         visita.condominio_id in _admin_condominios(db, usuario) or
                         _is_msp_admin_for(db, usuario, visita.condominio_id)):
        if not usuario.casa_unidad or not usuario.condominio_id or (
            visita.casa_unidad != usuario.casa_unidad or
            visita.condominio_id != usuario.condominio_id
        ):
            raise HTTPException(403, "Sin acceso a esta vivienda")
    return visita


def _admin_condominios(db: Session, usuario: Usuario) -> set[str]:
    return {row[0] for row in db.query(UserTenantScope.tenant_id).filter(
        UserTenantScope.usuario_id == usuario.usuario_id,
        UserTenantScope.estado == ScopeStatus.ACTIVO,
        UserTenantScope.access_level.in_([AccessLevel.ADMIN_CONDOMINIO, AccessLevel.MSP_ADMIN]),
    ).all()}


def _is_msp_admin_for(db: Session, usuario: Usuario, condominio_id: str) -> bool:
    return db.query(Condominio).filter(
        Condominio.condominio_id == condominio_id,
        Condominio.msp_id.in_(active_msp_ids(db, usuario)),
    ).first() is not None
