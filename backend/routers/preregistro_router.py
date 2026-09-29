"""Router de Preregistro - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, AccessLevel
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_condominio, require_visita
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from ..services import visita_service, qr_service
from ..schemas.preregistro import PreregistroCreate
from backend.db.core import Usuario
from ..core.gov.facade import puede_ejecutar_accion
import base64
from datetime import datetime
import logging

logger = logging.getLogger("axs.preregistro")

router = APIRouter(prefix="/preregistro", tags=["Preregistro"])


@router.post("/crear")
def crear_preregistro(
    data: PreregistroCreate,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["RESIDENTE", "MSP_ADMIN", "ADMIN_CONDOMINIO"])
    if not usuario.condominio_id or not usuario.casa_unidad:
        raise HTTPException(400, "Se requiere vivienda asignada")
    require_condominio(db, db_gov, usuario, usuario.condominio_id, AccessLevel.RESIDENTE)

    # ═══════════════════════════════════════════════════════════════════
    # AUP_GOV: Evaluar política ANTES de crear preregistro
    # Axioma: Gobierno precede a operación
    # ═══════════════════════════════════════════════════════════════════
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    dias_vigencia = 7  # Default del sistema
    
    permitido, motivo = puede_ejecutar_accion(
        db=db,
        usuario=usuario,
        session_token=token,
        accion="generar_qr",
        tenant_id=usuario.condominio_id,
        metadata={"dias_vigencia": dias_vigencia}
    )
    
    if not permitido:
        raise HTTPException(403, detail=f"Gobierno denegó preregistro: {motivo}")
    # ═══════════════════════════════════════════════════════════════════

    try:
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
    except Exception as exc:
        logger.exception("Failed to create preregistro")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creando preregistro") from exc


@router.get("/qr/{visita_id}")
def reenviar_qr(
    visita_id: str,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["RESIDENTE", "MSP_ADMIN", "ADMIN_CONDOMINIO"])

    level = AccessLevel.RESIDENTE if usuario.rol == "RESIDENTE" else AccessLevel.ADMIN_CONDOMINIO
    visita = require_visita(db, db_gov, usuario, visita_id, level,
                           own_unit=usuario.rol == "RESIDENTE")

    # Si el QR no existe o está expirado, regenerar
    if not visita.qr_token or not visita.qr_vigencia or visita.qr_vigencia < datetime.utcnow():
        qr_data = qr_service.generar_qr_para_visita(visita.visita_id)
        visita_service.actualizar_qr(db, visita.visita_id, qr_data["token"], qr_data["qr_vigencia"])
    else:
        # Construir el QR actual
        remaining_minutes = max(
            int((visita.qr_vigencia - datetime.utcnow()).total_seconds() / 60),
            1
        )
        img_blob = qr_service.generar_qr_para_visita(
            visita.visita_id,
            minutos_vigencia=remaining_minutes
        )
        qr_data = {
            "token": visita.qr_token,
            "qr_vigencia": visita.qr_vigencia,
            "qr_bytes": img_blob["qr_bytes"]
        }

    return {
        "status": "ok",
        "visita_id": visita_id,
        "qr_base64": base64.b64encode(qr_data["qr_bytes"]).decode(),
        "qr_vigencia": qr_data["qr_vigencia"],
    }
