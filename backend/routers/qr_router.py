"""Router de QR - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, HTTPException, Request
import logging
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, AccessLevel
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_visita, require_condominio
from backend.core.tenant.context import _set_postgres_tenant
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from backend.db.core import Visita, Usuario
from ..services import qr_service, visita_service
from backend.services.event_outbox import contexto_evento, rechazar_operacion
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
        rechazar_operacion(db, usuario, token, visita.condominio_id, visita_id,
            detail=f"Gobierno denegó operación: {motivo}", status_code=403,
            entidad="qr", accion="crear", motivo="Gobierno denegó la generación de QR")
    # ═══════════════════════════════════════════════════════════════════

    if visita.estado not in ["pendiente", "activa"]:
        rechazar_operacion(db, usuario, token, visita.condominio_id, visita_id,
            detail="No se puede generar QR para una visita cancelada o finalizada", entidad="qr", accion="crear")
    if visita.vigencia and qr_service.utc_now() >= qr_service.ventana_visita(visita.vigencia)[1]:
        rechazar_operacion(db, usuario, token, visita.condominio_id, visita_id,
            detail="La ventana de acceso de la visita ya terminó", entidad="qr", accion="crear")
    qr_data = qr_service.generar_qr_para_visita(visita_id, fecha_visita=visita.vigencia)
    tenant_id = visita.condominio_id
    try:
        visita_service.actualizar_qr(db, visita_id, qr_data["token"], qr_data["qr_vigencia"],
            auditoria=contexto_evento(usuario, token, entidad="qr", accion="crear", motivo="QR generado para visita"))
    except HTTPException as exc:
        if exc.status_code == 400:
            rechazar_operacion(db, usuario, token, tenant_id, visita_id,
                detail=str(exc.detail), entidad="qr", accion="crear")
        raise
    
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
    verificar_rol(usuario, ["GUARDIA", "MSP_ADMIN", "ADMIN_CONDOMINIO"])
    tenant_id = condominio_id or usuario.condominio_id
    if not tenant_id:
        raise HTTPException(400, "condominio_id requerido para esta operación")
    # Autorizar antes de registrar incluso una visita inexistente: ningún
    # parámetro del cliente puede elegir una bandeja ajena ni el tenant sistema.
    require_condominio(db, db_gov, usuario, tenant_id, AccessLevel.GUARDIA)
    _set_postgres_tenant(db, tenant_id)
    session_token = request.headers.get("Authorization", "").replace("Bearer ", "")

    def rechazar(detail, *, status_code=400, resultado="denegado"):
        rechazar_operacion(db, usuario, session_token, tenant_id, visita_id, detail=detail,
                          entidad="qr", accion="validar", status_code=status_code,
                          resultado=resultado, metadata={"visita_id": visita_id})

    try:
        visita = require_visita(db, db_gov, usuario, visita_id, AccessLevel.GUARDIA,
                               condominio_id=tenant_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            rechazar("Visita no encontrada", status_code=404, resultado="fallo")
        raise

    if visita.estado == "cancelada":
        rechazar("Visita cancelada; QR sin autorización de acceso")
    if visita.estado not in ["pendiente", "activa", "entrada_registrada", "salida_registrada"]:
        rechazar("Visita finalizada; QR sin autorización de acceso")
    if visita.qr_token != token:
        rechazar("QR inválido", resultado="fallo")

    now = qr_service.utc_now()
    window_start, window_end = qr_service.ventana_visita(visita.vigencia) if visita.vigencia else (None, None)
    if (not visita.qr_vigencia or now >= qr_service.as_utc(visita.qr_vigencia)
            or (window_end is not None and now >= window_end)):
        rechazar("QR expirado")
    if visita.estado in ["entrada_registrada", "salida_registrada"]:
        rechazar("QR ya utilizado")
    if window_start is not None and now < window_start:
        rechazar("QR aún no vigente; acceso desde 30 minutos antes de la visita")

    try:
        visita = visita_service.registrar_entrada(db, visita_id, qr_token=token,
            auditoria=contexto_evento(usuario, session_token, entidad="qr", accion="validar",
                                      motivo="QR validado y entrada registrada"))
    except HTTPException as exc:
        if exc.status_code == 400:
            rechazar(str(exc.detail))
        raise

    return {
        "status": "aprobado",
        "visita_id": visita_id,
        "nombre_visitante": visita.nombre_visitante,
        "casa_unidad": visita.casa_unidad,
        "condominio_id": visita.condominio_id,
    }
