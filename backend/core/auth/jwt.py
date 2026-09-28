"""
═══════════════════════════════════════════════════════════════════════════════
AUP_SESSION - Entidad de Contexto Temporal Autenticado
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

  AUP_SESSION es una cápsula temporal de contexto autenticado.
  
  - Representa una sesión activa
  - Tiene identidad (identity_id)
  - Tiene alcance (rol)
  - Tiene vigencia (issued_at, expires_at)
  - Conoce su método de autenticación (local, oauth, sso)
  
  JWT es la serialización de una AUP_SESSION.

RELACIÓN:
  AUP_IDENTITY -genera→ AUP_SESSION

AXIOMAS:
  1. Ninguna acción se ejecuta sin AUP_SESSION válida
  2. AUP_SESSION es temporal y expira
  3. AUP_SESSION no puede ser modificada una vez emitida (stateless)

ESTRUCTURA AUP_SESSION:
  {
    "sub": identity_id,        # quién es
    "role": rol_base,          # qué puede hacer (base)
    "method": "local",         # cómo se autenticó
    "iat": timestamp,          # cuándo se creó
    "exp": timestamp           # cuándo expira
  }

MIGRACIÓN FUTURA:
  - Cambiar a RS256 (asymmetric) para SSO/OAuth
  - Agregar "scope": [...] para permisos granulares (AUP_SCOPE)
  - Agregar "tenant": condominio_id para multitenant
  - Agregar "jti" para revocación activa

═══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import time
import logging

import httpx
from jose import JWTError, jwt

logger = logging.getLogger("axs.jwt")

# Configuración desde variables de entorno
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# Clerk — JWKS cache simple (se invalida cada hora)
_clerk_jwks_cache: Dict[str, Any] = {"keys": None, "fetched_at": 0}
_CLERK_JWKS_TTL = 3600  # 1 hora


def _get_clerk_domain() -> Optional[str]:
    """Deriva el dominio Clerk desde la publishable key."""
    pk = os.getenv("CLERK_PUBLISHABLE_KEY") or os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
    if not pk:
        return None
    try:
        import base64
        # pk_test_<base64> → decodificar
        b64 = pk.split("_", 2)[-1]
        # Agregar padding si falta
        b64 += "=" * (-len(b64) % 4)
        decoded = base64.b64decode(b64).decode("utf-8").rstrip("$")
        return decoded
    except Exception:
        return None


def _fetch_clerk_jwks() -> Optional[Dict]:
    """Obtiene JWKS de Clerk con caché de 1 hora."""
    global _clerk_jwks_cache
    now = time.time()
    if _clerk_jwks_cache["keys"] and (now - _clerk_jwks_cache["fetched_at"]) < _CLERK_JWKS_TTL:
        return _clerk_jwks_cache["keys"]

    domain = _get_clerk_domain()
    if not domain:
        return None

    try:
        url = f"https://{domain}/.well-known/jwks.json"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        jwks = response.json()
        _clerk_jwks_cache = {"keys": jwks, "fetched_at": now}
        return jwks
    except Exception as e:
        logger.warning(f"No se pudo obtener JWKS de Clerk: {e}")
        return None


def verify_clerk_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifica un JWT emitido por Clerk usando sus llaves públicas (RS256).
    Retorna el payload si es válido, None si no.
    """
    jwks = _fetch_clerk_jwks()
    if not jwks:
        return None
    try:
        payload = jwt.decode(
            token, jwks, algorithms=["RS256"],
            options={"verify_aud": False}
        )
        return payload
    except JWTError as e:
        logger.warning(f"Clerk JWT error: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Clerk verify error inesperado: {type(e).__name__}: {e}")
        return None


def create_access_token(
    user_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea una AUP_SESSION serializada como JWT.
    
    Esta función GENERA una sesión autenticada.
    
    Args:
        user_id: identity_id de AUP_IDENTITY
        role: rol_base de AUP_IDENTITY
        expires_delta: Tiempo de vida de la sesión (opcional)
        
    Returns:
        AUP_SESSION serializada (JWT string)
        
    AXIOMA APLICADO:
        Una AUP_SESSION siempre tiene expiración explícita.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Estructura AUP_SESSION
    session_payload = {
        "sub": user_id,              # AUP_IDENTITY
        "role": role,                # Alcance base
        "method": "local",           # Método de autenticación
        "iat": datetime.utcnow(),    # Emitido en
        "exp": expire,               # Expira en
    }
    
    # Serializar AUP_SESSION
    encoded_jwt = jwt.encode(session_payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Deserializa y valida una AUP_SESSION desde JWT.
    
    Esta función VALIDA una sesión.
    
    Args:
        token: JWT serializado
        
    Returns:
        Payload de AUP_SESSION si es válida, None si es inválida o expirada
        
    AXIOMA APLICADO:
        Una AUP_SESSION expirada o inválida es equivalente a ausencia de sesión.
    """
    import logging
    logger = logging.getLogger("axs.jwt")
    
    try:
        logger.debug(f"🔍 Decodificando token: {token[:30]}...")
        logger.debug(f"🔍 SECRET_KEY usado: {SECRET_KEY[:20]}... (primeros 20 chars)")
        logger.debug(f"🔍 ALGORITHM: {ALGORITHM}")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"✅ Token decodificado exitosamente. identity_id: {payload.get('sub')}")
        return payload
    except JWTError as e:
        # Token inválido, expirado o manipulado
        logger.warning(f"❌ JWT Error al decodificar: {type(e).__name__}: {str(e)}")
        logger.warning(f"   Token: {token[:50]}...")
        logger.warning(f"   Error details: {repr(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Error inesperado en decode_access_token: {type(e).__name__}: {str(e)}")
        return None

