from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.dependencies import get_db, get_usuario_actual
from ..core.security import verificar_rol
from ..services import visita_service, qr_service
from ..schemas.preregistro import PreregistroCreate
import base64
from datetime import datetime

router = APIRouter(prefix="/preregistro", tags=["Preregistro"])


@router.post("/crear")
def crear_preregistro(
    data: PreregistroCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
    verificar_rol(usuario, ["RESIDENTE"])

    # Crear visita y persistir metadata opcional como evidencia
    visita = visita_service.crear_desde_preregistro(db, data, usuario)

    # Generar QR y guardar token/vigencia en la visita
    qr_data = qr_service.generar_qr_para_visita(visita.visita_id)
    visita_service.actualizar_qr(db, visita.visita_id, qr_data["token"], qr_data["qr_vigencia"])

    return {
        "status": "ok",
        "visita_id": visita.visita_id,
        "qr_base64": base64.b64encode(qr_data["qr_bytes"]).decode(),
        "qr_vigencia": qr_data["qr_vigencia"],
    }


@router.get("/qr/{visita_id}")
def reenviar_qr(
    visita_id: str,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
    verificar_rol(usuario, ["RESIDENTE"])

    from ..db.models import Visita

    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")

    # Solo el residente que creó la visita (o del mismo condominio) puede pedir reenvío
    if getattr(usuario, "condominio_id", None) != visita.condominio_id:
        raise HTTPException(403, "No autorizado para esta visita")

    # Si el QR no existe o está expirado, regenerar
    if not visita.qr_token or not visita.qr_vigencia or visita.qr_vigencia < datetime.utcnow():
        qr_data = qr_service.generar_qr_para_visita(visita.visita_id)
        visita_service.actualizar_qr(db, visita.visita_id, qr_data["token"], qr_data["qr_vigencia"])
    else:
        # Construir el QR actual
        qr_data = {"token": visita.qr_token, "qr_vigencia": visita.qr_vigencia}
        # Regenerar bytes for the QR image on demand
        img_blob = qr_service.generar_qr_para_visita(visita.visita_id, minutos_vigencia=int((visita.qr_vigencia - datetime.utcnow()).total_seconds() / 60))
        qr_data["qr_bytes"] = img_blob["qr_bytes"]

    return {
        "status": "ok",
        "visita_id": visita_id,
        "qr_base64": base64.b64encode(qr_data["qr_bytes"]).decode(),
        "qr_vigencia": qr_data["qr_vigencia"],
    }
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.dependencies import get_db, get_usuario_actual
from ..core.security import verificar_rol
from ..schemas.visita import PreregistroCreate
from ..services import visita_service, qr_service
import base64

router = APIRouter(prefix="/preregistro", tags=["Preregistro"])


@router.post("/crear")
def crear_preregistro(
    data: PreregistroCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
    verificar_rol(usuario, ["RESIDENTE"])

    class Obj:
        nombre_visitante = data.nombre_visitante
        tipo_visita = data.tipo_visita
        vigencia = data.fecha_visita

    visita = visita_service.crear_visita(
        db,
        Obj,
        condominio_id=usuario.condominio_id,
        casa_unidad=usuario.casa_unidad,
    )

    qr_data = qr_service.generar_qr_para_visita(visita.visita_id)
    visita_service.actualizar_qr(db, visita.visita_id, qr_data["token"], qr_data["qr_vigencia"])

    return {
        "status": "ok",
        "visita_id": visita.visita_id,
        "qr_base64": base64.b64encode(qr_data["qr_bytes"]).decode(),
        "qr_vigencia": qr_data["qr_vigencia"],
    }
from fastapi import APIRouter

router = APIRouter()


@router.post("/", tags=["preregistro"])
def preregistro(payload: dict):
    # placeholder: validar y crear preregistro
    return {"status": "ok", "payload": payload}
