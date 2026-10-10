"""Reporte administrativo de hechos recibidos, nunca de estados inferidos."""
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import require_condominio
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import AccessLevel, EventOutbox, Usuario, get_core_db
from backend.db.event import Event
from backend.db.event.session import get_event_db
from backend.db.gov import get_gov_db
from backend.services.qr_service import as_utc

router = APIRouter(prefix="/reportes", tags=["reportes"])
ZONA = ZoneInfo("America/Mexico_City")
MAX_EVENTOS = 5000


def categoria(e):
    meta = e.metadata_json or {}
    if e.resultado == "denegado":
        return "rechazo"
    if e.resultado != "exito":
        return "otro"
    if e.entidad == "visita" and e.accion == "revocar":
        return "cancelacion"
    if e.entidad == "visita" and e.accion == "registrar" and meta.get("estado") == "salida_registrada":
        return "salida"
    if ((e.entidad == "qr" and e.accion == "validar") or
            (e.entidad == "visita" and e.accion in ("crear", "registrar"))) and meta.get("estado") == "entrada_registrada":
        return "entrada"
    return "otro"


@router.get("/{condominio_id}/operacion")
def operacion(
    condominio_id: str, desde: date, hasta: date,
    estado: Literal["pendiente", "activa", "entrada_registrada", "salida_registrada", "cancelada"] | None = None,
    destino: str | None = Query(None, max_length=200),
    actor_id: str | None = Query(None, max_length=200),
    formato: Literal["json", "xlsx", "pdf"] = "json",
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_core_db),
    gov: Session = Depends(get_gov_db), event_db: Session = Depends(get_event_db),
):
    condo = require_condominio(db, gov, usuario, condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    _set_postgres_tenant(db, condominio_id)
    if hasta < desde or (hasta - desde).days > 30 or hasta == date.max:
        raise HTTPException(422, "Selecciona un periodo de 1 a 31 días")
    inicio = datetime.combine(desde, time.min, ZONA).astimezone(timezone.utc).replace(tzinfo=None)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, ZONA).astimezone(timezone.utc).replace(tzinfo=None)
    query = event_db.query(Event).filter(
        Event.tenant_id == condominio_id, Event.entidad.in_(["visita", "qr"]),
        Event.timestamp >= inicio, Event.timestamp < fin,
    )
    if estado:
        query = query.filter(Event.metadata_json["estado"].as_string() == estado)
    if destino:
        query = query.filter(Event.metadata_json["casa_unidad"].as_string() == destino)
    if actor_id:
        query = query.filter(Event.identity_id == actor_id)
    rows = query.order_by(Event.timestamp.desc(), Event.id.desc()).limit(MAX_EVENTOS + 1).all()
    if len(rows) > MAX_EVENTOS:
        raise HTTPException(422, "El reporte supera 5,000 eventos; reduce el periodo o aplica filtros")
    items = []
    resumen = {"entrada": 0, "salida": 0, "cancelacion": 0, "rechazo": 0, "otro": 0}
    for e in rows:
        meta = e.metadata_json or {}
        tipo = categoria(e)
        resumen[tipo] += 1
        items.append({"id": e.id, "fecha": as_utc(e.timestamp).isoformat(),
                      "visita_id": e.entidad_id, "actor_id": e.identity_id,
                      "categoria": tipo, "accion": e.accion, "resultado": e.resultado,
                      "motivo": e.motivo, "estado": meta.get("estado"),
                      "destino": meta.get("casa_unidad"), "proposito": meta.get("proposito")})
    pending = db.query(EventOutbox).filter(EventOutbox.condominio_id == condominio_id,
                                         EventOutbox.delivered_at.is_(None)).count()
    data = {"condominio_id": condominio_id, "condominio": condo.nombre,
            "desde": desde.isoformat(), "hasta": hasta.isoformat(), "zona_horaria": ZONA.key,
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "filtros": {"estado": estado, "destino": destino, "actor_id": actor_id},
            "pendientes_entrega_condominio": pending, "total": len(items),
            "resumen": resumen, "items": items}
    headers = {"Cache-Control": "no-store"}
    if formato == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(data, headers=headers)
    from backend.services.reportes_export import exportar
    content, media = exportar(data, formato)
    headers["Content-Disposition"] = f'attachment; filename="AXS-operacion-{desde}-{hasta}.{formato}"'
    return Response(content, media_type=media, headers=headers)
