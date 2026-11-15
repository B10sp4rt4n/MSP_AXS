"""Corporate access v1: references only, no residential routes or biometrics."""
import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import Field
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, Usuario, CorporateMembership, CorporateSiteAssignment, CorporateDestination, EventOutbox
from backend.db.core.corporate_visits import CorporateVisit
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.corporate_boundary import require_corporate_member, ADMIN_ROLES, SITE_ROLES
from backend.routers.corporativo_router import enabled, private, StrictInput, require_site
from backend.services.event_outbox import contexto_evento, encolar_evento
from backend.core.tenant.company_lock import lock_company_query
from backend.db.core import Condominio
from backend.db.gov import get_gov_db


def visits_enabled():
    if os.getenv("AXS_CORPORATE_VISITS_ENABLED", "false").lower() != "true":
        raise HTTPException(404, "Visitas corporativas no disponibles")


router = APIRouter(prefix="/corporativo/{tenant_id}/sedes/{site_id}/visitas",
                   tags=["Visitas corporativas"],
                   dependencies=[Depends(enabled), Depends(visits_enabled), Depends(private)])
privacy_router = APIRouter(prefix="/arco-corporativo/{tenant_id}/visitas",
                           tags=["Privacidad corporativa"], dependencies=[Depends(private)])


class NewVisit(StrictInput):
    request_id: UUID
    destination_id: str = Field(min_length=1, max_length=40)
    host_user_id: str = Field(min_length=1, max_length=120)
    visitor_ref: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")


def view(row):
    return {k: getattr(row, k) for k in (
        "visit_id", "tenant_id", "site_id", "destination_id", "host_user_id", "visitor_ref",
        "state", "created_at", "authorized_at", "entered_at", "exited_at", "cancelled_at")}


@privacy_router.get("")
def privacy_visits(tenant_id: str, subject_ref: str = Query(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$"),
                   limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_core_db),
                   actor: Usuario = Depends(get_current_user),
                   gov: Session = Depends(get_gov_db)):
    from backend.core.scope.arco_boundary import require_arco_operator
    from sqlalchemy import inspect
    require_arco_operator(db, gov, actor, tenant_id)
    if not inspect(db.get_bind()).has_table("corporate_visits"):
        raise HTTPException(404, "Registro corporativo no instalado")
    return [view(row) for row in db.query(CorporateVisit).filter_by(
        tenant_id=tenant_id, visitor_ref=subject_ref).order_by(CorporateVisit.created_at, CorporateVisit.visit_id).limit(limit)]


def access(db, actor, tenant, site, roles=SITE_ROLES):
    return require_corporate_member(db, actor, tenant, site_id=site, allowed_roles=roles)


def host_valid(db, tenant, site, user_id):
    member = db.query(CorporateMembership).filter_by(tenant_id=tenant, user_id=user_id,
                                                    estado="activo").first()
    if not member or member.rol not in ADMIN_ROLES | {"host"}:
        raise HTTPException(409, "Anfitrion no disponible")
    if member.rol not in ADMIN_ROLES and not db.query(CorporateSiteAssignment).filter_by(
            tenant_id=tenant, site_id=site, user_id=user_id, estado="activo").first():
        raise HTTPException(409, "Anfitrion sin asignacion vigente")


def destination_valid(db, tenant, site, destination):
    require_site(db, tenant, site)
    if not db.query(CorporateDestination).filter_by(tenant_id=tenant, site_id=site,
            destination_id=destination, activa=True).with_for_update().first():
        raise HTTPException(404, "Destino no disponible en esta sede")


def audit(db, row, actor, request, action):
    # Never copy the visitor reference, name, credentials or identity evidence to EVENT.
    encolar_evento(db, row.tenant_id, row.visit_id, contexto_evento(actor,
        request.headers.get("Authorization", "").removeprefix("Bearer "),
        entidad="visita_corporativa", accion=action),
        metadata={"site_id": row.site_id, "state": row.state})


def load(db, tenant, site, visit, actor, member):
    row = db.query(CorporateVisit).filter_by(tenant_id=tenant, site_id=site,
                                           visit_id=str(visit)).with_for_update().first()
    if not row or (member.rol == "host" and row.host_user_id != actor.usuario_id):
        raise HTTPException(404, "Visita no encontrada")
    return row


@router.post("", status_code=201)
def create(tenant_id: str, site_id: str, body: NewVisit, request: Request,
           db: Session = Depends(get_core_db), actor: Usuario = Depends(get_current_user)):
    member = access(db, actor, tenant_id, site_id)
    if member.rol == "host" and body.host_user_id != actor.usuario_id:
        raise HTTPException(403, "Un anfitrion solo puede solicitar sus visitas")
    lock_company_query(db, db.query(Condominio).filter_by(condominio_id=tenant_id), tenant_id).one()
    existing = db.query(CorporateVisit).filter_by(tenant_id=tenant_id, visit_id=str(body.request_id)).first()
    if existing:
        if (existing.site_id, existing.destination_id, existing.host_user_id, existing.visitor_ref,
            existing.created_by) != (site_id, body.destination_id, body.host_user_id, body.visitor_ref, actor.usuario_id):
            raise HTTPException(409, "Identificador utilizado para otra solicitud")
        return view(existing)
    destination_valid(db, tenant_id, site_id, body.destination_id)
    host_valid(db, tenant_id, site_id, body.host_user_id)
    row = CorporateVisit(tenant_id=tenant_id, visit_id=str(body.request_id), site_id=site_id,
                         destination_id=body.destination_id, host_user_id=body.host_user_id,
                         visitor_ref=body.visitor_ref, created_by=actor.usuario_id)
    try:
        db.add(row)
        db.flush()
        audit(db, row, actor, request, "preregistrar")
        db.commit()
        db.refresh(row)
        return view(row)
    except Exception:
        db.rollback()
        raise


