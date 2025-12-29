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

from ..db.connection import SessionLocal
from ..db.models import Usuario
from .auth.schemas import LoginRequest, TokenResponse
from .auth.password import verify_password
from .auth.jwt import create_access_token
from ..core.event.registry import registrar_evento
from ..core.event import EventEntity, EventAction, EventResult

logger = logging.getLogger("axs.auth")

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_db():
    """Dependency para sesión de BD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    ═══════════════════════════════════════════════════════════════════════
    Autenticación: Crear AUP_SESSION desde AUP_CREDENTIAL
    ═══════════════════════════════════════════════════════════════════════
    
    Flujo completo:
      1. Buscar AUP_IDENTITY por email
      2. Validar AUP_CREDENTIAL (verify_password)
      3. Generar AUP_SESSION con identity_id + role
      4. Serializar AUP_SESSION como JWT
      5. Retornar TokenResponse
    
    AXIOMAS APLICADOS:
      - Sin AUP_CREDENTIAL válida → No hay AUP_SESSION
      - AUP_SESSION contiene identidad y alcance (role)
    
    USO POSTERIOR DEL TOKEN:
      Authorization: Bearer <access_token>
      
    El token será validado por get_current_user() en endpoints protegidos.
    """
    
    # Paso 1: Buscar AUP_IDENTITY por email
    usuario = db.query(Usuario).filter(Usuario.email == credentials.email).first()
    
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
        
        # AUP_EVENT: Login fallido
        # Nota: tenant_id es el condominio del usuario (o "sistema" si no tiene)
        registrar_evento(
            db=db,
            identity=usuario,
            session_token="login_attempt",  # No hay sesión aún
            tenant_id=usuario.condominio_id or "sistema",
            entidad=EventEntity.SESSION.value,
            entidad_id=usuario.usuario_id,
            accion=EventAction.LOGIN.value,
            resultado=EventResult.FALLO.value,
            scope_id=None,  # No hay scope en login
            motivo="Contraseña incorrecta"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # TODO (Futuro): Validar usuario activo
    # if not usuario.is_active:
    #     raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    # Paso 3 y 4: Generar y serializar AUP_SESSION
    access_token = create_access_token(
        user_id=usuario.usuario_id,
        role=usuario.rol
    )
    
    logger.info(
        f"AUP_SESSION creada: identity={usuario.usuario_id} role={usuario.rol} "
        f"method=local email={usuario.email}"
    )
    
    # AUP_EVENT: Login exitoso
    registrar_evento(
        db=db,
        identity=usuario,
        session_token=access_token,
        tenant_id=usuario.condominio_id or "sistema",
        entidad=EventEntity.SESSION.value,
        entidad_id=usuario.usuario_id,
        accion=EventAction.LOGIN.value,
        resultado=EventResult.EXITO.value,
        scope_id=None,  # Scope se valida después en endpoints
        motivo="Autenticación exitosa",
        metadata={"email": usuario.email, "rol": usuario.rol}
    )
    
    # Paso 5: Retornar contrato TokenResponse
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )
