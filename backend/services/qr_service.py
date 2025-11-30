import qrcode
import io
import uuid
from datetime import datetime, timedelta


def generar_qr_para_visita(visita_id: str, minutos_vigencia: int = 60):
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
