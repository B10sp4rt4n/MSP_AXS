"""
═══════════════════════════════════════════════════════════════════════════════
Router de Autenticación - Punto de Entrada para Crear AUP_SESSION
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

  POST /auth/login es el punto de creación de AUP_SESSION.
  
  Flujo AUP completo:
    1. Cliente presenta credenciales (LoginRequest)
    2. Sistema busca AUP_IDENTITY por email
    3. Sistema valida AUP_CREDENTIAL (password_local)
    4. Sistema genera AUP_SESSION con identity_id + role
    5. Sistema serializa AUP_SESSION como JWT
    6. Cliente recibe TokenResponse
  
  Después, el cliente usa el token en cada request:
    Authorization: Bearer <access_token>
  
  Y el sistema reconstruye AUP_IDENTITY mediante get_current_user()

AXIOMA APLICADO:
  Este endpoint NO requiere AUP_SESSION (es público).
  Todos los demás endpoints SÍ la requieren.

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

# ✅ AUP_CORE: Identidad y sesión
from backend.db.core import Usuario, get_core_db
# ✅ AUP_EVENT: Registro de verdad histórica
from backend.db.event import get_event_db

from backend.core.auth.schemas import LoginRequest, TokenResponse
from backend.core.auth.password import verify_password
from backend.core.auth.jwt import create_access_token
from ..core.event.registry import registrar_evento
from ..core.event import EventEntity, EventAction, EventResult

logger = logging.getLogger("axs.auth")

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db_core: Session = Depends(get_core_db),
    db_event: Session = Depends(get_event_db)
):
    """
    ═══════════════════════════════════════════════════════════════════════
    Autenticación: Crear AUP_SESSION desde AUP_CREDENTIAL
    ═══════════════════════════════════════════════════════════════════════
    
    Flujo completo:
      1. Buscar AUP_IDENTITY por email (CORE)
      2. Validar AUP_CREDENTIAL (password_local)
      3. Generar AUP_SESSION con identity_id + role
      4. Serializar AUP_SESSION como JWT
      5. Registrar evento (EVENT)
      6. Retornar TokenResponse
    
    AXIOMAS APLICADOS:
      - Sin AUP_CREDENTIAL válida → No hay AUP_SESSION
      - Operaciones de lectura → CORE
      - Operaciones de verdad → EVENT
    
    USO POSTERIOR DEL TOKEN:
      Authorization: Bearer <access_token>
      
    El token será validado por get_current_user() en endpoints protegidos.
    """
    
    # Paso 1: Buscar AUP_IDENTITY por email (CORE)
    usuario = db_core.query(Usuario).filter(Usuario.email == credentials.email).first()
    
    if not usuario:
        logger.warning(f"Login fallido: AUP_IDENTITY no encontrada - {credentials.email}")
        # No registramos evento aquí porque no hay identidad válida
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Paso 2: Validar AUP_CREDENTIAL
    if not verify_password(credentials.password, usuario.password_hash):
        logger.warning(f"Login fallido: AUP_CREDENTIAL inválida - {credentials.email}")
        
        # AUP_EVENT: Login fallido (escribe en EVENT)
        registrar_evento(
            db=db_event,
            identity=usuario,
            session_token="login_attempt",
            tenant_id=usuario.condominio_id or "sistema",
            entidad=EventEntity.SESSION.value,
            entidad_id=usuario.usuario_id,
            accion=EventAction.LOGIN.value,
            resultado=EventResult.FALLO.value,
            scope_id=None,
            motivo="Contraseña incorrecta"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Paso 3 y 4: Generar y serializar AUP_SESSION
    access_token = create_access_token(
        user_id=usuario.usuario_id,
        role=usuario.rol
    )
    
    logger.info(
        f"AUP_SESSION creada: identity={usuario.usuario_id} role={usuario.rol} "
        f"method=local email={usuario.email}"
    )
    
    # Paso 5: AUP_EVENT - Login exitoso (escribe en EVENT)
    registrar_evento(
        db=db_event,
        identity=usuario,
        session_token=access_token,
        tenant_id=usuario.condominio_id or "sistema",
        entidad=EventEntity.SESSION.value,
        entidad_id=usuario.usuario_id,
        accion=EventAction.LOGIN.value,
        resultado=EventResult.EXITO.value,
        scope_id=None,
        motivo="Autenticación exitosa",
        metadata={"email": usuario.email, "rol": usuario.rol}
    )
    
    # Paso 6: Retornar contrato TokenResponse
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )
