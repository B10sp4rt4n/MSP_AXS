"""Authenticated resident inbox. No WhatsApp/Alexa transport or public reply URL."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, Usuario, AccessLevel, SolicitudAcceso
from backend.db.gov import get_gov_db
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import authorized_tenant_context
from backend.core.security import verificar_rol
from backend.core.gov.facade import puede_ejecutar_accion
from backend.services.event_outbox import contexto_evento
from backend.services import solicitudes_acceso as service
from backend.schemas.solicitud_acceso import SolicitarAcceso, ResponderAcceso

router = APIRouter(prefix="/solicitudes-acceso/{condominio_id}", tags=["Autorización remota"])


def contexto(request, usuario):
    return contexto_evento(usuario, request.headers.get("Authorization", "").removeprefix("Bearer "),
                          entidad="solicitud_acceso")


def no_cache(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


@router.post("", dependencies=[Depends(no_cache)])
def crear(condominio_id: str, data: SolicitarAcceso, request: Request,
          db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
          usuario: Usuario = Depends(get_current_user),
          _tenant: str = Depends(authorized_tenant_context(AccessLevel.GUARDIA))):
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO", "MSP_ADMIN"])
    allowed, reason = puede_ejecutar_accion(db=db, db_gov=db_gov, usuario=usuario,
        session_token=request.headers.get("Authorization", "").removeprefix("Bearer "),
        accion="crear_visita", tenant_id=condominio_id, metadata={"canal": "app"})
    if not allowed:
        raise HTTPException(403, f"Gobierno denegó: {reason}")
    return service.crear(db, condominio_id, data, usuario, contexto(request, usuario))


@router.get("", dependencies=[Depends(no_cache)])
def listar(condominio_id: str, request: Request,
           db: Session = Depends(get_core_db), usuario: Usuario = Depends(get_current_user),
           _tenant: str = Depends(authorized_tenant_context(AccessLevel.RESIDENTE))):
    verificar_rol(usuario, ["RESIDENTE", "GUARDIA", "ADMIN_CONDOMINIO", "MSP_ADMIN"])
    query = db.query(SolicitudAcceso).filter_by(condominio_id=condominio_id)
    if usuario.rol == "RESIDENTE":
        query = query.filter(SolicitudAcceso.destino_id == usuario.casa_id)
    # Pending inbox plus recent decisions, bounded for guard recovery after reload.
    rows = query.order_by(SolicitudAcceso.creada_en.desc()).limit(100).all()
    result = []
    for row in rows:
        if usuario.rol == "RESIDENTE" and not service.visible(db, row, usuario):
            continue
        service.expirar(db, row, contexto(request, usuario))
        result.append(service.vista(db, row))
    db.commit()
    return result


@router.get("/{solicitud_id}", dependencies=[Depends(no_cache)])
def obtener(condominio_id: str, solicitud_id: str, request: Request,
            db: Session = Depends(get_core_db), usuario: Usuario = Depends(get_current_user),
            _tenant: str = Depends(authorized_tenant_context(AccessLevel.RESIDENTE))):
    verificar_rol(usuario, ["RESIDENTE", "GUARDIA", "ADMIN_CONDOMINIO", "MSP_ADMIN"])
    row = service.obtener(db, condominio_id, solicitud_id)
    if usuario.rol == "RESIDENTE" and not service.visible(db, row, usuario):
        raise HTTPException(404, "Solicitud no encontrada")
    service.expirar(db, row, contexto(request, usuario))
    db.commit()
    return service.vista(db, row)


@router.post("/{solicitud_id}/respuesta", dependencies=[Depends(no_cache)])
def responder(condominio_id: str, solicitud_id: str, data: ResponderAcceso, request: Request,
              db: Session = Depends(get_core_db), usuario: Usuario = Depends(get_current_user),
              _tenant: str = Depends(authorized_tenant_context(AccessLevel.RESIDENTE))):
    verificar_rol(usuario, ["RESIDENTE"])
    row = service.obtener(db, condominio_id, solicitud_id)
    return service.responder(db, row, data, usuario, contexto(request, usuario))
