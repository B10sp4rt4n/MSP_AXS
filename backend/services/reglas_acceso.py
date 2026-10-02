"""Validación de reglas en CORE, compartida por acceso manual y QR.

El bloqueo de la fila del condominio serializa cambios de configuración y
entradas. Nunca se toma autorización ni configuración del cuerpo del vigilante.
"""
from fastapi import HTTPException
from backend.db.core import Condominio
from backend.schemas.reglas_acceso import ReglasAcceso


def obtener_reglas(db, condominio_id, *, bloquear=False):
    query = db.query(Condominio).filter(Condominio.condominio_id == condominio_id)
    if bloquear:
        query = query.populate_existing().with_for_update()
    condo = query.one_or_none()
    if condo is None:
        raise HTTPException(404, "Condominio no encontrado")
    return condo, ReglasAcceso.model_validate(condo.reglas_acceso or {})


def validar_reglas(db, condominio_id, tipo_visita, proposito, *, entrada=False,
                   autorizada_por=None, autorizada_en=None, fecha_visita=None):
    _, reglas = obtener_reglas(db, condominio_id, bloquear=True)
    if not reglas.exigir_proposito and not reglas.exigir_autorizacion:
        return
    # Un tipo desconocido no puede utilizarse para evadir un filtro activo.
    if tipo_visita not in {"eventual", "frecuente", "visita_personal", "proveedor", "entrega"}:
        raise HTTPException(400, "Tipo de visita no reconocido para las reglas de este condominio")
    if tipo_visita not in reglas.tipos_visita:
        return
    if reglas.exigir_proposito and not (proposito or "").strip():
        raise HTTPException(403, "Este condominio exige el propósito de la visita")
    if entrada and reglas.exigir_autorizacion and (not autorizada_por or not autorizada_en):
        raise HTTPException(403, "Sin autorización previa: entrada no permitida")
    if entrada and reglas.exigir_autorizacion:
        from backend.services.qr_service import ventana_visita, utc_now
        if fecha_visita is None:
            raise HTTPException(403, "La autorización requiere fecha y hora de visita")
        inicio, fin = ventana_visita(fecha_visita)
        if not inicio <= utc_now() < fin:
            raise HTTPException(403, "La autorización está fuera de su horario de acceso")
