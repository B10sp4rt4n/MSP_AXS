"""
═══════════════════════════════════════════════════════════════════════════════
AUP_SESSION Validator - Punto Único de Validación de Contexto Autenticado
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

  Este módulo implementa el ÚNICO punto de validación de AUP_SESSION.
  
  get_current_user() es el guardián (gatekeeper) del sistema:
    1. Extrae AUP_SESSION serializada (JWT)
    2. Valida AUP_SESSION
    3. Reconstruye AUP_IDENTITY desde persistencia
    4. Retorna AUP_IDENTITY completa
  
AXIOMA FUNDAMENTAL:
  Ninguna acción puede ejecutarse sin pasar por este validador.
  
RELACIÓN:
  AUP_SESSION -reconstruye→ AUP_IDENTITY

CONTRATO:
  Todos los endpoints protegidos DEBEN usar:
    current_user: Usuario = Depends(get_current_user)
    
  Esto garantiza:
    - No hay identidad implícita (headers manuales)
    - No hay bypasseos
    - Un solo lugar para auditar/modificar autenticación

MIGRACIÓN FUTURA:
  - Validar scopes adicionales (AUP_SCOPE)
  - Validar tenant (multitenant)
  - Validar revocación activa (Redis/BD)
  - Cambiar a OAuth2 provider externo
  
  Todo se hace aquí, sin tocar lógica de negocio.

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ...db.connection import SessionLocal
from ...db.models import Usuario
from .jwt import decode_access_token

# OAuth2PasswordBearer: extrae token desde header Authorization: Bearer <token>
# Esto es compatible con estándar OAuth2 (migración futura facilitada)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    """
    Dependency para obtener sesión de base de datos.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    ═══════════════════════════════════════════════════════════════════════
    PUNTO ÚNICO DE VALIDACIÓN DE AUP_SESSION
    ═══════════════════════════════════════════════════════════════════════
    
    Este es el guardián del sistema.
    Toda acción protegida pasa por aquí.
    
    Flujo:
      1. Extraer AUP_SESSION (JWT) desde header Authorization
      2. Deserializar y validar AUP_SESSION
      3. Extraer identity_id desde AUP_SESSION
      4. Reconstruir AUP_IDENTITY desde base de datos
      5. Retornar AUP_IDENTITY completa
    
    AXIOMA APLICADO:
      - Sin AUP_SESSION válida → 401 Unauthorized
      - Con AUP_SESSION válida → AUP_IDENTITY reconstruida
    
    Args:
        token: AUP_SESSION serializada (extraída por OAuth2PasswordBearer)
        db: Sesión de base de datos
        
    Returns:
        AUP_IDENTITY completa (objeto Usuario)
        
    Raises:
        HTTPException 401: Si AUP_SESSION es inválida o AUP_IDENTITY no existe
        
    USO EN ENDPOINTS:
        @router.get("/protected")
        def protected_endpoint(current_user: Usuario = Depends(get_current_user)):
            # current_user es AUP_IDENTITY validada
            # Lógica de negocio aquí
            pass
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Paso 1: Deserializar AUP_SESSION
    session_payload = decode_access_token(token)
    if session_payload is None:
        raise credentials_exception
    
    # Paso 2: Extraer identity_id desde AUP_SESSION
    identity_id: Optional[str] = session_payload.get("sub")
    if identity_id is None:
        raise credentials_exception
    
    # Paso 3: Reconstruir AUP_IDENTITY desde persistencia
    usuario = db.query(Usuario).filter(Usuario.usuario_id == identity_id).first()
    if usuario is None:
        raise credentials_exception
    
    # TODO (Futuro): Validar usuario activo cuando se implemente
    # if not usuario.is_active:
    #     raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    # TODO (Futuro): Validar scope/permisos adicionales (AUP_SCOPE)
    # session_scopes = session_payload.get("scopes", [])
    # validate_scopes(usuario, session_scopes)
    
    # Retornar AUP_IDENTITY completa
    return usuario


def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Dependency opcional para validar que AUP_IDENTITY esté activa.
    
    Por ahora es passthrough, pero queda listo para validación futura.
    
    USO:
        current_user: Usuario = Depends(get_current_active_user)
    """
    # TODO: Cuando se agregue campo is_active al modelo Usuario
    # if not getattr(current_user, "is_active", True):
    #     raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    return current_user
