"""Explicit registration invitations. Authorization stays in AXS, never in the email."""
import os
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException


def send_invitation(email: str) -> str:
    secret = os.getenv("CLERK_SECRET_KEY", "")
    redirect = os.getenv("CLERK_INVITATION_REDIRECT_URL", "")
    parsed = urlsplit(redirect)
    if not secret or parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise HTTPException(503, "Falta configurar el envío de invitaciones en el servidor")
    try:
        response = httpx.post(
            "https://api.clerk.com/v1/invitations",
            headers={"Authorization": f"Bearer {secret}"},
            json={"email_address": email, "redirect_url": redirect,
                  "notify": True, "expires_in_days": 7, "ignore_existing": False},
            timeout=10.0,
        )
    except httpx.RequestError:
        raise HTTPException(502, "No se pudo confirmar el envío. Consulta las invitaciones en Clerk antes de reintentar")
    if response.status_code == 429:
        raise HTTPException(429, "Clerk alcanzó su límite de invitaciones; intenta más tarde")
    if response.status_code in (409, 422):
        raise HTTPException(409, "Clerk no aceptó la invitación. Revisa si el correo ya tiene cuenta o una invitación pendiente")
    if response.status_code not in (200, 201):
        raise HTTPException(502, "Clerk no pudo aceptar la invitación")
    try:
        invitation_id = response.json()["id"]
        if not isinstance(invitation_id, str) or not invitation_id:
            raise ValueError()
        return invitation_id
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "No se pudo confirmar la invitación; revisa Clerk antes de reintentar")
