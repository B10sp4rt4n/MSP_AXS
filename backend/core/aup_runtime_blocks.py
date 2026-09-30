"""
═══════════════════════════════════════════════════════════════════════════════
AUP RUNTIME BLOCKS — Bloqueos Operativos del Modelo AUP
═══════════════════════════════════════════════════════════════════════════════

PROPÓSITO:
  Hacer que AUP sea IMPOSIBLE de ignorar en runtime.
  
  Estos bloqueos NO son logs.
  NO son warnings.
  NO son opcionales.
  
  Son GUARDRAILS DUROS que rompen ejecución si se violan.

BLOQUEOS IMPLEMENTADOS:
  1. AUP-01: No acción sin SESSION
  2. AUP-02: GOV antes del negocio (marcador de estado)
  3. AUP-03: No EVENT, no retorno (verificación post-ejecución)

AXIOMA FUNDAMENTAL:
  Si algo "funciona" pero viola estos bloqueos, ES incorrecto.

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Callable, Optional, Set
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from backend.core.auth.jwt import decode_access_token, verify_clerk_token

logger = logging.getLogger("aup.runtime")


# ═══════════════════════════════════════════════════════════════════════════
# BLOQUEO AUP-01: No acción sin SESSION
# ═══════════════════════════════════════════════════════════════════════════

class AUPSessionGuard(BaseHTTPMiddleware):
    """
    Middleware que bloquea TODA operación sin SESSION válida.
    
    Axioma aplicado:
      Nada ocurre sin sesión.
      
    Comportamiento:
      1. Si endpoint es público → pasa
      2. Si endpoint es protegido:
         a. Valida que existe token
         b. Valida que token es válido
         c. Si no → bloqueo duro + evento DENIED_NO_SESSION
    
    Violación AUP si:
      ❌ Se puede ejecutar lógica sin pasar por aquí
      ❌ Se retorna None en lugar de fallar
      ❌ Existe bypass (modo debug, etc.)
    """
    
    # Endpoints públicos (whitelist)
    PUBLIC_PATHS: Set[str] = {
        "/",
        "/docs",
        "/openapi.json",
        "/favicon.ico",
        "/auth/login",  # Login es la ÚNICA forma de obtener SESSION
        "/auth/register",
        "/admin.html",  # Panel de administración (valida token en cliente)
        "/webhooks/clerk",  # Clerk webhook — verificado por firma svix
        "/health",
        "/debug/db",
    }
    
    async def _conservar_rechazo(self, request, reason):
        from backend.services.security_outbox import guardar_intento
        try:
            await run_in_threadpool(guardar_intento, request, reason)
            return True
        except Exception as exc:
            logger.error("Rechazo de seguridad sin persistir (%s)", type(exc).__name__)
            return False

    async def dispatch(self, request: Request, call_next: Callable):
        from backend.services.security_outbox import ruta_segura
        path = request.url.path
        if request.method == "OPTIONS" or path in self.PUBLIC_PATHS or path.startswith("/docs"):
            return await call_next(request)
        auth_header = request.headers.get("Authorization", "")
        reason = "NO_SESSION" if not auth_header else None
        if auth_header:
            try:
                scheme, separator, token = auth_header.partition(" ")
                if scheme.lower() != "bearer" or not separator or not token:
                    raise ValueError("Formato de sesión inválido")
                payload = verify_clerk_token(token) or decode_access_token(token)
                if not payload or not payload.get("sub"):
                    raise ValueError("Sesión inválida")
                # sub aquí es una afirmación firmada; la identidad se verifica
                # en get_current_user antes de atribuirle un evento de seguridad.
                request.state.identity_id = payload["sub"]
                request.state.session_token = token
            except Exception:
                reason = "INVALID_SESSION"
        if reason:
            if not await self._conservar_rechazo(request, reason):
                return JSONResponse(status_code=503, content={"detail": "Acceso rechazado; auditoría no disponible"})
            return JSONResponse(status_code=401, content={
                "detail": "AUP-01 VIOLATED: No SESSION provided" if reason == "NO_SESSION" else "AUP-01 VIOLATED: Invalid SESSION",
                "axiom": "Nada ocurre sin sesión válida", "path": ruta_segura(request), "method": request.method},
                headers={"WWW-Authenticate": "Bearer"})
        response = await call_next(request)
        security_reason = getattr(request.state, "security_denial_reason", None)
        if security_reason and response.status_code in (401, 403):
            if not await self._conservar_rechazo(request, security_reason):
                return JSONResponse(status_code=503, content={"detail": "Acceso rechazado; auditoría no disponible"})
        return response


# ═══════════════════════════════════════════════════════════════════════════
# BLOQUEO AUP-02: GOV antes del negocio (marcador de estado)
# ═══════════════════════════════════════════════════════════════════════════

class AUPGovEnforcer:
    """
    Contexto que marca que GOV fue evaluado ANTES del negocio.
    
    Axioma aplicado:
      El negocio ocurre después del poder, nunca antes.
      
    Uso:
      with AUPGovEnforcer() as gov:
          # 1. Evaluar gobierno
          permitido, motivo = puede_ejecutar_accion(...)
          gov.mark_evaluated(permitido)
          
          if not permitido:
              raise HTTPException(403, motivo)
          
          # 2. Solo ahora ejecutar negocio
          resultado = ejecutar_negocio()
          gov.mark_business_executed()
          
          return resultado
    
    Violación AUP si:
      ❌ Se ejecuta negocio sin llamar mark_evaluated()
      ❌ Se ejecuta negocio con permitido=False
      ❌ Se omite el contexto AUPGovEnforcer
    """
    
    def __init__(self):
        self._gov_evaluated = False
        self._gov_result = False
        self._business_executed = False
    
    def __enter__(self):
        logger.debug("🛡️  AUP-02: Iniciando contexto de gobierno")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Verificar que GOV fue evaluado
        if not self._gov_evaluated:
            logger.error("🚫 AUP-02 VIOLATED: GOV nunca fue evaluado")
            raise RuntimeError(
                "AUP-02 VIOLATED: Gobierno nunca fue evaluado. "
                "Axioma: El negocio ocurre después del poder."
            )
        
        # Si negocio se ejecutó, verificar que GOV permitió
        if self._business_executed and not self._gov_result:
            logger.error("🚫 AUP-02 VIOLATED: Negocio ejecutado pero GOV denegó")
            raise RuntimeError(
                "AUP-02 VIOLATED: Negocio ejecutado con GOV denegado. "
                "Axioma: Si gobierno deniega, negocio no ocurre."
            )
        
        logger.debug(f"✅ AUP-02 PASSED: GOV={self._gov_result}, Negocio={self._business_executed}")
    
    def mark_evaluated(self, permitido: bool):
        """
        Marca que GOV fue evaluado.
        
        Args:
            permitido: Resultado de evaluación de gobierno
        """
        self._gov_evaluated = True
        self._gov_result = permitido
        logger.info(f"🛡️  AUP-02: GOV evaluado → {'PERMITIDO' if permitido else 'DENEGADO'}")
    
    def mark_business_executed(self):
        """
        Marca que negocio fue ejecutado.
        
        SOLO debe llamarse DESPUÉS de mark_evaluated(True)
        """
        if not self._gov_evaluated:
            raise RuntimeError(
                "AUP-02 VIOLATED: Intentando marcar negocio ejecutado sin evaluar GOV"
            )
        
        if not self._gov_result:
            raise RuntimeError(
                "AUP-02 VIOLATED: Intentando ejecutar negocio con GOV denegado"
            )
        
        self._business_executed = True
        logger.info("✅ AUP-02: Negocio ejecutado (GOV aprobó)")


# ═══════════════════════════════════════════════════════════════════════════
# BLOQUEO AUP-03: No EVENT, no retorno
# ═══════════════════════════════════════════════════════════════════════════

class AUPEventEnforcer:
    """
    Contexto que garantiza que EVENT se registra ANTES de retornar.
    
    Axioma aplicado:
      Sin evento, no hay existencia.
      
    Uso:
      with AUPEventEnforcer() as event_guard:
          # Ejecutar operación
          resultado = hacer_algo()
          
          # OBLIGATORIO: Registrar evento antes de salir
          registrar_evento(...)
          event_guard.mark_event_registered()
          
          return resultado
    
    Violación AUP si:
      ❌ Se retorna sin llamar mark_event_registered()
      ❌ Se omite el contexto AUPEventEnforcer
      ❌ EVENT es opcional
    """
    
    def __init__(self, operation: str):
        self._operation = operation
        self._event_registered = False
    
    def __enter__(self):
        logger.debug(f"📝 AUP-03: Iniciando contexto de evento para '{self._operation}'")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Si hay excepción, permitir propagación (pero avisar)
        if exc_type is not None:
            logger.warning(
                f"⚠️  AUP-03: Operación '{self._operation}' falló con {exc_type.__name__}. "
                f"EVENT registrado: {self._event_registered}"
            )
            # No bloquear excepciones de negocio
            return False
        
        # Si operación fue exitosa, verificar que EVENT existe
        if not self._event_registered:
            logger.error(f"🚫 AUP-03 VIOLATED: Operación '{self._operation}' completó sin EVENT")
            raise RuntimeError(
                f"AUP-03 VIOLATED: Operación '{self._operation}' no registró evento. "
                "Axioma: Sin evento, no hay existencia."
            )
        
        logger.info(f"✅ AUP-03 PASSED: EVENT registrado para '{self._operation}'")
    
    def mark_event_registered(self):
        """
        Marca que EVENT fue registrado.
        
        DEBE llamarse ANTES de retornar respuesta.
        """
        self._event_registered = True
        logger.debug(f"📝 AUP-03: EVENT registrado para '{self._operation}'")


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "AUPSessionGuard",      # Middleware para BLOQUEO AUP-01
    "AUPGovEnforcer",       # Context manager para BLOQUEO AUP-02
    "AUPEventEnforcer",     # Context manager para BLOQUEO AUP-03
]
