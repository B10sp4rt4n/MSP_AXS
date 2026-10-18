"""Progressive self-service identity. No provider calls or permission mutations."""
from datetime import datetime
import re
from typing import Literal
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, EmailStr, TypeAdapter, ValidationError, field_validator
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.db.core import Usuario, get_core_db
from backend.db.core.models import ExternalIdentity

router = APIRouter(prefix="/auth/me/identity", tags=["Identidad"])
Provider = Literal["whatsapp", "facebook", "instagram", "amazon"]
CONSENT_VERSION = "profile-reference-v1"


def phone(value):
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise ValueError("Usa formato internacional: +525512345678")
    return value


class PhoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    celular: str | None
    consent: bool = False

    @field_validator("celular")
    @classmethod
    def validate_phone(cls, value):
        return phone(value.strip()) if value is not None else None


class ReferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: str
    consent: Literal[True]

    @field_validator("reference")
    @classmethod
    def validate_reference(cls, value):
        value = value.strip()
        if not value or len(value) > 300:
            raise ValueError("Referencia vacía o demasiado larga")
        return value


def normalized_reference(provider, value):
    if provider == "amazon":
        try:
            return TypeAdapter(EmailStr).validate_python(value)
        except ValidationError:
            raise HTTPException(422, "Usa el correo de tu cuenta Amazon") from None
    if provider == "whatsapp":
        try:
            return phone(value)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
    # Store canonical public profile references only, never tokens or app IDs.
    try:
        url = urlsplit(value)
        hosts = {provider + ".com", "www." + provider + ".com"}
        if (url.scheme != "https" or url.hostname not in hosts or url.port
                or url.username or url.password or url.query or url.fragment
                or not re.fullmatch(r"/[A-Za-z0-9._]+/?", url.path)):
            raise ValueError()
        return f"https://{provider}.com/{url.path.strip('/')}"
    except ValueError:
        raise HTTPException(422, f"Usa la URL https://{provider}.com/usuario sin parámetros") from None


def locked_user(db, usuario):
    # Serialize phone/reference changes for this identity, independent of tenant.
    row = db.query(Usuario).filter_by(usuario_id=usuario.usuario_id).populate_existing().with_for_update().first()
    if row is None:
        raise HTTPException(404, "Usuario no disponible")
    return row


def snapshot(db, usuario):
    rows = db.query(ExternalIdentity).filter_by(usuario_id=usuario.usuario_id).order_by(ExternalIdentity.provider).all()
    return {
        "usuario_id": usuario.usuario_id,
        "celular": usuario.celular,
        "celular_verified_at": usuario.celular_verified_at,
        "celular_consent_at": usuario.celular_consent_at,
        "identities": [{
            "provider": row.provider, "reference": row.reference,
            "verified_at": row.verified_at, "consent_at": row.consent_at,
            "consent_version": row.consent_version, "revoked_at": row.revoked_at,
        } for row in rows],
    }


@router.get("")
def get_identity(response: Response, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_core_db)):
    response.headers["Cache-Control"] = "no-store"
    return snapshot(db, usuario)


@router.patch("")
def update_phone(body: PhoneUpdate, response: Response, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_core_db)):
    if body.celular is not None and not body.consent:
        raise HTTPException(422, "Autoriza guardar tu celular en el perfil")
    row = locked_user(db, usuario)
    if row.celular != body.celular:
        row.celular = body.celular
        row.celular_verified_at = None
        row.celular_consent_at = datetime.utcnow() if body.celular else None
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return snapshot(db, row)


@router.put("/external/{provider}")
def put_reference(provider: Provider, body: ReferenceUpdate, response: Response,
                  usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_core_db)):
    reference = normalized_reference(provider, body.reference)
    owner = locked_user(db, usuario)
    row = db.query(ExternalIdentity).filter_by(usuario_id=owner.usuario_id, provider=provider).first()
    if row is None:
        row = ExternalIdentity(identity_id=str(uuid4()), usuario_id=owner.usuario_id, provider=provider)
        db.add(row)
    if row.reference != reference or row.revoked_at is not None:
        row.reference = reference
        row.verified_at = None
        row.verification_method = None
        row.revoked_at = None
        row.consent_at = datetime.utcnow()
        row.consent_version = CONSENT_VERSION
        row.updated_at = datetime.utcnow()
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return snapshot(db, owner)


@router.delete("/external/{provider}")
def revoke_reference(provider: Provider, response: Response,
                     usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_core_db)):
    owner = locked_user(db, usuario)
    row = db.query(ExternalIdentity).filter_by(usuario_id=owner.usuario_id, provider=provider).first()
    if row and row.revoked_at is None:
        row.reference = None
        row.verified_at = None
        row.verification_method = None
        row.revoked_at = datetime.utcnow()
        row.updated_at = row.revoked_at
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return snapshot(db, owner)
