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

from jose import JWTError, jwt

# Configuración desde variables de entorno
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"  # Simétrico, migrable a RS256 en el futuro
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 horas por defecto


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

