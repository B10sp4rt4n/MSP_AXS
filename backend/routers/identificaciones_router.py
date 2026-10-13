"""Scoped ID capture and authenticated delivery; never expose provider URLs."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session
from backend.db.core import AccessLevel, Evidencia, Usuario, get_core_db
from backend.db.gov import get_gov_db
from backend.core.auth.dependencies import get_current_user
from backend.core.security import verificar_rol
from backend.core.scope.msp_boundary import require_visita
from backend.services import identificacion_service as service
from backend.services.event_outbox import contexto_evento, encolar_evento
from backend.services import identificacion_conservacion as retention
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

router = APIRouter(prefix="/identificaciones", tags=["Identificaciones"])


def authorized(visita_id, condominio_id, db, db_gov, usuario):
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO", "MSP_ADMIN"])
    return require_visita(db, db_gov, usuario, visita_id, AccessLevel.GUARDIA,
                          condominio_id=condominio_id)


def audit(request, usuario, accion):
    return contexto_evento(usuario, request.headers.get("Authorization", "").removeprefix("Bearer "),
                           entidad="evidencia", accion=accion, motivo="Identificación de visita")


@router.post("/{visita_id}")
def upload(visita_id: str, request: Request, condominio_id: str,
           nombre: str = Form(..., max_length=200), captura_id: str = Form(..., max_length=36),
           frente: UploadFile = File(...), reverso: UploadFile = File(...),
           db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
           usuario: Usuario = Depends(get_current_user)):
    visita = authorized(visita_id, condominio_id, db, db_gov, usuario)
    rows = service.save_pair(db, visita, usuario, nombre, captura_id, frente, reverso,
                             audit(request, usuario, "registrar"))
    return {"status": "guardado", "evidencias": rows}


@router.get("/{visita_id}")
def listing(visita_id: str, condominio_id: str, response: Response,
            db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
            usuario: Usuario = Depends(get_current_user)):
    visit = authorized(visita_id, condominio_id, db, db_gov, usuario)
    response.headers["Cache-Control"] = "private, no-store"
    lifecycle = retention.access_record(db, visit)
    lifecycle_info = {"conservacion": retention.describe(lifecycle),
        "puede_gestionar_conservacion": bool(lifecycle and retention.pilot_enabled()
            and usuario.rol.upper() in {"ADMIN_CONDOMINIO", "MSP_ADMIN"} and lifecycle.state == "active")}
    rows = service.list_pairs(db, visita_id)
    if any((row.metadata_json or {}).get("purge_status") for row in rows):
        done = all((row.metadata_json or {}).get("purge_status") == "purged" for row in rows)
        return {"estado": "eliminada" if done else "eliminando", "evidencias": [],
                "eliminada_en": rows[0].metadata_json.get("purged_at") if done else None, **lifecycle_info}
    lifecycle_state = retention.state(lifecycle)
    if lifecycle_state in {"vencida", "eliminando", "eliminada", "revision"}:
        return {"estado": lifecycle_state, "evidencias": [], **lifecycle_info}
    return {"estado": "guardada" if rows else "sin_identificacion", "evidencias": service.describe(rows),
            **lifecycle_info}


@router.post("/{visita_id}/conservacion/ciclo-prueba")
def cycle_fixture(visita_id: str, condominio_id: str,
                  db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
                  usuario: Usuario = Depends(get_current_user)):
    """Bounded pilot trigger: never changes dates, enforces tenant/admin and fixture hash."""
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "MSP_ADMIN"])
    visit = require_visita(db, db_gov, usuario, visita_id, AccessLevel.ADMIN_CONDOMINIO, condominio_id=condominio_id)
    retention.require_pilot()
    row = retention.lookup(db, visit)
    if not row or row.policy_version != retention.VERSION or condominio_id not in retention.TENANTS:
        raise HTTPException(404, "Identificación fuera del piloto")
    # Claim only the requested visit; same path as the periodic worker.
    db.rollback()
    from backend.db.core import SessionLocal_CORE
    with SessionLocal_CORE() as session:
        claims = retention.claim(session, condominio_id, visit_id=visita_id)
    results = [retention.process(SessionLocal_CORE, condominio_id, *item) for item in claims]
    return Response(__import__("json").dumps({"reclamados":len(claims),"completados":sum(results),"solo_prueba":True}),
                    media_type="application/json", headers={"Cache-Control":"private, no-store"})


class HoldInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hasta: datetime
    responsable: str = Field(min_length=1, max_length=200)
    incidencia: str = Field(min_length=1, max_length=100)
    motivo: str = Field(min_length=1, max_length=500)

    @field_validator("hasta")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None:
            raise ValueError("La fecha límite debe incluir zona horaria")
        return value


@router.put("/{visita_id}/conservacion/excepcion")
def hold(visita_id: str, condominio_id: str, payload: HoldInput, request: Request, response: Response,
         db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
         usuario: Usuario = Depends(get_current_user)):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "MSP_ADMIN"])
    visit = require_visita(db, db_gov, usuario, visita_id, AccessLevel.ADMIN_CONDOMINIO, condominio_id=condominio_id)
    response.headers["Cache-Control"] = "private, no-store"
    return retention.set_hold(db, visit, audit(request, usuario, "conservar_identificacion_por_incidencia"),
        until=payload.hasta, owner=payload.responsable, incident=payload.incidencia, reason=payload.motivo)


@router.delete("/{visita_id}/conservacion/excepcion")
def release_hold(visita_id: str, condominio_id: str, request: Request, response: Response,
                 db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
                 usuario: Usuario = Depends(get_current_user)):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "MSP_ADMIN"])
    visit = require_visita(db, db_gov, usuario, visita_id, AccessLevel.ADMIN_CONDOMINIO, condominio_id=condominio_id)
    response.headers["Cache-Control"] = "private, no-store"
    return retention.set_hold(db, visit, audit(request, usuario, "liberar_conservacion_identificacion"))


@router.delete("/{visita_id}/borrado-prueba")
def borrar_ficticia(visita_id: str, condominio_id: str, request: Request,
                   db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
                   usuario: Usuario = Depends(get_current_user)):
    from backend.services.identificacion_borrado_prueba import gate, purge
    gate()
    def authorize():
        return require_visita(db, db_gov, usuario, visita_id, AccessLevel.ADMIN_CONDOMINIO, condominio_id=condominio_id)
    context = contexto_evento(usuario, request.headers.get("Authorization", "").removeprefix("Bearer "),
                             entidad="visita", accion="eliminar_identificacion_prueba",
                             motivo="Eliminación de fotografías ficticias en Development")
    return purge(db, usuario, authorize, context)


@router.get("/{visita_id}/{evidencia_id}")
def photo(visita_id: str, evidencia_id: str, condominio_id: str, request: Request,
          db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
          usuario: Usuario = Depends(get_current_user)):
    visita = authorized(visita_id, condominio_id, db, db_gov, usuario)
    retention.assert_readable(retention.access_record(db, visita))
    row = db.query(Evidencia).filter_by(visita_id=visita_id, evidencia_id=evidencia_id,
                                      categoria="identificacion").first()
    if not row or row.metadata_json.get("storage") != "vercel_blob_private":
        raise HTTPException(404, "Foto no encontrada")
    if row.metadata_json.get("purge_status"):
        raise HTTPException(410, "Esta fotografía fue retirada")
    key = row.archivo_url
    # Release read/tenant locks before remote I/O. Authorization and evidence
    # are checked again before delivery, including revocation during download.
    db.rollback()
    try:
        data = service.PrivateIdentityStore().read(key)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "No se pudo recuperar la foto; reintenta")
    visita = authorized(visita_id, condominio_id, db, db_gov, usuario)
    retention.assert_readable(retention.access_record(db, visita))
    current = db.query(Evidencia).filter_by(visita_id=visita_id, evidencia_id=evidencia_id,
                                          categoria="identificacion").first()
    if not current or current.archivo_url != key or current.metadata_json.get("storage") != "vercel_blob_private" or current.metadata_json.get("purge_status"):
        raise HTTPException(404, "Foto no encontrada")
    encolar_evento(db, visita.condominio_id, evidencia_id, audit(request, usuario, "consultar"))
    db.commit()
    return Response(data, media_type="image/jpeg", headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
