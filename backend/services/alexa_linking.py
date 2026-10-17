"""Resident beta linking through Clerk OAuth and signed Alexa lifecycle events."""
from datetime import datetime, timezone
import hashlib
import os
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from sqlalchemy import text

from backend.db.core import AccessLevel, AlexaAccount, Casa, Usuario
from backend.core.scope.msp_boundary import require_condominio
from backend.core.tenant.context import _set_postgres_tenant
from backend.services.alexa_request import SKILL_EVENTS
from backend.services.event_outbox import contexto_evento, encolar_evento

PERMISSION = 'alexa::devices:all:notifications:write'
PUBLICATION = 'AMAZON.MessageAlert.Activated'


def enabled():
    return os.getenv('AXS_ALEXA_LINKING_ENABLED', '').lower() == 'true'


def account_key(user_id):
    if not isinstance(user_id, str) or not user_id.startswith('amzn1.ask.account.') or len(user_id) > 1024:
        raise HTTPException(400, 'Identificador Alexa inválido')
    return hashlib.sha256(user_id.encode()).hexdigest()


def clerk_subject(token):
    """Introspect only at the configured Clerk issuer, never a request-supplied URL."""
    issuer = os.getenv('CLERK_JWT_ISSUER', '').strip().rstrip('/')
    client_id = os.getenv('AXS_ALEXA_CLERK_CLIENT_ID', '').strip()
    secret = os.getenv('AXS_ALEXA_CLERK_CLIENT_SECRET', '').strip()
    url = urlsplit(issuer)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path or url.query or url.fragment or not client_id or not secret):
        raise HTTPException(503, 'Vinculación Alexa sin configurar')
    if not isinstance(token, str) or not token or len(token) > 16384:
        raise HTTPException(403, 'Vincula tu cuenta AXS desde Alexa')
    try:
        with httpx.Client(timeout=3.0, follow_redirects=False) as client:
            response = client.post(issuer + '/oauth/token_info',
                auth=(client_id, secret), data={'token': token, 'token_type_hint': 'access_token'})
            response.raise_for_status()
            info = response.json()
    except Exception:
        # No upstream bodies/tokens in responses or logs.
        raise HTTPException(503, 'No se pudo verificar la vinculación AXS') from None
    if (info.get('active') is not True or info.get('client_id') != client_id
            or 'openid' not in str(info.get('scope', '')).split()
            or not isinstance(info.get('sub'), str) or not info['sub'].startswith('user_')
            or ('exp' in info and (not isinstance(info['exp'], (int, float))
                                  or info['exp'] <= datetime.now(timezone.utc).timestamp()))):
        raise HTTPException(403, 'Vinculación AXS no vigente')
    return info['sub']


def authorized_resident(db, db_gov, *, resident=None, clerk_id=None, tenant=None, house=None):
    query = db.query(Usuario).filter(Usuario.rol == 'RESIDENTE')
    query = query.filter(Usuario.clerk_id == clerk_id) if clerk_id else query.filter(Usuario.usuario_id == resident)
    user = query.one_or_none()
    allowed = {v.strip() for v in os.getenv('AXS_ALEXA_BETA_CONDOMINIOS', '').split(',') if v.strip()}
    if (not user or not user.condominio_id or not user.casa_id
            or user.condominio_id not in allowed
            or (tenant and user.condominio_id != tenant) or (house and user.casa_id != house)):
        raise HTTPException(403, 'Residente o vivienda fuera de la beta')
    require_condominio(db, db_gov, user, user.condominio_id, AccessLevel.RESIDENTE)
    _set_postgres_tenant(db, user.condominio_id)
    if not db.query(Casa).filter_by(casa_id=user.casa_id, condominio_id=user.condominio_id).one_or_none():
        raise HTTPException(403, 'Vivienda no vigente')
    return user


def active(row):
    return bool(row and row.usuario_id and row.linked_at
                and (row.disabled_at is None or row.linked_at > row.disabled_at))


def notifications_active(row):
    return bool(active(row) and row.permission_granted and row.subscribed
                and (row.disabled_at is None or (
                    row.permission_at and row.permission_at > row.disabled_at
                    and row.subscription_at and row.subscription_at > row.disabled_at)))


