"""Autorizacion corporativa independiente de Casa, RESIDENTE y niveles AUP legados.

Importante: el selector de tenant se usa SOLO para establecer el contexto RLS;
se consulta membership antes de leer/escribir informacion de la empresa.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.security_denial import SecurityDenial
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import (
    Condominio, CorporateMembership, CorporateSiteAssignment, Usuario,
)

ADMIN_ROLES = frozenset({"owner", "admin"})
SITE_ROLES = frozenset({"owner", "admin", "host", "reception"})


def require_corporate_member(
    db: Session, actor: Usuario, tenant_id: str, *, allowed_roles=frozenset(SITE_ROLES),
    site_id: str | None = None,
) -> CorporateMembership:
    """Una membresia vigente no se deduce del rol global ni de compartir correo."""
    if not tenant_id or not tenant_id.strip():
        raise HTTPException(400, "Empresa requerida")
    tenant_id = tenant_id.strip()
    # El contexto debe fijarse antes de consultar membresias sometidas a RLS.
    # No implica autorizacion: ninguna fila operativa se retorna sin membership.
    _set_postgres_tenant(db, tenant_id)
    member = db.query(CorporateMembership).filter(
        CorporateMembership.tenant_id == tenant_id,
        CorporateMembership.user_id == actor.usuario_id,
        CorporateMembership.estado == "activo",
    ).first()
    if not member:
        raise SecurityDenial(403, "Sin membresia corporativa vigente", reason="SCOPE_DENIED")
    tenant = db.query(Condominio).filter(Condominio.condominio_id == tenant_id).first()
    if not tenant or tenant.modalidad != "corporativo" or not tenant.corporativo_habilitado:
        raise SecurityDenial(403, "Operacion corporativa no habilitada", reason="CORPORATE_DISABLED")
    if member.rol not in allowed_roles:
        raise SecurityDenial(403, "Funcion corporativa insuficiente", reason="ROLE_DENIED")
    if site_id and member.rol not in ADMIN_ROLES:
        assigned = db.query(CorporateSiteAssignment).filter(
            CorporateSiteAssignment.tenant_id == tenant_id,
            CorporateSiteAssignment.site_id == site_id,
            CorporateSiteAssignment.user_id == actor.usuario_id,
            CorporateSiteAssignment.estado == "activo",
        ).first()
        if not assigned:
            raise SecurityDenial(403, "Sin asignacion a esta sede", reason="SCOPE_DENIED")
    return member
