"""Reviewed operational windows, separate from initial emptiness certificates.

Only an explicitly selected, versioned authorization may extend a synthetic run.
No database write, inferred renewal, or caller-controlled filesystem path.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

AUTHORIZATION_ROOT = Path(__file__).resolve().parents[1] / 'sandbox_authorizations'
AUTHORIZATION_ENV = 'AXS_CORPORATE_SANDBOX_AUTHORIZATION_ID'


def utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise RuntimeError('Sandbox: UTC explícito requerido')
    return value


def validate_window(window, *, run_id, issuer, now=None):
    now = now or datetime.now(timezone.utc)
    UUID(window['authorization_id'])
    UUID(window['run_id'])
    approved, start, end = (utc(window[k]) for k in ('approved_at', 'starts_at', 'expires_at'))
    if (window.get('version') != 1 or window['run_id'] != run_id
            or window['clerk_issuer'] != issuer or window.get('synthetic_only') is not True
            or window.get('revoked') is not False or not window.get('approved_by', '').strip()
            or not window.get('reason', '').strip()
            or not approved <= start <= now < end
            or end - approved > timedelta(days=7)
            or set(window.get('certificates', {})) != {'CORE', 'GOV', 'EVENT'}):
        raise RuntimeError('Sandbox: autorización ausente, vencida, revocada o incompatible')
    return end


def load_window(values):
    selected = values.get(AUTHORIZATION_ENV, '')
    if not selected:
        return None  # Unchanged legacy 24-hour contract; never infer a renewal.
    try:
        selected = str(UUID(selected))
        window = json.loads((AUTHORIZATION_ROOT / f'{selected}.json').read_text())
        if window['authorization_id'] != selected:
            raise ValueError('Wrong authorization')
        # Selection is confined to the reviewed synthetic C5 profile.
        if (values.get('AXS_CORPORATE_SANDBOX_ONLY') != 'true'
                or values.get('AXS_CORPORATE_SANDBOX_PHASE') != 'runtime'
                or values.get('AXS_CORPORATE_SANDBOX_RUN_PROFILE') != 'visits-20261115'):
            raise ValueError('Wrong environment')
        validate_window(window, run_id=values['AXS_CORPORATE_SANDBOX_RUN_ID'],
                        issuer=values['CLERK_JWT_ISSUER'])
        return window
    except Exception as exc:
        raise RuntimeError('Sandbox: autorización operativa no verificable') from exc


def certificate_matches(window, row):
    """Bind the authorization to the exact original evidence, without altering it."""
    original = window['certificates'][row['domain']]
    for key in ('database_name', 'catalog_hash'):
        if original[key] != row[key]:
            raise RuntimeError('Sandbox: constancia distinta a la autorizada')
    for key in ('certified_at', 'expires_at'):
        if utc(original[key]) != utc(row[key]):
            raise RuntimeError('Sandbox: constancia inicial modificada')
