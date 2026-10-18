"""Optional private photographs bound to an already confirmed exit."""
import hashlib
import logging
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session
from backend.db.core import Evidencia, Visita, Usuario, get_core_db
from backend.db.gov import get_gov_db
from backend.core.auth.dependencies import get_current_user
from backend.routers.identificaciones_router import authorized
from backend.services import identificacion_service as images
from backend.services.reglas_acceso import obtener_reglas
from backend.services.event_outbox import contexto_evento, encolar_evento

router = APIRouter(prefix="/evidencias-salida", tags=["Evidencias de salida"])
logger = logging.getLogger(__name__)


def context(request, user, action):
    return contexto_evento(user, request.headers.get("Authorization", "").removeprefix("Bearer "),
        entidad="evidencia", accion=action, motivo="Evidencia opcional de salida")


def describe(row):
    return {"evidencia_id": row.evidencia_id, "created_at": row.created_at.isoformat() + "Z",
            "salida_registrada_en": row.metadata_json["salida_registrada_en"], "guardia_id": row.guardia_id}


@router.post("/{visita_id}")
def upload(visita_id: str, condominio_id: str, request: Request,
           captura_id: uuid.UUID = Form(...), foto: UploadFile = File(...),
           db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
           user: Usuario = Depends(get_current_user)):
    visit = authorized(visita_id, condominio_id, db, gov, user)
    _, rules = obtener_reglas(db, condominio_id, bloquear=True)
    if rules.foto_salida == "deshabilitada":
        raise HTTPException(403, "La captura de salida está deshabilitada en este condominio")
    visit = db.query(Visita).filter_by(visita_id=visita_id, condominio_id=condominio_id).populate_existing().with_for_update().one()
    if visit.estado != "salida_registrada" or not visit.salida_registrada_en:
        raise HTTPException(409, "Confirma primero la salida de la visita")
    data = images.normalize_image(foto)
    digest = hashlib.sha256(data).hexdigest()
    existing = db.query(Evidencia).filter_by(visita_id=visita_id, categoria="salida").first()
    if existing:
        if existing.metadata_json.get("captura_id") == str(captura_id) and existing.hash_sha256 == digest:
            return describe(existing)
        raise HTTPException(409, "Esta salida ya tiene una fotografía guardada")
    eid = str(uuid.uuid4())
    key = f"axs-salidas/{hashlib.sha256(condominio_id.encode()).hexdigest()[:24]}/{eid}"
    store = images.PrivateIdentityStore()
    try:
        store.put(key, data)
        row = Evidencia(evidencia_id=eid, visita_id=visita_id, categoria="salida", sub_tipo="general",
            guardia_id=user.usuario_id, archivo_url=key, hash_sha256=digest, metadata_json={
                "storage": "vercel_blob_private", "captura_id": str(captura_id), "condominio_id": condominio_id,
                "salida_registrada_en": visit.salida_registrada_en.isoformat() + "Z"})
        db.add(row)
        encolar_evento(db, condominio_id, eid, context(request, user, "registrar"),
                      metadata={"visita_id": visita_id, "captura_id": str(captura_id)})
        db.flush()
        result = describe(row)
        db.commit()
        return result
    except Exception:
        db.rollback()
        try:
            store.delete(key)
        except Exception:
            logger.error("Exit photo rollback cleanup required: %s", key)
        raise HTTPException(503, "La salida sigue registrada. No se confirmó la foto; reintenta o continúa sin ella")


@router.get("/{visita_id}")
def listing(visita_id: str, condominio_id: str, response: Response,
            db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
            user: Usuario = Depends(get_current_user)):
    authorized(visita_id, condominio_id, db, gov, user)
    response.headers["Cache-Control"] = "private, no-store"
    return [describe(row) for row in db.query(Evidencia).filter_by(visita_id=visita_id, categoria="salida").all()]


@router.get("/{visita_id}/{evidencia_id}")
def photo(visita_id: str, evidencia_id: str, condominio_id: str, request: Request,
          db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
          user: Usuario = Depends(get_current_user)):
    authorized(visita_id, condominio_id, db, gov, user)
    def find():
        row = db.query(Evidencia).filter_by(visita_id=visita_id, evidencia_id=evidencia_id, categoria="salida").first()
        if not row or not row.archivo_url or (row.metadata_json or {}).get("purge_status"):
            raise HTTPException(404, "Foto no encontrada")
        return row
    key = find().archivo_url
    db.rollback()
    try:
        data = images.PrivateIdentityStore().read(key)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "No se pudo recuperar la foto; reintenta")
    authorized(visita_id, condominio_id, db, gov, user)
    if find().archivo_url != key:
        raise HTTPException(404, "Foto no encontrada")
    encolar_evento(db, condominio_id, evidencia_id, context(request, user, "consultar"))
    db.commit()
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