def lock_account(db, key):
    if db.get_bind().dialect.name == 'postgresql':
        # Serializes even first creation; collisions only serialize unrelated accounts.
        lock_id = int.from_bytes(bytes.fromhex(key)[:8], 'big', signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock_id})


def event_time(req):
    stamp = datetime.fromisoformat(req.get('eventCreationTime', req['timestamp']).replace('Z', '+00:00'))
    sent = datetime.fromisoformat(req['timestamp'].replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp > sent:
        raise HTTPException(400, 'Fecha de evento inválida')
    return stamp.astimezone(timezone.utc).replace(tzinfo=None)


def audit(db, row, user, request_id, action):
    ctx = contexto_evento(user, request_id, entidad='alexa', accion=action,
                          motivo='Preferencia de vinculación Alexa')
    _set_postgres_tenant(db, row.condominio_id)
    encolar_evento(db, row.condominio_id, row.account_key, ctx,
                  metadata={'canal': 'alexa', 'casa_id': row.casa_id})


def handle_event(envelope, db, db_gov):
    req = envelope['request']
    kind = req['type']
    if kind not in SKILL_EVENTS:
        raise HTTPException(400, 'Evento Alexa no soportado')
    system_user = envelope['context']['System']['user']
    key = account_key(system_user['userId'])
    stamp = event_time(req)
    # Resolve OAuth outside the account lock; errors leave all state unchanged.
    user = None
    if kind == 'AlexaSkillEvent.SkillAccountLinked':
        token = req.get('body', {}).get('accessToken') or system_user.get('accessToken')
        subject = clerk_subject(token)
        user = authorized_resident(db, db_gov, clerk_id=subject)
    lock_account(db, key)
    row = db.query(AlexaAccount).filter_by(account_key=key).populate_existing().one_or_none()
    if row is None:
        row = AlexaAccount(account_key=key, amazon_user_id=system_user['userId'],
                           permission_granted=False, subscribed=False)
        db.add(row)
    changed = False
    if kind == 'AlexaSkillEvent.SkillAccountLinked':
        if (row.linked_at is None or stamp > row.linked_at) and (row.disabled_at is None or stamp > row.disabled_at):
            row.usuario_id, row.condominio_id, row.casa_id = user.usuario_id, user.condominio_id, user.casa_id
            row.linked_at = stamp
            changed = True
    elif kind in ('AlexaSkillEvent.SkillDisabled', 'AlexaSkillEvent.SkillAccountUnlinked'):
        if row.disabled_at is None or stamp > row.disabled_at:
            row.disabled_at = stamp
            changed = True
    elif kind in ('AlexaSkillEvent.SkillPermissionAccepted', 'AlexaSkillEvent.SkillPermissionChanged'):
        granted = any(p.get('scope') == PERMISSION for p in req.get('body', {}).get('acceptedPermissions', []))
        # At equal timestamps, revocation always wins. Duplicate grants are no-ops.
        if row.permission_at is None or stamp > row.permission_at or (stamp == row.permission_at and not granted and row.permission_granted):
            row.permission_at, row.permission_granted = stamp, granted
            changed = True
    elif kind == 'AlexaSkillEvent.ProactiveSubscriptionChanged':
        subscribed = any(p.get('eventName') == PUBLICATION for p in req.get('body', {}).get('subscriptions', []))
        if row.subscription_at is None or stamp > row.subscription_at or (stamp == row.subscription_at and not subscribed and row.subscribed):
            row.subscription_at, row.subscribed = stamp, subscribed
            changed = True
    if changed and row.usuario_id:
        actor = user or db.query(Usuario).filter_by(usuario_id=row.usuario_id).one()
        audit(db, row, actor, req['requestId'],
              'vincular' if kind.endswith('SkillAccountLinked') else 'actualizar_preferencia')
    db.commit()
    return {}


def resolve_voice(envelope, db, db_gov):
    system_user = envelope['context']['System']['user']
    row = db.get(AlexaAccount, account_key(system_user['userId']))
    if not active(row):
        return None
    subject = clerk_subject(system_user.get('accessToken'))
    return authorized_resident(db, db_gov, clerk_id=subject,
        tenant=row.condominio_id, house=row.casa_id) if db.query(Usuario).filter_by(
            usuario_id=row.usuario_id, clerk_id=subject).one_or_none() else None
