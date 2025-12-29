"""Router de QR - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, HTTPException, Request
import logging
from sqlalchemy.orm import Session
from ..core.dependencies import get_db
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from ..db.models import Visita, Usuario
from ..services import qr_service, visita_service
from ..core.event.registry import registrar_evento
from ..core.event import EventEntity, EventAction, EventResult
import base64
from datetime import datetime

router = APIRouter(prefix="/qr", tags=["QR"]) 


@router.post("/generar/{visita_id}")
def generar_qr(
    visita_id: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "RESIDENTE"])
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")

    qr_data = qr_service.generar_qr_para_visita(visita_id)
    visita_service.actualizar_qr(db, visita_id, qr_data["token"], qr_data["qr_vigencia"])
    
    # AUP_EVENT: QR generado exitosamente
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    registrar_evento(
        db=db,
        identity=usuario,
        session_token=token,
        tenant_id=visita.condominio_id,
        entidad=EventEntity.QR.value,
        entidad_id=qr_data["token"],
        accion=EventAction.CREAR.value,
        resultado=EventResult.EXITO.value,
        motivo="QR generado para visita",
        metadata={
            "visita_id": visita_id,
            "qr_vigencia": str(qr_data["qr_vigencia"])
        }
    )

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
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    logger = logging.getLogger("axs.qr")
    verificar_rol(usuario, ["GUARDIA"])

    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        logger.warning("QR validation failed: visita no encontrada", extra={"visita_id": visita_id, "user": getattr(usuario, "usuario_id", None)})
        # AUP_EVENT: Validación fallida (visita no encontrada)
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=session_token,
            tenant_id=usuario.condominio_id or "sistema",
            entidad=EventEntity.QR.value,
            entidad_id=token,
            accion=EventAction.VALIDAR.value,
            resultado=EventResult.FALLO.value,
            motivo="Visita no encontrada"
        )
        raise HTTPException(404, "Visita no encontrada")

    if visita.qr_token != token:
        logger.warning("QR validation failed: token mismatch", extra={"visita_id": visita_id, "expected": visita.qr_token, "provided": token})
        # AUP_EVENT: Validación fallida (token inválido)
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=session_token,
            tenant_id=visita.condominio_id,
            entidad=EventEntity.QR.value,
            entidad_id=token,
            accion=EventAction.VALIDAR.value,
            resultado=EventResult.FALLO.value,
            motivo="Token QR no coincide",
            metadata={"visita_id": visita_id}
        )
        raise HTTPException(400, "QR inválido")

    if not visita.qr_vigencia or visita.qr_vigencia < datetime.utcnow():
        logger.info("QR expired", extra={"visita_id": visita_id, "qr_vigencia": visita.qr_vigencia})
        # AUP_EVENT: Validación denegada (QR expirado)
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=session_token,
            tenant_id=visita.condominio_id,
            entidad=EventEntity.QR.value,
            entidad_id=token,
            accion=EventAction.VALIDAR.value,
            resultado=EventResult.DENEGADO.value,
            motivo="QR expirado",
            metadata={
                "visita_id": visita_id,
                "qr_vigencia": str(visita.qr_vigencia)
            }
        )
        raise HTTPException(400, "QR expirado")

    if visita.estado in ["entrada_registrada", "salida_registrada"]:
        logger.warning("QR already used", extra={"visita_id": visita_id, "estado": visita.estado})
        # AUP_EVENT: Validación denegada (QR ya usado)
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=session_token,
            tenant_id=visita.condominio_id,
            entidad=EventEntity.QR.value,
            entidad_id=token,
            accion=EventAction.VALIDAR.value,
            resultado=EventResult.DENEGADO.value,
            motivo="QR ya utilizado",
            metadata={"visita_id": visita_id, "estado": visita.estado}
        )
        raise HTTPException(400, "QR ya utilizado")

    visita_service.registrar_entrada(db, visita_id)
    
    # AUP_EVENT: Validación exitosa y entrada registrada
    session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    registrar_evento(
        db=db,
        identity=usuario,
        session_token=session_token,
        tenant_id=visita.condominio_id,
        entidad=EventEntity.QR.value,
        entidad_id=token,
        accion=EventAction.VALIDAR.value,
        resultado=EventResult.EXITO.value,
        motivo="QR validado y entrada registrada",
        metadata={
            "visita_id": visita_id,
            "visitante": visita.nombre_visitante,
            "casa_unidad": visita.casa_unidad
        }
    )

    return {
        "status": "aprobado",
        "visita_id": visita_id,
        "nombre_visitante": visita.nombre_visitante,
        "casa_unidad": visita.casa_unidad,
        "condominio_id": visita.condominio_id,
    }
