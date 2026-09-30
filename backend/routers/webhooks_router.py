"""
Webhook de Clerk → crea/actualiza Usuario en AUP_CORE cuando Clerk registra un usuario.
"""
import os
import uuid
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from svix.webhooks import Webhook, WebhookVerificationError

from backend.db.core import get_core_db, Usuario
from fastapi import Depends

logger = logging.getLogger("axs.webhooks")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET", "")
DEFAULT_MSP_ID = os.getenv("DEFAULT_MSP_ID", "msp-axs")


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(None),
    svix_timestamp: str = Header(None),
    svix_signature: str = Header(None),
    db: Session = Depends(get_core_db),
):
    """
    Recibe eventos de Clerk y sincroniza usuarios en Neon.

    Eventos manejados:
      - user.created  → crea Usuario en AUP_CORE
      - user.updated  → actualiza nombre/email
      - user.deleted  → (no borra, solo loguea)
    """
    body = await request.body()

    import json
    # Verificar firma del webhook
    if CLERK_WEBHOOK_SECRET:
        try:
            wh = Webhook(CLERK_WEBHOOK_SECRET)
            wh.verify(body, {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            })
        except WebhookVerificationError:
            raise HTTPException(status_code=400, detail="Firma de webhook inválida")
    else:
        logger.warning("CLERK_WEBHOOK_SECRET no configurado — webhook sin verificar")

    # Parsear body independientemente del resultado de verify()
    payload = json.loads(body)

    event_type = payload.get("type")
    data = payload.get("data", {})
    clerk_id = data.get("id")

    logger.info(f"Clerk webhook: {event_type} — clerk_id={clerk_id}")

    if event_type == "user.created":
        # Extraer email primario
        emails = data.get("email_addresses", [])
        primary = data.get("primary_email_address_id")
        email_row = next((row for row in emails if row.get("id") == primary), emails[0] if emails else {})
        email = email_row.get("email_address")
        email = email.strip().lower() if email else None
        nombre = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or email

        if not email:
            logger.warning(f"Clerk user.created sin email: {clerk_id}")
            return {"ok": True, "skipped": "no email"}

        # No duplicar si ya existe
        existente = db.query(Usuario).filter(
            (Usuario.clerk_id == clerk_id) | (func.lower(Usuario.email) == email)
        ).first()

        if existente:
            # Vincular clerk_id si faltaba
            if not existente.clerk_id:
                existente.clerk_id = clerk_id
                db.commit()
                logger.info(f"clerk_id vinculado a usuario existente: {email}")
            return {"ok": True, "action": "linked"}

        # Crear nuevo Usuario
        nuevo = Usuario(
            usuario_id=str(uuid.uuid4()),
            clerk_id=clerk_id,
            email=email,
            nombre=nombre,
            rol="RESIDENTE",          # Rol por defecto — MSP_ADMIN lo cambia
            msp_id=DEFAULT_MSP_ID,
            password_hash=None,       # Auth via Clerk, no password local
        )
        db.add(nuevo)
        db.commit()
        logger.info(f"Usuario creado desde Clerk: {email} ({clerk_id})")
        return {"ok": True, "action": "created", "usuario_id": nuevo.usuario_id}

    if event_type == "user.updated":
        usuario = db.query(Usuario).filter(Usuario.clerk_id == clerk_id).first()
        if usuario:
            emails = data.get("email_addresses", [])
            email = emails[0]["email_address"] if emails else None
            nombre = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            if email:
                usuario.email = email
            if nombre:
                usuario.nombre = nombre
            db.commit()
            logger.info(f"Usuario actualizado desde Clerk: {clerk_id}")
        return {"ok": True, "action": "updated"}

    if event_type == "user.deleted":
        logger.info(f"Clerk user.deleted recibido para {clerk_id} — no se borra de Neon")
        return {"ok": True, "action": "ignored"}

    return {"ok": True, "action": "unhandled", "type": event_type}
