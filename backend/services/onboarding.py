"""Read-only incorporation states derived from AXS identity and invitation evidence."""
from datetime import datetime, timedelta, timezone


def invitation_state(identity, scope, now=None):
    previous = (scope.metadata_json or {}).get('clerk_invitation') or {}
    if not previous or previous.get('email') != identity.email:
        return {'estado': 'sin_solicitar', 'solicitada_en': None, 'vence_en': None}
    try:
        sent = datetime.fromisoformat(previous['sent_at'])
        if sent.tzinfo is None:
            raise ValueError('Timestamp without timezone')
        expires = sent + timedelta(days=7)
        if sent > (now or datetime.now(timezone.utc)):
            raise ValueError('Future timestamp')
    except (KeyError, TypeError, ValueError):
        return {'estado': 'revisar', 'solicitada_en': None, 'vence_en': None}
    return {'estado': 'solicitada' if expires > (now or datetime.now(timezone.utc)) else 'vencida',
            'solicitada_en': sent.isoformat(), 'vence_en': expires.isoformat()}


def incorporation_state(identity, scope, valid_home):
    invitation = invitation_state(identity, scope)
    if not valid_home:
        state = 'vivienda_pendiente'
    elif identity.clerk_id:
        state = 'registrado'
    elif invitation['estado'] == 'solicitada':
        state = 'invitacion_solicitada'
    elif invitation['estado'] == 'vencida':
        state = 'invitacion_vencida'
    elif invitation['estado'] == 'revisar':
        state = 'revisar_invitacion'
    else:
        state = 'precargado'
    return {'estado': state, 'registro_completo': bool(identity.clerk_id),
            'vivienda_valida': valid_home, 'invitacion': invitation,
            'puede_invitar': valid_home and not identity.clerk_id and invitation['estado'] in {'sin_solicitar', 'vencida'}}
