"""Router de Preregistro - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, AccessLevel
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_condominio, require_visita
from backend.core.tenant.context import _set_postgres_tenant
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from ..services import visita_service, qr_service
from backend.services.event_outbox import contexto_evento
from ..schemas.preregistro import PreregistroCreate
from backend.db.core import Usuario
from ..core.gov.facade import puede_ejecutar_accion
import base64
from datetime import datetime
import logging

logger = logging.getLogger("axs.preregistro")

router = APIRouter(prefix="/preregistro", tags=["Preregistro"])


@router.get("/reloj")
def reloj_servidor(usuario: Usuario = Depends(get_current_user)):
    return {"utc": qr_service.utc_now()}


@router.post("/crear")
def crear_preregistro(
    data: PreregistroCreate,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["RESIDENTE", "MSP_ADMIN", "ADMIN_CONDOMINIO"])
    residente = usuario.rol == "RESIDENTE"
    if residente:
        if not usuario.condominio_id or not usuario.casa_unidad:
            raise HTTPException(400, "Se requiere vivienda asignada")
        if data.condominio_id is not None and data.condominio_id != usuario.condominio_id:
            raise HTTPException(403, "El residente sólo puede preregistrar en su condominio")
        condominio_id = usuario.condominio_id
    else:
        if not data.condominio_id or not data.destino_id:
            raise HTTPException(400, "Selecciona condominio y destino para el preregistro administrativo")
        condominio_id = data.condominio_id

    require_condominio(db, db_gov, usuario, condominio_id,
                       AccessLevel.RESIDENTE if residente else AccessLevel.ADMIN_CONDOMINIO)
    _set_postgres_tenant(db, condominio_id)
    if not residente and data.destino_id == "OTRO":
        raise HTTPException(400, "El preregistro requiere un destino del catálogo")
    label, destination = visita_service.resolver_destino(
        db, condominio_id,
        destino_id=usuario.casa_id if residente else data.destino_id,
        casa_unidad=usuario.casa_unidad if residente else None, residente=residente,
    )
    if residente and data.destino_id is not None and data.destino_id != destination["destino_id"]:
        raise HTTPException(403, "El residente sólo puede preregistrar para su vivienda")
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
        tenant_id=condominio_id,
        metadata={"dias_vigencia": dias_vigencia},
        db_gov=db_gov,
    )
    
    if not permitido:
        raise HTTPException(403, detail=f"Gobierno denegó preregistro: {motivo}")
    # ═══════════════════════════════════════════════════════════════════

    if data.fecha_visita is None:
        data.fecha_visita = qr_service.utc_now().replace(tzinfo=None)
    try:
        # Crear visita y persistir metadata opcional como evidencia
        visita = visita_service.crear_desde_preregistro(db, data, usuario, destino=destination, casa_label=label, condominio_id=condominio_id,
            generar_qr=True, auditoria=contexto_evento(usuario, token, accion="crear", motivo="Visita preregistrada"))

        # Visita, QR y eventos se confirmaron juntos; renderizar el token guardado.
        qr_data = {"qr_bytes": qr_service.imagen_qr(visita.visita_id, visita.qr_token),
                   "qr_vigencia": visita.qr_vigencia,
                   "qr_inicio": qr_service.ventana_visita(visita.vigencia)[0]}

        return {
            "status": "ok",
            "visita_id": visita.visita_id,
            "qr_base64": base64.b64encode(qr_data["qr_bytes"]).decode(),
            "qr_vigencia": qr_service.as_utc(qr_data["qr_vigencia"]),
            "qr_inicio": qr_data["qr_inicio"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create preregistro")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creando preregistro") from exc


@router.get("/qr/{visita_id}")
def reenviar_qr(
    visita_id: str,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
    condominio_id: str | None = None,
):
    verificar_rol(usuario, ["RESIDENTE", "MSP_ADMIN", "ADMIN_CONDOMINIO"])

    level = AccessLevel.RESIDENTE if usuario.rol == "RESIDENTE" else AccessLevel.ADMIN_CONDOMINIO
    visita = require_visita(db, db_gov, usuario, visita_id, level,
                           own_unit=usuario.rol == "RESIDENTE", condominio_id=condominio_id)

    if visita.estado not in ["pendiente", "activa"]:
        raise HTTPException(400, "No se puede recuperar QR de una visita cancelada o finalizada")
    qr_inicio, window_end = qr_service.ventana_visita(visita.vigencia) if visita.vigencia else (None, None)
    if window_end is not None and qr_service.utc_now() >= window_end:
        raise HTTPException(400, "La ventana de acceso de la visita ya terminó")
    if not visita.qr_token or not visita.qr_vigencia or qr_service.as_utc(visita.qr_vigencia) <= qr_service.utc_now():
        qr_data = qr_service.generar_qr_para_visita(visita.visita_id, fecha_visita=visita.vigencia)
        visita_service.actualizar_qr(db, visita.visita_id, qr_data["token"], qr_data["qr_vigencia"],
            auditoria=contexto_evento(usuario, request.headers.get("Authorization", "").replace("Bearer ", ""),
                                      entidad="qr", accion="crear", motivo="QR generado al recuperar preregistro"))
    else:
        qr_data = {
            "token": visita.qr_token,
            "qr_vigencia": visita.qr_vigencia,
            "qr_inicio": qr_inicio,
            "qr_bytes": qr_service.imagen_qr(visita.visita_id, visita.qr_token),
        }

    return {
        "status": "ok",
        "visita_id": visita_id,
        "qr_base64": base64.b64encode(qr_data["qr_bytes"]).decode(),
        "qr_vigencia": qr_data["qr_vigencia"],
    }
