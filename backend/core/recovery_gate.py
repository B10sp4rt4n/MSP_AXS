"""Recovery interlock bound to an incident set OUTSIDE restored databases."""
import os
import uuid

from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware


def incident_id():
    value = os.getenv('AXS_RECOVERY_INCIDENT')
    if value is None:
        return None
    # An empty or malformed configured value must never mean normal operation.
    return str(uuid.UUID(value))


def recovery_allowed(core_factory=None, gov_factory=None):
    try:
        incident = incident_id()
        if incident is None:
            return True
        from backend.db.core.models import RecoveryCheckpoint
        from backend.db.gov.models import RecoveryGovCheckpoint
        from backend.db.core.session import SessionLocal_CORE
        from backend.db.gov.session import SessionLocal_GOV
        with (core_factory or SessionLocal_CORE)() as core, (gov_factory or SessionLocal_GOV)() as gov:
            c = core.get(RecoveryCheckpoint, incident)
            g = gov.get(RecoveryGovCheckpoint, incident)
            return bool(c and g and c.phase == g.phase == 'released'
                        and c.release_nonce and c.release_nonce == g.release_nonce)
    except Exception:
        # Missing schema, unavailable domain or bad configuration -> closed.
        return False


class RecoveryGuard(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        allowed = await run_in_threadpool(recovery_allowed)
        if request.url.path == '/ready' and request.method in ('GET', 'HEAD'):
            return JSONResponse({'ready': allowed}, status_code=200 if allowed else 503)
        if not allowed:
            if request.url.path == '/health' and request.method in ('GET', 'HEAD'):
                return JSONResponse({'status': 'recovery', 'ready': False})
            # Includes GET QR validation, login, webhooks, debug, and all mutations.
            return JSONResponse({'detail': 'Recuperación en curso; operación bloqueada',
                                 'code': 'RECOVERY_LOCKED'}, status_code=503,
                                headers={'Retry-After': '60'})
        return await call_next(request)
