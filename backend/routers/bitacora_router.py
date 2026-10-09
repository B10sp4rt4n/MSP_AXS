"""Lectura de eventos entregados, autorizada por condominio antes de consultar EVENT."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import require_condominio
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import AccessLevel, EventOutbox, Usuario, get_core_db
from backend.db.event import Event
from backend.db.event.session import get_event_db
from backend.db.gov import get_gov_db
from backend.services.qr_service import as_utc

router = APIRouter(prefix="/bitacora", tags=["bitacora"])


@router.get("/{condominio_id}")
def listar(condominio_id: str, visita_id: str | None = None,
           antes_id: int | None = Query(None, ge=1), limite: int = Query(50, ge=1, le=100),
           usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_core_db),
           gov: Session = Depends(get_gov_db), event_db: Session = Depends(get_event_db)):
    require_condominio(db, gov, usuario, condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    _set_postgres_tenant(db, condominio_id)
    query = event_db.query(Event).filter(Event.tenant_id == condominio_id,
                                        Event.entidad.in_(["visita", "qr"]))
    pending = db.query(EventOutbox).filter(EventOutbox.condominio_id == condominio_id,
                                         EventOutbox.delivered_at.is_(None))
    if visita_id:
        query = query.filter(Event.entidad_id == visita_id)
    if antes_id:
        query = query.filter(Event.id < antes_id)
    rows = query.order_by(Event.id.desc()).limit(limite + 1).all()
    more = len(rows) > limite
    items = []
    for e in rows[:limite]:
        meta = e.metadata_json or {}
        items.append({"id": e.id, "event_uid": e.event_uid, "visita_id": e.entidad_id,
                      "fecha": as_utc(e.timestamp), "actor_id": e.identity_id,
                      "accion": e.accion, "resultado": e.resultado, "motivo": e.motivo,
                      **{key: meta.get(key) for key in ["estado", "autorizada_por", "proposito",
                          "entrada_registrada_en", "salida_registrada_en"]}})
    return {"items": items, "siguiente": rows[limite-1].id if more else None,
            "pendientes_entrega_condominio": pending.count()}
