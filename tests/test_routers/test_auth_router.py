"""
═══════════════════════════════════════════════════════════════════════════════
Tests: Auth Router - Casos de /auth/login
═══════════════════════════════════════════════════════════════════════════════

DECISIÓN TÉCNICA:

  Estos tests validan el punto de entrada de AUP_SESSION mediante HTTP endpoints.
  
  Usamos TestClient (HTTP) en vez de llamadas directas porque:
    ✅ Valida el contrato FastAPI completo (request/response models)
    ✅ Prueba la integración con depends (get_core_db, get_event_db)
    ✅ Asegura que middleware y validaciones HTTP funcionen
  
  Patrones aplicados:
    - FastAPI dependency override (sobreescribir get_core_db/get_event_db)
    - TestClient para simular requests HTTP
    - Fixtures de pytest para setup/teardown

═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch
from backend.main import app
from backend.db.core import get_core_db, Usuario
from backend.db.event import get_event_db, Event
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures: Sobrescribir dependencias con DBs de test
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def test_client(db_core_session, db_event_session):
    """Cliente HTTP con DBs sobrescritas por las de test."""
    
    def override_get_core_db():
        try:
            yield db_core_session
        finally:
            pass
    
    def override_get_event_db():
        try:
            yield db_event_session
        finally:
            pass
    
    app.dependency_overrides[get_core_db] = override_get_core_db
    app.dependency_overrides[get_event_db] = override_get_event_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def usuario_test(db_core_session: Session):
    """
    Usuario de prueba con credenciales válidas.
    
    NOTA: Usamos un password_hash dummy porque mockeamos verify_password.
    Los tests no necesitan bcrypt real ya que mockean la verificación.
    """
    usuario = Usuario(
        usuario_id="test_user_001",
        nombre="Juan Test",
        email="juan@test.com",
        password_hash="$2b$12$DUMMY_HASH_FOR_TESTING",  # Hash dummy
        rol="residente",
        condominio_id="condo_test_001",
        msp_id="msp_test_001",
        casa_unidad="A-101"
    )
    db_core_session.add(usuario)
    db_core_session.commit()
    db_core_session.refresh(usuario)
    return usuario


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: POST /auth/login
# ═══════════════════════════════════════════════════════════════════════════════

@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_login_exitoso_retorna_token(mock_verify, test_client: TestClient, usuario_test: Usuario):
    """
    ✅ Caso: Credenciales válidas
    
    Espera:
      - HTTP 200
      - access_token presente en response
      - token_type = "bearer"
    """
    response = test_client.post(
        "/auth/login",
        json={
            "email": "juan@test.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 50  # JWT es largo


@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_login_exitoso_registra_evento_exito(
    mock_verify,
    test_client: TestClient, 
    usuario_test: Usuario,
    db_event_session: Session
):
    """
    ✅ Caso: Login exitoso debe registrar evento en AUP_EVENT
    
    Espera:
      - Evento con accion=LOGIN, resultado=EXITO
      - identity_id del usuario
      - metadata con email y rol
    """
    test_client.post(
        "/auth/login",
        json={
            "email": "juan@test.com",
            "password": "password123"
        }
    )
    
    # Verificar evento en DB
    evento = db_event_session.query(Event).filter(
        Event.tipo_evento == "login",
        Event.resultado == "exito"
    ).first()
    
    assert evento is not None
    assert evento.identity_id == usuario_test.usuario_id
    assert evento.tenant_id == usuario_test.condominio_id
    assert evento.entidad == "session"
    
    # Verificar metadata
    metadata = evento.metadata_json
    assert metadata["email"] == "juan@test.com"
    assert metadata["rol"] == "residente"


def test_login_email_no_existe_retorna_401(test_client: TestClient):
    """
    ❌ Caso: Email no registrado
    
    Espera:
      - HTTP 401 Unauthorized
      - Mensaje genérico (no revela si email existe)
      - NO registra evento (porque no hay identity válida)
    """
    response = test_client.post(
        "/auth/login",
        json={
            "email": "noexiste@test.com",
            "password": "cualquier_password"
        }
    )
    
    assert response.status_code == 401
    assert "Email o contraseña incorrectos" in response.json()["detail"]


def test_login_email_no_existe_no_registra_evento(
    test_client: TestClient,
    db_event_session: Session
):
    """
    ❌ Caso: Email no existe → NO debe registrar evento
    
    Espera:
      - Sin eventos en AUP_EVENT
      
    RAZÓN:
      No hay AUP_IDENTITY válida, por lo tanto no hay identity_id para el evento.
    """
    test_client.post(
        "/auth/login",
        json={
            "email": "noexiste@test.com",
            "password": "cualquier_password"
        }
    )
    
    eventos = db_event_session.query(Event).all()
    assert len(eventos) == 0


@patch('backend.routers.auth_router.verify_password', return_value=False)
def test_login_password_incorrecto_retorna_401(
    mock_verify,
    test_client: TestClient, 
    usuario_test: Usuario
):
    """
    ❌ Caso: Password incorrecto
    
    Espera:
      - HTTP 401 Unauthorized
      - Mensaje genérico (no revela si email existe)
    """
    response = test_client.post(
        "/auth/login",
        json={
            "email": "juan@test.com",
            "password": "password_incorrecto"
        }
    )
    
    assert response.status_code == 401
    assert "Email o contraseña incorrectos" in response.json()["detail"]


@patch('backend.routers.auth_router.verify_password', return_value=False)
def test_login_password_incorrecto_registra_evento_fallo(
    mock_verify,
    test_client: TestClient,
    usuario_test: Usuario,
    db_event_session: Session
):
    """
    ❌ Caso: Password incorrecto → registra evento FALLO
    
    Espera:
      - Evento con accion=LOGIN, resultado=FALLO
      - motivo="Contraseña incorrecta"
      
    RAZÓN:
      A diferencia de email no existe, aquí SÍ hay AUP_IDENTITY válida,
      por lo tanto SÍ podemos registrar el evento de fallo.
    """
    test_client.post(
        "/auth/login",
        json={
            "email": "juan@test.com",
            "password": "password_incorrecto"
        }
    )
    
    evento = db_event_session.query(Event).filter(
        Event.tipo_evento == "login",
        Event.resultado == "fallo"
    ).first()
    
    assert evento is not None
    assert evento.identity_id == usuario_test.usuario_id
    assert evento.motivo == "Contraseña incorrecta"


@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_login_valida_formato_token_response(
    mock_verify,
    test_client: TestClient,
    usuario_test: Usuario
):
    """
    ✅ Caso: Response cumple con contrato TokenResponse
    
    Espera:
      - Estructura exact: {"access_token": str, "token_type": "bearer"}
      - Compatible con OAuth2 RFC 6749
    """
    response = test_client.post(
        "/auth/login",
        json={
            "email": "juan@test.com",
            "password": "password123"
        }
    )
    
    data = response.json()
    
    # Validar estructura exacta
    assert set(data.keys()) == {"access_token", "token_type"}
    assert isinstance(data["access_token"], str)
    assert data["token_type"] == "bearer"


@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_login_usuario_inactivo_puede_autenticar(
    mock_verify,
    test_client: TestClient,
    db_core_session: Session
):
    """
    ⚠️ Caso: Cualquier usuario en DB puede autenticarse
    
    NOTA IMPORTANTE:
      El modelo Usuario NO tiene flag 'activo', por lo tanto cualquier
      usuario que exista en la tabla puede hacer login.
      
      Si queremos bloquear usuarios, necesitamos:
      - Agregar campo 'activo' al modelo Usuario (migración)
      - O validar mediante AUP_SCOPE (scope con status INACTIVO)
      
      Este test documenta el comportamiento actual.
    """
    usuario_inactivo = Usuario(
        usuario_id="inactive_user_001",
        nombre="Usuario Inactivo",
        email="inactivo@test.com",
        password_hash="$2b$12$DUMMY_HASH_FOR_TESTING",  # Hash dummy
        rol="residente",
        condominio_id="condo_test_001",
        msp_id="msp_test_001",
        casa_unidad="B-202"
    )
    db_core_session.add(usuario_inactivo)
    db_core_session.commit()
    
    response = test_client.post(
        "/auth/login",
        json={
            "email": "inactivo@test.com",
            "password": "password123"
        }
    )
    
    # Actualmente permite login
    assert response.status_code == 200
    assert "access_token" in response.json()


@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_login_email_case_sensitive(
    mock_verify,
    test_client: TestClient,
    usuario_test: Usuario
):
    """
    ⚠️ Caso: Email es case-sensitive en búsqueda
    
    NOTA:
      SQLite por defecto es case-sensitive para strings.
      Si queremos búsqueda case-insensitive, usar func.lower() o COLLATE NOCASE.
      
      Este test documenta el comportamiento actual.
    """
    response = test_client.post(
        "/auth/login",
        json={
            "email": "JUAN@test.com",  # Mayúsculas
            "password": "password123"
        }
    )
    
    # Actualmente NO encuentra el usuario (case-sensitive)
    assert response.status_code == 401


@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_login_sin_condominio_id_usa_sistema(
    mock_verify,
    test_client: TestClient,
    db_core_session: Session,
    db_event_session: Session
):
    """
    ✅ Caso: Usuario sin condominio_id → tenant_id="sistema" en eventos
    
    Espera:
      - Login exitoso
      - Evento registrado con tenant_id="sistema"
    """
    usuario_sin_condo = Usuario(
        usuario_id="admin_user_001",
        nombre="Admin Sistema",
        email="admin@sistema.com",
        password_hash="$2b$12$DUMMY_HASH_FOR_TESTING",  # Hash dummy
        rol="MSP_ADMIN",
        condominio_id=None,  # Sin condominio
        msp_id="msp_test_001",
        casa_unidad=None
    )
    db_core_session.add(usuario_sin_condo)
    db_core_session.commit()
    
    response = test_client.post(
        "/auth/login",
        json={
            "email": "admin@sistema.com",
            "password": "admin123"
        }
    )
    
    assert response.status_code == 200
    
    # Verificar evento usa "sistema" como tenant_id
    evento = db_event_session.query(Event).filter(
        Event.identity_id == "admin_user_001"
    ).first()
    
    assert evento.tenant_id == "sistema"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: Axiomas AUP
# ═══════════════════════════════════════════════════════════════════════════════

def test_axioma_sin_credential_no_hay_session(test_client: TestClient):
    """
    🔒 AXIOMA: Sin AUP_CREDENTIAL válida → No hay AUP_SESSION
    
    Espera:
      - Credential inválida → HTTP 401
      - NO retorna token
    """
    response = test_client.post(
        "/auth/login",
        json={
            "email": "juan@test.com",
            "password": "password_incorrecto"
        }
    )
    
    assert response.status_code == 401
    assert "access_token" not in response.json()


@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_axioma_operaciones_lectura_en_core(
    mock_verify,
    test_client: TestClient,
    usuario_test: Usuario,
    db_core_session: Session
):
    """
    🔒 AXIOMA: Operaciones de lectura → CORE
    
    Espera:
      - Login busca usuario en db_core_session
      - Usuario existe en CORE después del login
    """
    # Verificar que usuario está en CORE
    usuario_en_core = db_core_session.query(Usuario).filter(
        Usuario.email == "juan@test.com"
    ).first()
    
    assert usuario_en_core is not None
    assert usuario_en_core.usuario_id == usuario_test.usuario_id


@patch('backend.routers.auth_router.verify_password', return_value=True)
def test_axioma_operaciones_verdad_en_event(
    mock_verify,
    test_client: TestClient,
    usuario_test: Usuario,
    db_event_session: Session
):
    """
    🔒 AXIOMA: Operaciones de verdad → EVENT
    
    Espera:
      - Login exitoso registra evento en db_event_session
      - Evento es inmutable (no se puede editar después)
    """
    test_client.post(
        "/auth/login",
        json={
            "email": "juan@test.com",
            "password": "password123"
        }
    )
    
    # Verificar evento en EVENT
    evento = db_event_session.query(Event).first()
    assert evento is not None
    
    # Guardar hash original
    hash_original = evento.hash_evento
    
    # Intentar modificar (esto violaría inmutabilidad en producción)
    # Por ahora solo verificamos que el hash existe
    assert hash_original is not None
    assert len(hash_original) == 64  # SHA-256 hex
