from fastapi import APIRouter, Depends, HTTPException
import logging
from sqlalchemy.orm import Session
from ..core.dependencies import get_db, get_usuario_actual
from ..core.security import verificar_rol
from ..db.models import Visita
from ..services import qr_service, visita_service
import base64
from datetime import datetime

router = APIRouter(prefix="/qr", tags=["QR"]) 


@router.post("/generar/{visita_id}")
def generar_qr(
    visita_id: str,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "RESIDENTE"])
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")

    qr_data = qr_service.generar_qr_para_visita(visita_id)
    visita_service.actualizar_qr(db, visita_id, qr_data["token"], qr_data["qr_vigencia"])

    return {
        "status": "ok",
        "visita_id": visita_id,
        "qr_base64": base64.b64encode(qr_data["qr_bytes"]).decode(),
        "qr_vigencia": qr_data["qr_vigencia"],
    }


@router.get("/validar/{visita_id}/{token}")
def validar_qr(
    visita_id: str,
    token: str,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
    from ..db.models import Visita
    from datetime import datetime
    verificar_rol(usuario, ["GUARDIA"])

    logger = logging.getLogger("axs.qr")
    verificar_rol(usuario, ["GUARDIA"])

    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        logger.warning("QR validation failed: visita no encontrada", extra={"visita_id": visita_id, "user": getattr(usuario, "usuario_id", None)})
        raise HTTPException(404, "Visita no encontrada")

    if visita.qr_token != token:
        logger.warning("QR validation failed: token mismatch", extra={"visita_id": visita_id, "expected": visita.qr_token, "provided": token})
        raise HTTPException(400, "QR inválido")

    if not visita.qr_vigencia or visita.qr_vigencia < datetime.utcnow():
        logger.info("QR expired", extra={"visita_id": visita_id, "qr_vigencia": visita.qr_vigencia})
        raise HTTPException(400, "QR expirado")

    if visita.estado in ["entrada_registrada", "salida_registrada"]:
        logger.warning("QR already used", extra={"visita_id": visita_id, "estado": visita.estado})
        raise HTTPException(400, "QR ya utilizado")

    visita_service.registrar_entrada(db, visita_id)

    return {
        "status": "aprobado",
        "visita_id": visita_id,
        "nombre_visitante": visita.nombre_visitante,
        "casa_unidad": visita.casa_unidad,
        "condominio_id": visita.condominio_id,
    }
