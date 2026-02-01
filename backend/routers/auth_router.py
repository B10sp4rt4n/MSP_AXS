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
from backend.core.auth.dependencies import get_current_user
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
    
    # DEBUG: Log de inicio
    logger.info(f"🔍 Intento de login: {credentials.email}")
    
    # DEBUG: Verificar configuración de BD
    from backend.db.core.engine import DATABASE_CORE_URL
    import os
    logger.info(f"🔍 DATABASE_CORE_URL: {DATABASE_CORE_URL}")
    logger.info(f"🔍 CWD: {os.getcwd()}")
    
    # DEBUG: Verificar todos los usuarios
    todos_usuarios = db_core.query(Usuario).all()
    logger.info(f"🔍 Total usuarios en BD: {len(todos_usuarios)}")
    for u in todos_usuarios[:3]:
        logger.info(f"   - {u.email}")
    
    # Paso 1: Buscar AUP_IDENTITY por email (CORE)
    logger.info(f"🔍 Buscando en base de datos...")
    usuario = db_core.query(Usuario).filter(Usuario.email == credentials.email).first()
    
    logger.info(f"🔍 Resultado de búsqueda: {usuario is not None}")
    if usuario:
        logger.info(f"🔍 Usuario encontrado: {usuario.email} - {usuario.nombre}")
    
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


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    current_user: Usuario = Depends(get_current_user),
    db_event: Session = Depends(get_event_db)
):
    """
    ═══════════════════════════════════════════════════════════════════════
    Renovar AUP_SESSION: Crear nuevo token desde uno existente válido
    ═══════════════════════════════════════════════════════════════════════
    
    Este endpoint permite renovar un token ANTES de que expire, evitando
    que el usuario tenga que volver a hacer login.
    
    Flujo:
      1. Usuario presenta token válido (pero puede estar cerca de expirar)
      2. Sistema valida el token (vía get_current_user)
      3. Sistema genera nuevo token con el mismo contexto
      4. Retorna nuevo token con tiempo de vida completo
    
    USO RECOMENDADO:
      - Llamar este endpoint cada 7 horas (1 hora antes de expirar)
      - O llamarlo cuando recibas 401 y tengas token "reciente"
      - Implementar auto-refresh en el frontend
    
    VENTAJA:
      El usuario mantiene su sesión sin interrupciones.
    """
    
    # Generar nuevo token con el mismo contexto del usuario actual
    new_token = create_access_token(
        user_id=current_user.usuario_id,
        role=current_user.rol
    )
    
    logger.info(
        f"Token renovado: identity={current_user.usuario_id} "
        f"email={current_user.email}"
    )
    
    # Registrar evento de renovación
    registrar_evento(
        db=db_event,
        identity=current_user,
        session_token=new_token,
        tenant_id=current_user.condominio_id or "sistema",
        entidad=EventEntity.SESSION.value,
        entidad_id=current_user.usuario_id,
        accion=EventAction.LOGIN.value,
        resultado=EventResult.EXITO.value,
        scope_id=None,
        motivo="Token renovado",
        metadata={"email": current_user.email, "rol": current_user.rol}
    )
    
    return TokenResponse(
        access_token=new_token,
        token_type="bearer"
    )


@router.get("/me")
def get_me(
    current_user: Usuario = Depends(get_current_user),
    db_core: Session = Depends(get_core_db)
):
    """
    ═══════════════════════════════════════════════════════════════════════
    Obtener datos del usuario autenticado
    ═══════════════════════════════════════════════════════════════════════
    
    Retorna la información completa del usuario actual basado en el token JWT.
    Incluye datos del tenant y condominio si están disponibles.
    """
    
    # Buscar información del tenant (MSP) si existe
    tenant_nombre = None
    if current_user.msp_id:
        from backend.db.core.models import MSP
        msp = db_core.query(MSP).filter(MSP.msp_id == current_user.msp_id).first()
        if msp:
            tenant_nombre = msp.nombre
    
    # Buscar información del condominio en registro de condominios activos
    condominio_nombre = None
    if current_user.condominio_id:
        from backend.db.core.models import Condominio
        condominio = db_core.query(Condominio).filter(
            Condominio.condominio_id == current_user.condominio_id
        ).first()
        if condominio:
            condominio_nombre = condominio.nombre
    
    return {
        "usuario_id": current_user.usuario_id,
        "email": current_user.email,
        "nombre": current_user.nombre,
        "rol": current_user.rol,
        "msp_id": current_user.msp_id,
        "tenant_nombre": tenant_nombre or current_user.msp_id,
        "condominio_id": current_user.condominio_id,
        "condominio_nombre": condominio_nombre or current_user.condominio_id,
        "casa_unidad": current_user.casa_unidad
    }
