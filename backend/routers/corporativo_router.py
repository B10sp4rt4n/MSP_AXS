"""AXS Corporativo C1: directorio de sedes y destinos, sin visitas ni hardware.

Inactivo por defecto: requiere AXS_CORPORATE_API_ENABLED=true y tenant habilitado
por aprovisionamiento privilegiado futuro. No crea casas ni usa rol RESIDENTE.
"""
import os
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.core.gov.policy import evaluar_politica
from backend.core.security_denial import SecurityDenial
from backend.core.scope.corporate_boundary import (
    ADMIN_ROLES, SITE_ROLES, require_corporate_member,
)
from backend.db.core import (
    Condominio, CorporateDestination, CorporateSite, CorporateSiteAssignment, Usuario, get_core_db,
)
from backend.db.gov import get_gov_db
from backend.services.event_outbox import contexto_evento, encolar_evento


def enabled():
    if os.getenv("AXS_CORPORATE_API_ENABLED", "").lower() != "true":
        raise HTTPException(404, "AXS Corporativo no disponible")


def private(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/corporativo/{tenant_id}", tags=["AXS Corporativo"],
    dependencies=[Depends(enabled), Depends(private)],
)


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NewSite(StrictInput):
    nombre: str = Field(min_length=2, max_length=120)
    zona_horaria: str = Field(default="America/Mexico_City", min_length=3, max_length=80)

    @field_validator("zona_horaria")
    @classmethod
    def valid_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Zona horaria IANA no reconocida") from exc
        return v


class NewDestination(StrictInput):
    nombre: str = Field(min_length=2, max_length=120)


def site_view(s: CorporateSite) -> dict:
    return {"site_id": s.site_id, "tenant_id": s.tenant_id,
            "nombre": s.nombre, "zona_horaria": s.zona_horaria, "activa": s.activa}


def destination_view(d: CorporateDestination) -> dict:
    return {"destination_id": d.destination_id, "tenant_id": d.tenant_id,
            "site_id": d.site_id, "nombre": d.nombre, "activa": d.activa}


def require_policy(db: Session, gov: Session, tenant_id: str, accion: str, count: int):
    """Sin política GOV de la empresa no hay alta; el rechazo es auditado por middleware."""
    allowed, _ = evaluar_politica(gov, accion, tenant_id=tenant_id, valor_actual=count)
    if not allowed:
        raise SecurityDenial(403, "Capacidad corporativa restringida por gobierno",
                             reason="CORPORATE_DISABLED")


def audit(db, tenant_id, row_id, user, request, entity):
    # No duplicar información del visitante/identificaciones en EVENT.
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    encolar_evento(db, tenant_id, row_id, contexto_evento(
        user, token, entidad=entity, accion="crear", motivo="Alta en directorio corporativo"),
        metadata={"tipo": entity})


@router.get("/sedes")
def sites(
    tenant_id: str,
    db: Session = Depends(get_core_db),
    actor: Usuario = Depends(get_current_user),
):
    member = require_corporate_member(db, actor, tenant_id, allowed_roles=SITE_ROLES)
    query = db.query(CorporateSite).filter_by(tenant_id=tenant_id)
    if member.rol not in ADMIN_ROLES:
        permitted = db.query(CorporateSiteAssignment.site_id).filter(
            CorporateSiteAssignment.tenant_id == tenant_id,
            CorporateSiteAssignment.user_id == actor.usuario_id,
            CorporateSiteAssignment.estado == "activo",
        )
        query = query.filter(CorporateSite.site_id.in_(permitted), CorporateSite.activa.is_(True))
    return [site_view(s) for s in query.order_by(CorporateSite.nombre, CorporateSite.site_id).all()]


@router.post("/sedes", status_code=201)
def create_site(
    tenant_id: str, body: NewSite, request: Request,
    db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
    actor: Usuario = Depends(get_current_user),
):
    require_corporate_member(db, actor, tenant_id, allowed_roles=ADMIN_ROLES)
    # Serializa el cupo de sedes por empresa antes de insertar.
    from backend.core.tenant.company_lock import lock_company_query
    lock_company_query(db, db.query(Condominio).filter_by(condominio_id=tenant_id), tenant_id).one()
    count = db.query(CorporateSite).filter_by(tenant_id=tenant_id, activa=True).count()
    require_policy(db, gov, tenant_id, "crear_sede_corporativa", count)
    row = CorporateSite(site_id="site_" + uuid.uuid4().hex[:24],
                        tenant_id=tenant_id, nombre=body.nombre,
                        zona_horaria=body.zona_horaria)
    try:
        db.add(row)
        audit(db, tenant_id, row.site_id, actor, request, "sede")
        db.commit()
        db.refresh(row)
        return site_view(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "No se pudo crear la sede") from exc
    except Exception:
        db.rollback()
        raise


def require_site(db: Session, tenant_id: str, site_id: str) -> CorporateSite:
    row = db.query(CorporateSite).filter(
        CorporateSite.tenant_id == tenant_id, CorporateSite.site_id == site_id,
        CorporateSite.activa.is_(True),
    ).first()
    if not row:
        raise HTTPException(404, "Sede no encontrada")
    return row


@router.get("/sedes/{site_id}/destinos")
def destinations(
    tenant_id: str, site_id: str,
    db: Session = Depends(get_core_db), actor: Usuario = Depends(get_current_user),
):
    require_corporate_member(db, actor, tenant_id, allowed_roles=SITE_ROLES, site_id=site_id)
    require_site(db, tenant_id, site_id)
    return [destination_view(d) for d in db.query(CorporateDestination).filter(
        CorporateDestination.tenant_id == tenant_id,
        CorporateDestination.site_id == site_id,
        CorporateDestination.activa.is_(True),
    ).order_by(CorporateDestination.nombre, CorporateDestination.destination_id).all()]


@router.post("/sedes/{site_id}/destinos", status_code=201)
def create_destination(
    tenant_id: str, site_id: str, body: NewDestination, request: Request,
    db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
    actor: Usuario = Depends(get_current_user),
):
    require_corporate_member(db, actor, tenant_id, allowed_roles=ADMIN_ROLES, site_id=site_id)
    # La sede bloqueada serializa altas al mismo catalogo.
    site = db.query(CorporateSite).filter_by(tenant_id=tenant_id, site_id=site_id,
                                             activa=True).with_for_update().first()
    if not site:
        raise HTTPException(404, "Sede no encontrada")
    count = db.query(CorporateDestination).filter_by(tenant_id=tenant_id,
                                                      site_id=site_id, activa=True).count()
    require_policy(db, gov, tenant_id, "crear_destino_corporativo", count)
    row = CorporateDestination(destination_id="area_" + uuid.uuid4().hex[:24],
                               tenant_id=tenant_id, site_id=site_id, nombre=body.nombre)
    try:
        db.add(row)
        audit(db, tenant_id, row.destination_id, actor, request, "destino_corporativo")
        db.commit()
        db.refresh(row)
        return destination_view(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Ya existe este destino o no pertenece a la sede") from exc
    except Exception:
        db.rollback()
        raise
