"""Private ARCO client selector; never enumerate the business directory."""
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.core.scope.arco_boundary import require_arco_operator
from backend.db.core import Condominio, Usuario, get_core_db
from backend.db.gov import get_gov_db
from backend.routers.arco_router import enabled, privacy

router = APIRouter(prefix="/arco-clientes", tags=["ARCO privado"],
                   dependencies=[Depends(enabled), Depends(privacy)])


@router.get("")
def clients(db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
            user: Usuario = Depends(get_current_user)):
    prefix = user.usuario_id + ":"
    designated = {item.strip()[len(prefix):] for item in os.getenv("AXS_ARCO_OPERATORS", "").split(",")
                  if item.strip().startswith(prefix) and item.strip()[len(prefix):]}
    if not designated:
        return []
    # IDs originate in explicit server-side designations, not caller input.
    # A designation alone is insufficient: recheck current effective authority.
    candidates = db.query(Condominio).filter(Condominio.condominio_id.in_(designated)).all()
    result = []
    for tenant in candidates:
        try:
            require_arco_operator(db, gov, user, tenant.condominio_id)
        except HTTPException as exc:
            if exc.status_code not in (403, 404):
                raise
            continue
        result.append({"tenant_id": tenant.condominio_id, "nombre": tenant.nombre,
                       "modalidad": tenant.modalidad})
    return sorted(result, key=lambda item: ((item["nombre"] or "").casefold(), item["tenant_id"]))
