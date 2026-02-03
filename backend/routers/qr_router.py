"""Router de QR - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, HTTPException, Request
import logging
from sqlalchemy.orm import Session
from ..core.dependencies import get_db
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from backend.db.core import Visita, Usuario, QRCode
from ..services import qr_service, visita_service
from ..services.qr_share_service import QRShareService
from ..services.notification_service import notification_service
from pydantic import BaseModel
from ..core.event.registry import registrar_evento
from ..core.event import EventEntity, EventAction, EventResult
from ..core.gov.facade import puede_ejecutar_accion
import base64
import json
from datetime import datetime, timedelta

# ═════════════════════════════════════════════════════════════════
# Schemas para compartir QR
# ═════════════════════════════════════════════════════════════════
class CompartirWhatsAppRequest(BaseModel):
    visita_id: str
    phone_number: str  # Formato: +34XXXXXXXXX


class CompartirSMSRequest(BaseModel):
    visita_id: str
    phone_number: str


class CompartirEmailRequest(BaseModel):
    visita_id: str
    email: str


class ValidarAccesoCodigoRequest(BaseModel):
    codigo: str
    visita_id: str


class QRPublicoResponse(BaseModel):
    codigo: str
    visitante: str
    apartamento: str
    vigencia: str
    mensaje: str

router = APIRouter(prefix="/qr", tags=["QR"]) 


@router.post("/generar/{visita_id}")
def generar_qr(
    visita_id: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "RESIDENTE", "GUARDIA"])
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")

    # ═══════════════════════════════════════════════════════════════════
    # AUP_GOV: Evaluar política ANTES de generar QR
    # Axioma: Gobierno precede a operación
    # TEMPORAL: Saltamos validación GOV para GUARDIA (modo operativo básico)
    # ═══════════════════════════════════════════════════════════════════
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # Solo validar GOV si no es GUARDIA (GUARDIA tiene permisos operativos directos)
    if usuario.rol not in ["GUARDIA"]:
        # Calcular días de vigencia (del servicio QR)
        dias_vigencia = 7  # Default del sistema (puede venir de config)
        
        permitido, motivo = puede_ejecutar_accion(
            db=db,
            usuario=usuario,
            session_token=token,
            accion="generar_qr",
            tenant_id=visita.condominio_id,
            metadata={"dias_vigencia": dias_vigencia}
        )
        
        if not permitido:
            # AUP_GOV denegó la operación
            raise HTTPException(403, detail=f"Gobierno denegó operación: {motivo}")
    # ═══════════════════════════════════════════════════════════════════

    qr_data = qr_service.generar_qr_para_visita(visita_id)
    visita_service.actualizar_qr(db, visita_id, qr_data["token"], qr_data["qr_vigencia"])
    
    # AUP_EVENT: QR generado exitosamente
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
        # Notificación Slack: QR Inválido
        notification_service.enviar_qr_invalido(
            qr_code=token,
            tenant_id=visita.condominio_id,
            vigilante_id=usuario.usuario_id
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
        # Notificación Slack: QR Expirado
        notification_service.enviar_alerta_seguridad(
            titulo="QR Expirado Escaneado",
            descripcion=f"Se intentó usar un QR expirado\nVisita: {visita.nombre_visitante}\nExpiró: {visita.qr_vigencia.strftime('%Y-%m-%d %H:%M')}",
            tenant_id=visita.condominio_id,
            prioridad="normal",
            metadata={
                "vigilante": usuario.usuario_id,
                "visita_id": visita_id
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


# ═════════════════════════════════════════════════════════════════
# Nuevos Endpoints: Compartir QR
# ═════════════════════════════════════════════════════════════════

@router.post("/compartir/whatsapp")
def compartir_qr_whatsapp(
    data: CompartirWhatsAppRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Compartir QR de una visita por WhatsApp"""
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO"])
    
    visita = db.query(Visita).filter(Visita.visita_id == data.visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    codigo = qr_service.generar_codigo_alfanumerico()
    qr_data = qr_service.generar_qr_para_visita(visita.visita_id)
    qr_response = qr_service.qr_data_para_respuesta(
        qr_bytes=qr_data["qr_bytes"],
        vigencia=qr_data["qr_vigencia"],
        codigo=codigo,
        visita_id=visita.visita_id
    )
    
    result = qr_share_service.compartir_por_whatsapp(
        phone_number=data.phone_number,
        visitant_name=visita.nombre_visitante,
        qr_image_base64=qr_response["qr_image"],
        codigo=codigo,
        apartamento=visita.casa_unidad,
        vigencia=f"{(qr_data['qr_vigencia'] - datetime.utcnow()).seconds // 3600}h"
    )
    
    return {"status": "ok" if result["success"] else "error", "channel": "whatsapp", "result": result}


@router.post("/compartir/sms")
def compartir_qr_sms(
    data: CompartirSMSRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Compartir código QR por SMS"""
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO"])
    
    visita = db.query(Visita).filter(Visita.visita_id == data.visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    codigo = qr_service.generar_codigo_alfanumerico()
    result = qr_share_service.compartir_por_sms(
        phone_number=data.phone_number,
        codigo=codigo,
        apartamento=visita.casa_unidad
    )
    
    return {"status": "ok" if result["success"] else "error", "channel": "sms", "codigo": codigo}


@router.get("/acceso/{codigo}")
def acceso_publico_por_codigo(
    codigo: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint público para validar código QR sin autenticación
    Visitante puede ver su QR usando código alfanumérico
    
    Ejemplo: GET /qr/acceso/V-260201-123
    """
    # Buscar código en BD
    qr_record = db.query(QRCode).filter(QRCode.codigo == codigo).first()
    
    if not qr_record:
        raise HTTPException(404, "Código no encontrado")
    
    # Validar vigencia
    if qr_record.vigencia_hasta < datetime.utcnow():
        raise HTTPException(400, "Código expirado")
    
    # Validar que no esté usado
    if qr_record.usado:
        raise HTTPException(400, "Código ya utilizado")
    
    # Buscar visita
    visita = db.query(Visita).filter(Visita.visita_id == qr_record.visita_id).first()
    
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    return {
        "status": "ok",
        "codigo": codigo,
        "visitante": visita.nombre_visitante,
        "apartamento": visita.casa_unidad,
        "vigencia": qr_record.vigencia_hasta.isoformat(),
        "valido": True,
        "mensaje": "Código válido. Muestra este código al guardia para acceder."
    }


@router.post("/compartir/slack")
def compartir_qr_slack(
    data: CompartirSMSRequest,  # Reusar schema (solo necesita visita_id)
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Compartir código QR por Slack (notificación al equipo)"""
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO"])
    
    visita = db.query(Visita).filter(Visita.visita_id == data.visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    # Obtener webhook de Slack desde env
    import os
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    slack_channel = os.getenv("SLACK_CHANNEL")
    
    if not slack_webhook:
        raise HTTPException(400, "Slack no está configurado")
    
    codigo = qr_service.generar_codigo_alfanumerico()
    qr_data = qr_service.generar_qr_para_visita(visita.visita_id)
    
    result = qr_share_service.compartir_por_slack(
        webhook_url=slack_webhook,
        visitant_name=visita.nombre_visitante,
        codigo=codigo,
        apartamento=visita.casa_unidad,
        vigencia=f"{(qr_data['qr_vigencia'] - datetime.utcnow()).seconds // 3600}h",
        channel=slack_channel
    )
    
    return {"status": "ok" if result["success"] else "error", "channel": "slack", "codigo": codigo, "result": result}

@router.post("/qr/compartir/slack")
async def compartir_qr_slack(
    request: CompartirSMSRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Envía notificación de QR a canal de Slack
    """
    try:
        # Obtener información de la visita
        visita = db.query(Visita).filter(Visita.id == request.visita_id).first()
        if not visita:
            raise HTTPException(status_code=404, detail="Visita no encontrada")
        
        # Usar apartamento de la visita si está disponible
        apartamento = str(visita.apartamento_id) if visita.apartamento_id else "N/A"
        
        # Generar código alfanumérico
        from backend.services.qr_service import generar_codigo_alfanumerico
        codigo = generar_codigo_alfanumerico(db, visita.condominio_id)
        
        # Enviar por Slack
        qr_share = QRShareService(db)
        resultado = qr_share.compartir_por_slack(
            visita_id=visita.id,
            visitante=f"{visita.nombre} {visita.apellido}",
            apartamento=apartamento,
            codigo=codigo,
            vigencia_hasta=visita.fecha_fin,
            compartido_por_usuario_id=current_user.id
        )
        
        if resultado["success"]:
            # Registrar en AUP_EVENT
            from backend.db.event import AUPEvent
            evento = AUPEvent(
                timestamp=datetime.now(),
                event_type="QR_SLACK_ENVIADO",
                user_id=current_user.id,
                condominio_id=visita.condominio_id,
                payload=json.dumps({
                    "visita_id": visita.id,
                    "canal": resultado["canal"],
                    "codigo": codigo
                })
            )
            db.add(evento)
            db.commit()
            
            return {
                "status": "success",
                "canal": resultado["canal"],
                "codigo": codigo,
                "message": resultado["message"]
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=resultado["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

