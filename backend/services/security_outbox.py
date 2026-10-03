"""Bandeja global: no cambia tenant, no consulta visitas y no guarda credenciales."""
import logging
import uuid
from datetime import datetime, timedelta

from starlette.routing import Match
from backend.db.core import SecurityOutbox
from backend.db.core.session import SessionLocal_CORE
from backend.core.event.registry import calcular_hash_evento, hash_session_token

logger = logging.getLogger("axs.security_outbox")
SessionFactory = SessionLocal_CORE
DOMAIN = "PLATFORM_SECURITY"
REASONS = {"NO_SESSION", "INVALID_SESSION", "UNKNOWN_IDENTITY", "SCOPE_DENIED",
           "ROLE_DENIED", "MSP_DENIED", "PLATFORM_DENIED", "RESIDENCE_DENIED", "INVALID_CREDENTIALS"}


def ruta_segura(request):
    # Antes de autenticación aún no hay route en scope. Sólo evaluar patrones;
    # nunca ejecutar el endpoint ni guardar path_params, query o ruta raw.
    partial_path = None
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", "unknown_route")
        if match == Match.PARTIAL and partial_path is None:
            partial_path = getattr(route, "path", "unknown_route")
    # Sólo usar la coincidencia sin método cuando no existe una ruta completa.
    return partial_path or "unknown_route"


def guardar_intento(request, reason, *, factory=None):
    if reason not in REASONS:
        raise ValueError("Motivo de seguridad no permitido")
    identity = getattr(request.state, "verified_identity_id", None)
    token = getattr(request.state, "session_token", "") if identity else ""
    uid, now = "sec_" + uuid.uuid4().hex, datetime.utcnow()
    payload = {"event_uid": uid, "identity_id": identity or "NONE",
        "session_hash": hash_session_token(token), "tenant_id": DOMAIN,
        "tipo_evento": "denegar", "entidad": "scope" if identity else "session",
        "entidad_id": "request", "accion": "denegar", "resultado": "denegado",
        "motivo": reason, "timestamp": now.isoformat(),
        "metadata_json": {"route": ruta_segura(request), "method": request.method,
                          "reason": reason, "identity_verified": bool(identity)}}
    payload["hash_evento"] = calcular_hash_evento(uid, payload["identity_id"], payload["session_hash"],
        DOMAIN, payload["entidad"], "request", "denegar", "denegado", now)
    # Sesión independiente: no confirma ni revierte la transacción del request.
    with (factory or SessionFactory)() as db:
        db.add(SecurityOutbox(event_uid=uid, payload=payload, created_at=now,
                             attempts=0, next_attempt_at=now))
        db.commit()
    return uid


def enviar_seguridad(db, event_factory, *, limit=25, now=None, publisher=None):
    from backend.services.event_outbox import publicar_evento
    publisher = publisher or publicar_evento
    now = now or datetime.utcnow()
    rows = db.query(SecurityOutbox).filter(SecurityOutbox.delivered_at.is_(None),
        SecurityOutbox.next_attempt_at <= now).order_by(SecurityOutbox.created_at,
        SecurityOutbox.event_uid).limit(limit).with_for_update(skip_locked=True).all()
    delivered = 0
    for row in rows:
        row.attempts += 1
        try:
            p = row.payload
            if (p.get("tenant_id") != DOMAIN or p.get("event_uid") != row.event_uid
                    or p.get("accion") != "denegar" or p.get("resultado") != "denegado"
                    or p.get("motivo") not in REASONS):
                raise ValueError("Evento fuera del dominio de seguridad")
            with event_factory() as event_db:
                publisher(event_db, p)
            row.delivered_at, row.last_error = datetime.utcnow(), None
            delivered += 1
        except Exception as exc:
            row.last_error = type(exc).__name__
            row.next_attempt_at = now + timedelta(seconds=2 ** min(row.attempts, 8))
            logger.warning("Seguridad pendiente de envío: %s (%s)", row.event_uid, row.last_error)
    db.commit()
    return delivered
