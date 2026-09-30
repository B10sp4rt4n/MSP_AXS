"""Router de QR - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, HTTPException, Request
import logging
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, AccessLevel
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_visita
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from backend.db.core import Visita, Usuario
from ..services import qr_service, visita_service
from ..core.event.registry import registrar_evento
from ..core.event import EventEntity, EventAction, EventResult
from ..core.gov.facade import puede_ejecutar_accion
import base64
from datetime import datetime, timedelta

router = APIRouter(prefix="/qr", tags=["QR"]) 


@router.post("/generar/{visita_id}")
def generar_qr(
    visita_id: str,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
    condominio_id: str | None = None,
):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "RESIDENTE"])
    level = AccessLevel.RESIDENTE if usuario.rol == "RESIDENTE" else AccessLevel.ADMIN_CONDOMINIO
    visita = require_visita(db, db_gov, usuario, visita_id, level,
                           own_unit=usuario.rol == "RESIDENTE", condominio_id=condominio_id)

    # ═══════════════════════════════════════════════════════════════════
    # AUP_GOV: Evaluar política ANTES de generar QR
    # Axioma: Gobierno precede a operación
    # ═══════════════════════════════════════════════════════════════════
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # Calcular días de vigencia (del servicio QR)
    dias_vigencia = 7  # Default del sistema (puede venir de config)
    
    permitido, motivo = puede_ejecutar_accion(
        db=db,
        usuario=usuario,
        session_token=token,
        accion="generar_qr",
        tenant_id=visita.condominio_id,
        metadata={"dias_vigencia": dias_vigencia},
        db_gov=db_gov,
    )
    
    if not permitido:
        # AUP_GOV denegó la operación
        raise HTTPException(403, detail=f"Gobierno denegó operación: {motivo}")
    # ═══════════════════════════════════════════════════════════════════

    if visita.estado not in ["pendiente", "activa"]:
        raise HTTPException(400, "No se puede generar QR para una visita cancelada o finalizada")
    if visita.vigencia and qr_service.utc_now() >= qr_service.ventana_visita(visita.vigencia)[1]:
        raise HTTPException(400, "La ventana de acceso de la visita ya terminó")
    qr_data = qr_service.generar_qr_para_visita(visita_id, fecha_visita=visita.vigencia)
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
        "qr_vigencia": qr_service.as_utc(qr_data["qr_vigencia"]),
        "qr_inicio": qr_data["qr_inicio"],
    }


@router.get("/validar/{visita_id}/{token}")
def validar_qr(
    visita_id: str,
    token: str,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
    condominio_id: str | None = None,
):
    logger = logging.getLogger("axs.qr")
    verificar_rol(usuario, ["GUARDIA", "MSP_ADMIN", "ADMIN_CONDOMINIO"])

    try:
        visita = require_visita(db, db_gov, usuario, visita_id, AccessLevel.GUARDIA,
                               condominio_id=condominio_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        logger.warning("QR validation failed: visita no encontrada", extra={"visita_id": visita_id, "user": getattr(usuario, "usuario_id", None)})
        # AUP_EVENT: Validación fallida (visita no encontrada)
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=session_token,
            tenant_id=condominio_id or usuario.condominio_id or "sistema",
            entidad=EventEntity.QR.value,
            entidad_id=token,
            accion=EventAction.VALIDAR.value,
            resultado=EventResult.FALLO.value,
            motivo="Visita no encontrada"
        )
        raise

    tenant_id = visita.condominio_id or usuario.condominio_id or "sistema"
    session_token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if visita.estado == "cancelada":
        raise HTTPException(400, "Visita cancelada; QR sin autorización de acceso")
    if visita.estado not in ["pendiente", "activa", "entrada_registrada", "salida_registrada"]:
        raise HTTPException(400, "Visita finalizada; QR sin autorización de acceso")

    if visita.qr_token != token:
        logger.warning("QR validation failed: token mismatch", extra={"visita_id": visita_id})
        try:
            registrar_evento(db=db, identity=usuario, session_token=session_token,
                tenant_id=tenant_id, entidad=EventEntity.QR.value, entidad_id=token,
                accion=EventAction.VALIDAR.value, resultado=EventResult.FALLO.value,
                motivo="Token QR no coincide", metadata={"visita_id": visita_id})
        except Exception:
            pass
        raise HTTPException(400, "QR inválido")

    now = qr_service.utc_now()
    window_start, window_end = qr_service.ventana_visita(visita.vigencia) if visita.vigencia else (None, None)
    if (not visita.qr_vigencia or now >= qr_service.as_utc(visita.qr_vigencia)
            or (window_end is not None and now >= window_end)):
        logger.info("QR expired", extra={"visita_id": visita_id})
        try:
            registrar_evento(db=db, identity=usuario, session_token=session_token,
                tenant_id=tenant_id, entidad=EventEntity.QR.value, entidad_id=token,
                accion=EventAction.VALIDAR.value, resultado=EventResult.DENEGADO.value,
                motivo="QR expirado", metadata={"visita_id": visita_id, "qr_vigencia": str(visita.qr_vigencia)})
        except Exception:
            pass
        raise HTTPException(400, "QR expirado")

    if visita.estado in ["entrada_registrada", "salida_registrada"]:
        logger.warning("QR already used", extra={"visita_id": visita_id, "estado": visita.estado})
        try:
            registrar_evento(db=db, identity=usuario, session_token=session_token,
                tenant_id=tenant_id, entidad=EventEntity.QR.value, entidad_id=token,
                accion=EventAction.VALIDAR.value, resultado=EventResult.DENEGADO.value,
                motivo="QR ya utilizado", metadata={"visita_id": visita_id, "estado": visita.estado})
        except Exception:
            pass
        raise HTTPException(400, "QR ya utilizado")

    if window_start is not None and now < window_start:
        raise HTTPException(400, "QR aún no vigente; acceso desde 30 minutos antes de la visita")

    visita = visita_service.registrar_entrada(db, visita_id, qr_token=token)

    try:
        registrar_evento(db=db, identity=usuario, session_token=session_token,
            tenant_id=tenant_id, entidad=EventEntity.QR.value, entidad_id=token,
            accion=EventAction.VALIDAR.value, resultado=EventResult.EXITO.value,
            motivo="QR validado y entrada registrada",
            metadata={"visita_id": visita_id, "visitante": visita.nombre_visitante, "casa_unidad": visita.casa_unidad})
    except Exception:
        pass

    return {
        "status": "aprobado",
        "visita_id": visita_id,
        "nombre_visitante": visita.nombre_visitante,
        "casa_unidad": visita.casa_unidad,
        "condominio_id": visita.condominio_id,
    }
