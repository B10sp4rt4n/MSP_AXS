"""Transactional outbox para visitas; no requiere una transacción distribuida.

CORE confirma operación + evento juntos. EVENT recibe el mismo event_uid en
cada intento. La fila CORE se marca enviada sólo después del commit en EVENT.
"""
import asyncio
import logging
from datetime import datetime, timedelta
import uuid

from backend.db.core import Condominio, EventOutbox
from backend.db.event import Event
from backend.core.event.registry import calcular_hash_evento, hash_session_token
from backend.core.tenant.context import _set_postgres_tenant

logger = logging.getLogger("axs.outbox")


def contexto_evento(usuario, session_token, *, entidad="visita", accion="registrar", motivo=None):
    if not usuario or not usuario.usuario_id:
        raise ValueError("Auditoría sin identidad")
    return {"identity_id": usuario.usuario_id, "session_hash": hash_session_token(session_token),
            "entidad": entidad, "accion": accion, "motivo": motivo}


def encolar_evento(db, condominio_id, entidad_id, contexto, *, resultado="exito", metadata=None):
    """Sólo inserta; el llamador confirma junto con su operación o rechazo."""
    if not condominio_id or not entidad_id:
        raise ValueError("Auditoría sin condominio o entidad")
    event_uid = "evt_" + uuid.uuid4().hex
    now = datetime.utcnow()
    payload = {**contexto, "event_uid": event_uid, "tenant_id": condominio_id,
               "tipo_evento": contexto["accion"], "entidad_id": entidad_id,
               "resultado": resultado, "timestamp": now.isoformat(), "metadata_json": metadata}
    payload["hash_evento"] = calcular_hash_evento(
        event_uid, payload["identity_id"], payload["session_hash"], payload["tenant_id"],
        payload["entidad"], payload["entidad_id"], payload["accion"], payload["resultado"], now)
    db.add(EventOutbox(event_uid=event_uid, condominio_id=condominio_id,
                      payload=payload, created_at=now, next_attempt_at=now, attempts=0))
    db.flush()
    return event_uid


def encolar_visita(db, visita, contexto):
    """No hace commit: una falla aquí revierte también la operación de visita."""
    metadata = {"visita_id": visita.visita_id, "estado": visita.estado,
        "destino_id": visita.destino_id, "destino_tipo": visita.destino_tipo,
        "casa_unidad": visita.casa_unidad,
        "entrada_registrada_en": visita.entrada_registrada_en.isoformat() if visita.entrada_registrada_en else None,
        "salida_registrada_en": visita.salida_registrada_en.isoformat() if visita.salida_registrada_en else None}
    return encolar_evento(db, visita.condominio_id, visita.visita_id, contexto, metadata=metadata)


def rechazar_operacion(db, usuario, session_token, condominio_id, entidad_id, *, detail,
                      entidad="visita", accion="registrar", motivo=None, status_code=400,
                      resultado="denegado", metadata=None):
    """Usar sólo DESPUÉS de autorizar el condominio. Nunca confirma negocio pendiente.

    Cada solicitud rechazada es un intento distinto. Su UID se conserva en los
    reenvíos a EVENT. Un fallo de CORE mantiene el rechazo y devuelve 503.
    """
    from fastapi import HTTPException
    contexto = contexto_evento(usuario, session_token, entidad=entidad, accion=accion,
                               motivo=motivo or detail)
    try:
        db.rollback()
        _set_postgres_tenant(db, condominio_id)
        encolar_evento(db, condominio_id, entidad_id, contexto, resultado=resultado, metadata=metadata)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("No se pudo conservar el rechazo (%s)", type(exc).__name__)
        raise HTTPException(503, "Acceso rechazado; no se pudo conservar su auditoría") from exc
    raise HTTPException(status_code, detail)


def publicar_evento(db_event, payload):
    """INSERT sin UPDATE; conflicto por event_uid es un reintento, no otro hecho."""
    values = {**payload, "timestamp": datetime.fromisoformat(payload["timestamp"])}
    expected_hash = calcular_hash_evento(
        values["event_uid"], values["identity_id"], values["session_hash"], values["tenant_id"],
        values["entidad"], values["entidad_id"], values["accion"], values["resultado"], values["timestamp"])
    if expected_hash != values["hash_evento"]:
        raise ValueError("El evento pendiente no conserva su integridad")
    dialect = db_event.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError("Motor EVENT no soportado")
    db_event.execute(insert(Event).values(**values).on_conflict_do_nothing(index_elements=["event_uid"]))
    # No reconocer como enviado un event_uid existente con contenido diferente.
    existing = db_event.query(Event).filter_by(event_uid=values["event_uid"]).one()
    if any(getattr(existing, key) != value for key, value in values.items()):
        raise ValueError("El identificador ya existe con otro contenido")
    db_event.commit()


def enviar_pendientes(db, condominio_id, event_factory, *, limit=25, now=None, publisher=publicar_evento):
    """Cada worker toma filas de un tenant autorizado; SKIP LOCKED evita duplicar trabajo."""
    now = now or datetime.utcnow()
    _set_postgres_tenant(db, condominio_id)
    rows = db.query(EventOutbox).filter(
        EventOutbox.condominio_id == condominio_id, EventOutbox.delivered_at.is_(None),
        EventOutbox.next_attempt_at <= now,
    ).order_by(EventOutbox.created_at, EventOutbox.event_uid).limit(limit).with_for_update(skip_locked=True).all()
    delivered = 0
    for row in rows:
        row.attempts += 1
        try:
            if row.payload["tenant_id"] != row.condominio_id or row.payload["event_uid"] != row.event_uid:
                raise ValueError("El evento no coincide con su tenant o identificador")
            with event_factory() as db_event:
                publisher(db_event, row.payload)
            row.delivered_at = datetime.utcnow()
            row.last_error = None
            delivered += 1
        except Exception as exc:
            # No persistir mensajes que puedan contener conexión, credenciales o PII.
            row.last_error = type(exc).__name__
            row.next_attempt_at = now + timedelta(seconds=min(300, 2 ** min(row.attempts, 8)))
            logger.warning("Evento pendiente de reintento: %s (%s)", row.event_uid, row.last_error)
    db.commit()
    return delivered


def enviar_ciclo(core_factory, event_factory):
    # El worker interno enumera el catálogo; cada acceso a la bandeja usa RLS.
    with core_factory() as db:
        tenants = [r[0] for r in db.query(Condominio.condominio_id).all()]
    for tenant_id in tenants:
        try:
            with core_factory() as db:
                enviar_pendientes(db, tenant_id, event_factory)
        except Exception as exc:
            logger.warning("No se pudo procesar la bandeja (%s)", type(exc).__name__)

    # Cola global deliberadamente fuera de los recorridos por condominio.
    try:
        from backend.services.security_outbox import enviar_seguridad
        with core_factory() as db:
            enviar_seguridad(db, event_factory)
    except Exception as exc:
        logger.warning("No se pudo procesar seguridad (%s)", type(exc).__name__)


async def ejecutar_worker(core_factory, event_factory):
    while True:
        try:
            await asyncio.to_thread(enviar_ciclo, core_factory, event_factory)
        except Exception as exc:
            logger.warning("Worker de auditoría pendiente (%s)", type(exc).__name__)
        await asyncio.sleep(15)
