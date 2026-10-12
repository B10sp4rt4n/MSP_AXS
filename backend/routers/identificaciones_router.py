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
    authorized(visita_id, condominio_id, db, db_gov, usuario)
    response.headers["Cache-Control"] = "private, no-store"
    return {"evidencias": service.describe(service.list_pairs(db, visita_id))}


@router.get("/{visita_id}/{evidencia_id}")
def photo(visita_id: str, evidencia_id: str, condominio_id: str, request: Request,
          db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
          usuario: Usuario = Depends(get_current_user)):
    visita = authorized(visita_id, condominio_id, db, db_gov, usuario)
    row = db.query(Evidencia).filter_by(visita_id=visita_id, evidencia_id=evidencia_id,
                                      categoria="identificacion").first()
    if not row or row.metadata_json.get("storage") != "vercel_blob_private":
        raise HTTPException(404, "Foto no encontrada")
    try:
        data = service.PrivateIdentityStore().read(row.archivo_url)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "No se pudo recuperar la foto; reintenta")
    encolar_evento(db, visita.condominio_id, evidencia_id, audit(request, usuario, "consultar"))
    db.commit()
    return Response(data, media_type="image/jpeg", headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
