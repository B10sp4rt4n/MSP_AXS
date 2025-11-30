import qrcode
import io
import uuid
from datetime import datetime, timedelta
from ..core.config import settings


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
