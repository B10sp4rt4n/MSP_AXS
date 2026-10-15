"""Aviso opcional de entrada para el piloto o residentes vinculados en beta.

Best effort después del commit y de la respuesta HTTP. No autoriza accesos,
no comparte datos del visitante y no conserva credenciales en CORE/EVENT.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os

import httpx

logger = logging.getLogger("axs.alexa")
TOKEN_URL = "https://api.amazon.com/auth/o2/token"
EVENT_URL = "https://api.amazonalexa.com/v1/proactiveEvents/stages/development"


def programar_aviso(background_tasks, visita):
    """Sólo rutas autorizadas, tras confirmar una entrada ganadora en CORE."""
    try:
        if background_tasks is None or os.getenv("AXS_ALEXA_ENABLED", "").lower() != "true":
            return
        from backend.services import alexa_linking
        if alexa_linking.enabled():
            if (visita.destino_tipo == 'vivienda' and visita.destino_id
                    and visita.estado == 'entrada_registrada' and visita.entrada_registrada_en):
                background_tasks.add_task(enviar_aviso_vivienda, visita.condominio_id,
                                          visita.destino_id, visita.visita_id)
            return
        tenant = os.getenv("AXS_ALEXA_PILOT_CONDOMINIO_ID", "").strip()
        house = os.getenv("AXS_ALEXA_PILOT_CASA_ID", "").strip()
        user = os.getenv("AXS_ALEXA_PILOT_USER_ID", "").strip()
        if not tenant or not house or not user.startswith("amzn1.ask.account."):
            logger.warning("Alexa: configuración de vivienda piloto incompleta")
            return
        if (visita.condominio_id != tenant or visita.destino_id != house
                or visita.destino_tipo != "vivienda"
                or visita.estado != "entrada_registrada" or not visita.entrada_registrada_en):
            return
        # Copiar escalares; la tarea no usa ORM ni una sesión fuera del request.
        reference = "AXS" + hashlib.sha256(
            f"{tenant}:{house}:{visita.visita_id}:entrada".encode()
        ).hexdigest()
        background_tasks.add_task(enviar_aviso, user, reference)
    except Exception:
        logger.warning("Alexa: no se pudo programar el aviso")


def enviar_aviso(user, reference):
    """Un intento acotado. Un 202 confirma aceptación, no entrega al Echo."""
    if os.getenv("AXS_ALEXA_ENABLED", "").lower() != "true":
        return
    client_id = os.getenv("AXS_ALEXA_CLIENT_ID", "").strip()
    secret = os.getenv("AXS_ALEXA_CLIENT_SECRET", "").strip()
    if not client_id or not secret:
        logger.warning("Alexa: credenciales sin configurar")
        return
    try:
        with httpx.Client(timeout=httpx.Timeout(3.0), follow_redirects=False) as client:
            auth = client.post(TOKEN_URL, data={
                "grant_type": "client_credentials", "client_id": client_id,
                "client_secret": secret, "scope": "alexa::proactive_events",
            })
            auth.raise_for_status()
            token = auth.json()["access_token"]
            now = datetime.now(timezone.utc)
            response = client.post(EVENT_URL, headers={"Authorization": f"Bearer {token}"}, json={
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "referenceId": reference,
                "expiryTime": (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event": {"name": "AMAZON.MessageAlert.Activated", "payload": {
                    "state": {"status": "UNREAD", "freshness": "NEW"},
                    "messageGroup": {"creator": {"name": "AXS Condominios"}, "count": 1},
                }},
                "localizedAttributes": [],
                "relevantAudience": {"type": "Unicast", "payload": {"user": user}},
            })
            response.raise_for_status()
            if response.status_code != 202:
                logger.warning("Alexa: respuesta inesperada HTTP %s", response.status_code)
                return
            logger.info("Alexa: aviso de entrada aceptado por Amazon")
    except httpx.HTTPStatusError as exc:
        logger.warning("Alexa: aviso no aceptado HTTP %s", exc.response.status_code)
    except Exception:
        # No registrar cuerpos, excepciones, userId, tokens ni secretos.
        logger.warning("Alexa: fallo de envío; la entrada permanece registrada")


def enviar_aviso_vivienda(tenant, house, visit_id):
    """Reauthorize each recipient with fresh sessions after the entrance commit.

    Beta best effort, like the pilot: failures never roll back a gate entrance.
    No automatic retries or delivery guarantees.
    """
    from backend.db.core import AlexaAccount, SessionLocal_CORE
    from backend.db.gov import SessionLocal_GOV
    from backend.services import alexa_linking
    from backend.core.recovery_gate import recovery_allowed
    if not alexa_linking.enabled() or not recovery_allowed(core_factory=SessionLocal_CORE):
        return
    try:
        with SessionLocal_CORE() as db:
            keys = [r[0] for r in db.query(AlexaAccount.account_key).filter_by(
                condominio_id=tenant, casa_id=house).all()]
        for key in keys:
            try:
                with SessionLocal_CORE() as db, SessionLocal_GOV() as gov:
                    row = db.get(AlexaAccount, key)
                    if not alexa_linking.notifications_active(row):
                        continue
                    alexa_linking.authorized_resident(db, gov, resident=row.usuario_id,
                                                      tenant=tenant, house=house)
                    reference = 'AXS' + hashlib.sha256(f'{tenant}:{house}:{visit_id}:entrada'.encode()).hexdigest()
                    enviar_aviso(row.amazon_user_id, reference)
            except Exception:
                logger.warning('Alexa: destinatario no disponible para el aviso')
    except Exception:
        logger.warning('Alexa: no se pudo consultar la vinculación beta')