@router.get("")
def listing(tenant_id: str, site_id: str, limit: int = Query(50, ge=1, le=100),
            db: Session = Depends(get_core_db), actor: Usuario = Depends(get_current_user)):
    member = access(db, actor, tenant_id, site_id)
    query = db.query(CorporateVisit).filter_by(tenant_id=tenant_id, site_id=site_id)
    if member.rol == "host":
        query = query.filter_by(host_user_id=actor.usuario_id)
    return [view(row) for row in query.order_by(CorporateVisit.created_at.desc(), CorporateVisit.visit_id).limit(limit)]


@router.get("/capacidades")
def capabilities(tenant_id: str, site_id: str,
                 db: Session = Depends(get_core_db), actor: Usuario = Depends(get_current_user)):
    member = access(db, actor, tenant_id, site_id)
    require_site(db, tenant_id, site_id)
    candidates = db.query(CorporateMembership).filter(
        CorporateMembership.tenant_id == tenant_id, CorporateMembership.estado == "activo",
        CorporateMembership.rol.in_(ADMIN_ROLES | {"host"})).all()
    hosts = []
    for row in candidates:
        if member.rol == "host" and row.user_id != actor.usuario_id:
            continue
        if row.rol not in ADMIN_ROLES and not db.query(CorporateSiteAssignment).filter_by(
                tenant_id=tenant_id, site_id=site_id, user_id=row.user_id, estado="activo").first():
            continue
        user = db.query(Usuario).filter_by(usuario_id=row.user_id).first()
        if user:
            hosts.append({"user_id": row.user_id, "nombre": user.nombre or row.user_id})
    return {"role": member.rol, "hosts": hosts,
            "can_authorize": member.rol in ADMIN_ROLES | {"host"},
            "can_record_movement": member.rol in ADMIN_ROLES | {"reception"}}


@router.get("/{visit_id}")
def detail(tenant_id: str, site_id: str, visit_id: UUID,
           db: Session = Depends(get_core_db), actor: Usuario = Depends(get_current_user)):
    member = access(db, actor, tenant_id, site_id)
    return view(load(db, tenant_id, site_id, visit_id, actor, member))


@router.get("/{visit_id}/bitacora")
def history(tenant_id: str, site_id: str, visit_id: UUID,
            db: Session = Depends(get_core_db), actor: Usuario = Depends(get_current_user)):
    member = access(db, actor, tenant_id, site_id)
    load(db, tenant_id, site_id, visit_id, actor, member)
    rows = db.query(EventOutbox).filter_by(condominio_id=tenant_id).filter(
        EventOutbox.payload["entidad"].as_string() == "visita_corporativa",
        EventOutbox.payload["entidad_id"].as_string() == str(visit_id)).order_by(EventOutbox.created_at, EventOutbox.event_uid).all()
    return [{"event_uid": r.event_uid, "action": r.payload["accion"],
             "timestamp": r.created_at, "identity_id": r.payload["identity_id"]} for r in rows]


@router.patch("/{visit_id}/{action}")
def transition(tenant_id: str, site_id: str, visit_id: UUID, action: str, request: Request,
               db: Session = Depends(get_core_db), actor: Usuario = Depends(get_current_user)):
    states = {"autorizar": ("preregistrada", "autorizada", "authorized_at"),
              "entrada": ("autorizada", "dentro", "entered_at"),
              "salida": ("dentro", "cerrada", "exited_at"),
              "cancelar": (None, "cancelada", "cancelled_at")}
    if action not in states:
        raise HTTPException(404, "Operacion no disponible")
    roles = ADMIN_ROLES | ({"reception"} if action in {"entrada", "salida"} else {"host"})
    member = access(db, actor, tenant_id, site_id, roles)
    row = load(db, tenant_id, site_id, visit_id, actor, member)
    before, after, stamp = states[action]
    if row.state == after:
        return view(row)
    if (before and row.state != before) or (action == "cancelar" and row.state not in {"preregistrada", "autorizada"}):
        raise HTTPException(409, "Transicion no permitida")
    if action in {"autorizar", "entrada"}:
        destination_valid(db, tenant_id, site_id, row.destination_id)
        host_valid(db, tenant_id, site_id, row.host_user_id)
    try:
        row.state = after
        setattr(row, stamp, datetime.utcnow())
        if action == "autorizar":
            row.authorized_by = actor.usuario_id
        audit(db, row, actor, request, action)
        db.commit()
        db.refresh(row)
        return view(row)
    except Exception:
        db.rollback()
        raise
