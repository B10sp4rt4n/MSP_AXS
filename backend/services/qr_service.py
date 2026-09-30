import qrcode
import io
import uuid
import os
from datetime import datetime, timedelta, timezone
from ..core.config import settings

_QR_VIGENCIA_DEFAULT = int(os.getenv("QR_VIGENCIA_MINUTOS", "60"))


def utc_now():
    return datetime.now(timezone.utc)


def as_utc(value: datetime):
    # CORE legacy timestamps without timezone are UTC.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def ventana_visita(fecha_visita: datetime):
    scheduled = as_utc(fecha_visita)
    return scheduled - timedelta(minutes=30), scheduled + timedelta(minutes=60)


def imagen_qr(visita_id: str, token: str):
    img = qrcode.make(f"AXS|{visita_id}|{token}")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generar_qr_para_visita(visita_id: str, minutos_vigencia: int = _QR_VIGENCIA_DEFAULT,
                          *, fecha_visita: datetime | None = None):
    # normalize inputs
    visita_id = str(visita_id).strip()
    # cap vigencia to a reasonable maximum (e.g., 7 days)
    max_minutes = 60 * 24 * 7
    minutos_vigencia = max(1, min(int(minutos_vigencia), max_minutes))

    token = str(uuid.uuid4())[:10]
    qr_inicio = None
    if fecha_visita is not None:
        qr_inicio, expiration = ventana_visita(fecha_visita)
    else:
        expiration = utc_now() + timedelta(minutes=minutos_vigencia)
    # Keep CORE's timestamp-without-timezone storage in UTC.
    qr_vigencia = expiration.replace(tzinfo=None)

    return {
        "token": token,
        "qr_vigencia": qr_vigencia,
        "qr_bytes": imagen_qr(visita_id, token),
        "qr_inicio": qr_inicio,
    }
