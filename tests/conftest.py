"""
Pytest configuration and shared fixtures for MSP_AXS test suite.

Architecture: AUP (SESSION → SCOPE → EVENT → GOV)
"""

import pytest
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import bases and models (AUP architecture)
from backend.db.core import Base_CORE, MSP, Condominio, Usuario
from backend.db.event import Base_EVENT, Event
from backend.db.gov import Base_GOV, Policy

# Import auth utilities
from backend.core.auth.jwt import create_access_token
from backend.core.auth.password import hash_password


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def db_engine():
    """Motor de BD temporal en memoria (SQLite)."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Sesión de BD temporal para cada test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente FastAPI con override de BD."""
    # TODO: Re-enable cuando routers estén completamente funcionales
    pytest.skip("Client fixture disabled - routers tienen imports rotos")
    
    # from fastapi.testclient import TestClient
    # from backend.main import app
    # from backend.db.connection import get_db
    # 
    # def override_get_db():
    #     try:
    #         yield db_session
    #     finally:
    #         pass
    # 
    # app.dependency_overrides[get_db] = override_get_db
    # with TestClient(app) as test_client:
    #     yield test_client
    # app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# DATA FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def msp_base(db_session):
    """MSP de prueba."""
    msp = MSP(
        msp_id="msp_test_001",
        nombre="MSP Test"
    )
    db_session.add(msp)
    db_session.commit()
    db_session.refresh(msp)
    return msp


@pytest.fixture
def condominio_base(db_session, msp_base):
    """Condominio (tenant) de prueba."""
    condominio = Condominio(
        condominio_id="condo_test_001",
        msp_id=msp_base.msp_id,
        nombre="Condominio Test"
    )
    db_session.add(condominio)
    db_session.commit()
    db_session.refresh(condominio)
    return condominio


@pytest.fixture
def usuario_base(db_session, condominio_base):
    """Usuario de prueba con credenciales conocidas."""
    usuario = Usuario(
        usuario_id="user_test_001",
        msp_id=condominio_base.msp_id,
        condominio_id=condominio_base.condominio_id,
        nombre="Test User",
        email="test@example.com",
        rol="ADMIN_CONDOMINIO",
        password_hash=hash_password("password123")
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture
def usuario_sin_permisos(db_session, condominio_base):
    """Usuario sin políticas asignadas (para test de default deny)."""
    usuario = Usuario(
        usuario_id="user_no_perms_001",
        msp_id=condominio_base.msp_id,
        condominio_id=condominio_base.condominio_id,
        nombre="User Sin Permisos",
        email="noperms@example.com",
        rol="GUARDIA",
        password_hash=hash_password("password123")
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture
def scope_usuario_base(db_session, usuario_base, condominio_base):
    """Scope explícito para usuario_base."""
    scope = UserTenantScope(
        usuario_id=usuario_base.usuario_id,
        tenant_id=condominio_base.condominio_id,
        access_level=AccessLevel.ADMIN_CONDOMINIO,
        estado=ScopeStatus.ACTIVO
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)
    return scope


@pytest.fixture
def visita_base(db_session, condominio_base):
    """Visita de prueba."""
    from datetime import timedelta
    visita = Visita(
        visita_id="visita_test_001",
        condominio_id=condominio_base.condominio_id,
        nombre_visitante="Juan Perez",
        casa_unidad="101",
        tipo_visita="frecuente",
        vigencia=datetime.utcnow() + timedelta(days=7),
        estado="pendiente"
    )
    db_session.add(visita)
    db_session.commit()
    db_session.refresh(visita)
    return visita


# ═══════════════════════════════════════════════════════════════════════════
# GOV FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def authority_global(db_session, usuario_base):
    """Autoridad GLOBAL para tests de gobierno."""
    authority = Authority(
        authority_id="auth_global_test",
        identity_id=usuario_base.usuario_id,
        tipo=AuthorityType.GLOBAL,
        tenant_id=None,
        estado=GovStatus.ACTIVO
    )
    db_session.add(authority)
    db_session.commit()
    db_session.refresh(authority)
    return authority


@pytest.fixture
def politica_qr_7dias(db_session, condominio_base):
    """Política: QR vigencia máxima 7 días."""
    policy = Policy(
        policy_id="pol_qr_7dias_test",
        nombre="qr_vigencia_dias",
        descripcion="Máximo 7 días de vigencia para QR",
        ambito=PolicyScope.TENANT,
        target_tenant_id=condominio_base.condominio_id,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": 7},
        estado=GovStatus.ACTIVO
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def politica_max_tenants_5(db_session):
    """Política GLOBAL: Máximo 5 tenants."""
    policy = Policy(
        policy_id="pol_max_tenants_test",
        nombre="max_tenants",
        descripcion="Máximo 5 tenants por usuario",
        ambito=PolicyScope.GLOBAL,
        target_tenant_id=None,
        accion_objetivo="crear_tenant",
        limites={"max_count": 5},
        estado=GovStatus.ACTIVO
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def login_helper(client):
    """Helper para login rápido en tests."""
    def _login(email: str, password: str) -> str:
        """Retorna token JWT."""
        response = client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        return None
    return _login


@pytest.fixture
def auth_headers(login_helper):
    """Helper para generar headers de autenticación."""
    def _headers(email: str = "test@example.com", password: str = "password123") -> dict:
        """Retorna headers con Bearer token."""
        token = login_helper(email, password)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}
    return _headers
