"""Enforce sandbox deadlines on every request, including after a long uptime."""
from datetime import datetime, timezone
from starlette.responses import JSONResponse


class SandboxExpiryGuard:
    def __init__(self, app, deadline):
        self.app = app
        self.deadline = deadline

    async def __call__(self, scope, receive, send):
        expired = self.deadline is None or datetime.now(timezone.utc) >= self.deadline
        if scope['type'] == 'websocket' and expired:
            await send({'type': 'websocket.close', 'code': 1008})
            return
        if scope['type'] == 'http' and scope['path'] not in ('/', '/health') and expired:
            response = JSONResponse(status_code=503,
                content={'detail': 'Ensayo vencido o cerrado. Requiere habilitación operativa explícita.'},
                headers={'Cache-Control': 'private, no-store'})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
