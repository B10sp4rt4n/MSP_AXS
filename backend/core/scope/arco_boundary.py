"""Explicit privacy authority, independent of corporate operational enablement."""
import os

from fastapi import HTTPException

from backend.core.scope.msp_boundary import require_condominio, is_platform_operator
from backend.core.security import verificar_rol
from backend.core.security_denial import SecurityDenial
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import AccessLevel, Condominio, CorporateMembership


def require_arco_operator(db, gov, user, tenant_id):
    from backend.core.tenant.company_lock import lock_company_query
    tenant = lock_company_query(db, db.query(Condominio).filter_by(condominio_id=tenant_id).populate_existing(), tenant_id).first()
    if tenant is None:
        raise HTTPException(404, "Cliente no encontrado")
    if tenant.modalidad == "residencial":
        # Preserve the residential contract, including effective grant provenance.
        require_condominio(db, gov, user, tenant_id, AccessLevel.ADMIN_CONDOMINIO, expected_mode=None)
        verificar_rol(user, ["ADMIN_CONDOMINIO", "MSP_ADMIN"])
    elif tenant.modalidad == "corporativo":
        # Corporate membership is RLS protected. Setting context is not a grant:
        # no dossier may be queried before membership AND designation succeed.
        _set_postgres_tenant(db, tenant_id)
        if is_platform_operator(gov, user):
            verificar_rol(user, ["ADMIN_CONDOMINIO", "MSP_ADMIN"])
        else:
            member = db.query(CorporateMembership).filter_by(
                tenant_id=tenant_id, user_id=user.usuario_id, estado="activo").first()
            if member is None:
                raise SecurityDenial(403, "Sin membresia corporativa vigente", reason="SCOPE_DENIED")
            if member.rol not in {"owner", "admin"}:
                raise SecurityDenial(403, "Funcion corporativa insuficiente para privacidad", reason="ROLE_DENIED")
        # Deliberately independent of business flags and corporativo_habilitado.
        # Suspension cannot remove an otherwise authorized privacy operator.
    else:
        raise SecurityDenial(403, "Modalidad de cliente no admitida", reason="TENANT_MODE_DENIED")
    allowed = {item.strip() for item in os.getenv("AXS_ARCO_OPERATORS", "").split(",") if item.strip()}
    if f"{user.usuario_id}:{tenant_id}" not in allowed:
        raise HTTPException(403, "Requiere designación de privacidad para este cliente")
    _set_postgres_tenant(db, tenant_id)
    return user
