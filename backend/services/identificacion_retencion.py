"""Read-only projection: no storage calls, deletion, or visit changes."""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from backend.db.core import Evidencia, Visita
from backend.services.qr_service import as_utc

DAYS = 30
MAX_ROWS = 10000
ZONE = ZoneInfo("America/Mexico_City")


def report(db, condominio_id: str, cutoff_date: date):
    if cutoff_date == date.max:
        raise HTTPException(422, "Selecciona una fecha de corte válida")
    cutoff = datetime.combine(cutoff_date + timedelta(days=1), time.min, ZONE).astimezone(timezone.utc)
    rows = db.query(
        Evidencia.visita_id, Evidencia.sub_tipo, Evidencia.created_at,
        Evidencia.metadata_json["storage"].as_string().label("storage"),
        Evidencia.metadata_json["captura_id"].as_string().label("captura_id"),
        Evidencia.metadata_json["condominio_id"].as_string().label("tenant"),
        Visita.estado, Visita.salida_registrada_en,
    ).join(Visita, Visita.visita_id == Evidencia.visita_id).filter(
        Visita.condominio_id == condominio_id, Evidencia.categoria == "identificacion",
    ).order_by(Evidencia.visita_id, Evidencia.id).limit(MAX_ROWS + 1).all()
    if len(rows) > MAX_ROWS:
        raise HTTPException(422, "El reporte supera 10,000 fotos; requiere una consulta paginada")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.visita_id].append(row)
    items = []
    counts = {"venceria": 0, "vigente": 0, "revision": 0, "posterior_al_corte": 0}
    for visit_id, pair in grouped.items():
        first = pair[0]
        item = {"visita_id": visit_id, "estado_visita": first.estado or "sin_dato", "fotos": len(pair),
                "capturada_en": None, "salida_en": None, "fecha_base": None,
                "venceria_en": None, "clasificacion": "revision", "motivo": ""}
        valid = (len(pair) == 2 and {row.sub_tipo for row in pair} == {"ine_frente", "ine_reverso"}
                 and all(row.storage == "vercel_blob_private" and row.tenant == condominio_id and row.created_at for row in pair)
                 and bool(first.captura_id) and all(row.captura_id == first.captura_id for row in pair))
        if not valid:
            item["motivo"] = "Par incompleto o referencias inconsistentes; revisión manual"
        else:
            captured = max(as_utc(row.created_at) for row in pair)
            exit_at = as_utc(first.salida_registrada_en) if first.salida_registrada_en else None
            item["capturada_en"] = captured.isoformat()
            item["salida_en"] = exit_at.isoformat() if exit_at else None
            if exit_at and exit_at < captured:
                item["motivo"] = "La captura es posterior a la salida; revisar antes de proponer eliminación"
            elif exit_at and first.estado != "salida_registrada":
                item["motivo"] = "Fecha de salida y estado de visita no coinciden; revisión manual"
            elif first.estado == "salida_registrada" and not exit_at:
                item["motivo"] = "Falta la fecha de salida; revisión manual"
            else:
                base = exit_at or captured
                try:
                    expires = base + timedelta(days=DAYS)
                except OverflowError:
                    item["motivo"] = "Fecha fuera de rango; revisión manual"
                else:
                    item["fecha_base"] = base.isoformat()
                    item["venceria_en"] = expires.isoformat()
                    item["motivo"] = "30 días desde la salida registrada" if exit_at else "30 días desde la captura, sin salida registrada"
                    item["clasificacion"] = "posterior_al_corte" if captured >= cutoff else "venceria" if expires < cutoff else "vigente"
        counts[item["clasificacion"]] += 1
        items.append(item)
    order = {"venceria": 0, "revision": 1, "vigente": 2, "posterior_al_corte": 3}
    items.sort(key=lambda item: (order[item["clasificacion"]], item["venceria_en"] or "", item["visita_id"]))
    return {"modo": "simulacion", "borrado_activado": False, "plazo_propuesto_dias": DAYS,
            "condominio_id": condominio_id, "fecha_corte": cutoff_date.isoformat(),
            "zona_horaria": ZONE.key, "generado_en": datetime.now(timezone.utc).isoformat(),
            "total_identificaciones": len(items), "total_fotos": len(rows), "resumen": counts,
            "nota": "Proyección con registros actuales. No consulta fotos ni valida incidencias o excepciones de conservación.",
            "items": items}
