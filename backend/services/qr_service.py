import qrcode
import io
import uuid
import base64
from datetime import datetime, timedelta
from ..core.config import settings
import logging

logger = logging.getLogger("axs.qr_service")


def generar_qr_para_visita(visita_id: str, minutos_vigencia: int = 60):
    # normalize inputs
    visita_id = str(visita_id).strip()
    # cap vigencia to a reasonable maximum (e.g., 7 days)
    max_minutes = 60 * 24 * 7
    minutos_vigencia = max(1, min(int(minutos_vigencia), max_minutes))

    token = str(uuid.uuid4())[:10]
    qr_vigencia = datetime.utcnow() + timedelta(minutes=minutos_vigencia)
    payload = f"AXS|{visita_id}|{token}"

    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return {
        "token": token,
        "qr_vigencia": qr_vigencia,
        "qr_bytes": buffer.getvalue(),
    }

def generar_codigo_alfanumerico():
    """Generar código alfanumérico corto para entrada manual (ej: V-2026-0201-001)"""
    date_str = datetime.utcnow().strftime("%y%m%d")
    numero = str(uuid.uuid4().int)[:3]
    
    codigo = f"V-{date_str}-{numero}"
    return codigo


def qr_data_para_respuesta(qr_bytes: bytes, vigencia: datetime, codigo: str, visita_id: str):
    """
    Preparar datos del QR para respuesta JSON
    
    Retorna:
    {
        "qr_image": "data:image/png;base64,...",
        "qr_url": "https://app.axs.com/qr/...",
        "codigo": "V-2026-0201-001",
        "vigencia_hasta": "2026-02-01T15:30:00Z"
    }
    """
    qr_base64 = f"data:image/png;base64,{base64.b64encode(qr_bytes).decode()}"
    qr_url = f"{settings.FRONTEND_URL}/qr/{codigo}" if hasattr(settings, 'FRONTEND_URL') else f"/qr/{codigo}"
    
    return {
        "qr_image": qr_base64,
        "qr_url": qr_url,
        "codigo": codigo,
        "visita_id": visita_id,
        "vigencia_hasta": vigencia.isoformat(),
    }


def validar_qr_codigo(codigo: str, db_record) -> bool:
    """Validar que el código no ha expirado"""
    if not db_record:
        return False
    
    if datetime.utcnow() > db_record.vigencia_hasta:
        logger.warning(f"Código QR expirado: {codigo}")
        return False
    
    if hasattr(db_record, 'usado') and db_record.usado:
        logger.warning(f"Código QR ya fue usado: {codigo}")
        return False
    
    return True
