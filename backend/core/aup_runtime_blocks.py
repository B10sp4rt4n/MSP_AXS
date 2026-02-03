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
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import logging

from backend.core.auth.jwt import decode_access_token
from backend.db.event import get_event_db
from backend.core.event.registry import registrar_evento
from backend.core.event import EventEntity, EventAction, EventResult

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
        "/health",  # Health check para monitoring
        "/docs",
        "/openapi.json",
        "/favicon.ico",
        "/auth/login",  # Login es la ÚNICA forma de obtener SESSION
        "/api/auth/login",  # Login con prefijo /api (para proxy de Vite)
        "/auth/register",
        "/api/auth/register",  # Register con prefijo /api
        "/login.html",  # Página de login
        "/admin.html",  # Panel de administración (valida token en cliente)
        "/guardia.html",  # Modo guardia (valida token en cliente)
        "/update_token.html",  # Página de actualización de token
    }
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Intercepta TODA request antes de llegar al router.
        """
        path = request.url.path
        
        # ─────────────────────────────────────────────────────────────
        # 0. Permitir preflight CORS (OPTIONS)
        # ─────────────────────────────────────────────────────────────
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # ─────────────────────────────────────────────────────────────
        # 1. Permitir endpoints públicos
        # ─────────────────────────────────────────────────────────────
        if path in self.PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/static"):
            return await call_next(request)
        
        # ─────────────────────────────────────────────────────────────
        # 2. Todos los demás endpoints requieren SESSION
        # ─────────────────────────────────────────────────────────────
        auth_header = request.headers.get("Authorization")
        logger.debug(f"🔍 Authorization header recibido: {auth_header[:50] if auth_header else 'VACÍO'}...")
        
        if not auth_header:
            logger.warning(f"🚫 AUP-01 BLOQUEADO: No SESSION en {request.method} {path}")
            
            # Registrar evento de denegación
            self._registrar_denied_no_session(request)
            
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "AUP-01 VIOLATED: No SESSION provided",
                    "axiom": "Nada ocurre sin sesión",
                    "path": path,
                    "method": request.method
                }
            )
        
        # ─────────────────────────────────────────────────────────────
        # 3. Validar que SESSION es válida
        # ─────────────────────────────────────────────────────────────
        try:
            token = auth_header.replace("Bearer ", "")
            logger.debug(f"🔍 Token extraído: {token[:30]}... (primeros 30 chars)")
            
            payload = decode_access_token(token)
            logger.debug(f"🔍 Payload después de decode: {payload}")
            
            if not payload:
                logger.warning(f"🚫 AUP-01 BLOQUEADO: Payload vacío/None después de decode")
                logger.warning(f"   Token que se intentó: {token[:50]}...")
                raise ValueError("Token inválido o expirado")
            
            logger.info(f"✅ AUP-01 PASADO: Token válido para identity_id={payload.get('sub')}")
            
            # Agregar identity_id al state de request (para uso posterior)
            request.state.identity_id = payload.get("sub")
            request.state.session_token = token
            
        except Exception as e:
            logger.warning(f"🚫 AUP-01 BLOQUEADO: SESSION inválida en {request.method} {path}: {type(e).__name__}: {str(e)}")
            
            # Registrar evento de denegación
            self._registrar_denied_no_session(request)
            
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "AUP-01 VIOLATED: Invalid SESSION",
                    "axiom": "Nada ocurre sin sesión válida",
                    "path": path,
                    "method": request.method,
                    "error": str(e)
                }
            )
        
        # ─────────────────────────────────────────────────────────────
        # 4. SESSION válida → Permitir continuar
        # ─────────────────────────────────────────────────────────────
        logger.info(f"✅ AUP-01 PASSED: SESSION válida para {request.method} {path}")
        return await call_next(request)
    
    def _registrar_denied_no_session(self, request: Request):
        """
        Registra evento cuando se bloquea por falta de SESSION.
        
        Axioma: Toda denegación deja huella.
        """
        try:
            db: Session = next(get_event_db())
            
            # Registrar evento sin identity (porque no hay SESSION)
            from backend.db.event import Event
            from datetime import datetime
            import hashlib
            
            timestamp = datetime.utcnow()
            
            # Calcular hash sin event_id (usamos timestamp como parte del hash)
            contenido = "|".join([
                "NONE",  # identity
                "NONE",  # tenant
                EventEntity.SESSION.value,
                "NONE",
                EventAction.DENEGAR.value,
                EventResult.DENEGADO.value,
                timestamp.isoformat()
            ])
            hash_evento = hashlib.sha256(contenido.encode('utf-8')).hexdigest()
            
            evento = Event(
                identity_id="NONE",  # No hay identidad sin SESSION
                tenant_id="NONE",
                tipo_evento=EventAction.DENEGAR.value,
                entidad=EventEntity.SESSION.value,
                entidad_id="NONE",
                accion=EventAction.DENEGAR.value,
                resultado=EventResult.DENEGADO.value,
                motivo=f"AUP-01 VIOLATED: No SESSION en {request.method} {request.url.path}",
                metadata_json={
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown"
                },
                timestamp=timestamp,
                hash_evento=hash_evento
            )
            
            db.add(evento)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Error registrando evento DENIED_NO_SESSION: {e}")


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
