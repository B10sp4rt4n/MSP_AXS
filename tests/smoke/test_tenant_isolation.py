"""
═══════════════════════════════════════════════════════════════════════════════
SMOKE TESTS - AISLAMIENTO MULTI-TENANT
═══════════════════════════════════════════════════════════════════════════════

PROPÓSITO:
  Tests mínimos que DEBEN pasar antes del piloto.
  Si alguno falla, NO arrancar el piloto.

CRITERIO:
  Estos tests validan que set_tenant_context() funciona y RLS está activo.

═══════════════════════════════════════════════════════════════════════════════
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.db.core import Base_CORE, Usuario, MSP, Condominio, UserTenantScope, AccessLevel, ScopeStatus
from backend.core.auth.jwt import create_access_token
from backend.core.auth.password import hash_password
from sqlalchemy.pool import StaticPool

# Motor en memoria — aislado por test, sin archivo en disco
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Crea una base de datos limpia (en memoria) para cada test."""
    Base_CORE.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base_CORE.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Cliente de prueba con override de DB (legacy + core)."""
    def override_get_db():
        yield db

    # Overridear tanto get_db (legacy) como get_core_db (AUP CORE usada por auth)
    from backend.core.dependencies import get_db
    from backend.db.core import get_core_db
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_core_db] = override_get_db

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture
def setup_tenants_and_users(db):
    """
    Crea 2 tenants y usuarios con scopes diferentes.
    
    Tenant A: usuario_a tiene scope
    Tenant B: usuario_b tiene scope
    usuario_a NO tiene scope en Tenant B
    """
    # Crear MSP
    msp = MSP(msp_id="msp-test", nombre="MSP Test")
    db.add(msp)
    
    # Crear 2 condominios (tenants)
    condo_a = Condominio(
        condominio_id="tenant-a",
        msp_id="msp-test",
        nombre="Condominio A"
    )
    condo_b = Condominio(
        condominio_id="tenant-b",
        msp_id="msp-test",
        nombre="Condominio B"
    )
    db.add(condo_a)
    db.add(condo_b)
    db.commit()
    
    # Crear usuarios
    usuario_a = Usuario(
        usuario_id="user-a",
        nombre="Usuario A",
        email="usera@test.com",
        password_hash=hash_password("password123"),
        rol="RESIDENTE",
        condominio_id="tenant-a",
        casa_unidad="A-101"
    )
    
    usuario_b = Usuario(
        usuario_id="user-b",
        nombre="Usuario B",
        email="userb@test.com",
        password_hash=hash_password("password123"),
        rol="RESIDENTE",
        condominio_id="tenant-b",
        casa_unidad="B-101"
    )
    
    usuario_sin_scope = Usuario(
        usuario_id="user-nosco",
        nombre="Usuario Sin Scope",
        email="nosco@test.com",
        password_hash=hash_password("password123"),
        rol="RESIDENTE",
        condominio_id=None,  # Sin condominio
        casa_unidad=None
    )
    
    db.add(usuario_a)
    db.add(usuario_b)
    db.add(usuario_sin_scope)
    db.commit()
    
    # Crear scopes
    scope_a = UserTenantScope(
        usuario_id="user-a",
        tenant_id="tenant-a",
        access_level=AccessLevel.RESIDENTE,
        estado=ScopeStatus.ACTIVO
    )

    scope_b = UserTenantScope(
        usuario_id="user-b",
        tenant_id="tenant-b",
        access_level=AccessLevel.RESIDENTE,
        estado=ScopeStatus.ACTIVO
    )
    
    db.add(scope_a)
    db.add(scope_b)
    db.commit()
    
    return {
        "usuario_a": usuario_a,
        "usuario_b": usuario_b,
        "usuario_sin_scope": usuario_sin_scope,
        "tenant_a": "tenant-a",
        "tenant_b": "tenant-b"
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: Usuario sin scope debe ser rechazado (403)
# ═══════════════════════════════════════════════════════════════════════════

def test_sin_scope_devuelve_403(client, db, setup_tenants_and_users):
    """
    CRÍTICO: Usuario sin scope NO puede acceder a ningún tenant.
    
    Si este test falla: Hay un problema grave de autorización.
    """
    data = setup_tenants_and_users
    usuario_sin_scope = data["usuario_sin_scope"]
    
    # Crear token para usuario sin scope
    token = create_access_token(usuario_sin_scope.usuario_id, usuario_sin_scope.rol)
    
    # Intentar acceder a tenant-a (donde no tiene scope)
    response = client.get(
        "/visitas/mis-visitas/tenant-a",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # DEBE ser rechazado
    assert response.status_code == 403, \
        f"Usuario sin scope NO debe acceder. Obtuvo: {response.status_code}"
    
    assert "sin acceso" in response.json()["detail"].lower() or \
           "scope" in response.json()["detail"].lower(), \
        f"Mensaje de error no claro: {response.json()}"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: Usuario con scope ve SOLO su tenant
# ═══════════════════════════════════════════════════════════════════════════

def test_usuario_ve_solo_su_tenant(client, db, setup_tenants_and_users):
    """
    CRÍTICO: Usuario de tenant-a NO debe ver datos de tenant-b.
    
    Si este test falla: HAY FUGA DE DATOS ENTRE TENANTS.
    """
    data = setup_tenants_and_users
    usuario_a = data["usuario_a"]
    
    # Token válido para usuario_a
    token = create_access_token(usuario_a.usuario_id, usuario_a.rol)
    
    # Intentar acceder a tenant-b (donde NO tiene scope)
    response = client.get(
        "/visitas/mis-visitas/tenant-b",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # DEBE ser rechazado
    assert response.status_code == 403, \
        f"❌ FUGA MULTI-TENANT: Usuario de tenant-a accedió a tenant-b! " \
        f"Status: {response.status_code}"
    
    # Ahora acceder a su propio tenant (DEBE funcionar)
    response = client.get(
        "/visitas/mis-visitas/tenant-a",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200, \
        f"Usuario NO puede acceder a su propio tenant. Status: {response.status_code}"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: SET app.tenant_id se ejecuta correctamente
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
def test_set_app_tenant_id_funciona():
    """
    CRÍTICO: Verificar que set_config(app.tenant_id) funciona en PostgreSQL.
    
    Si este test falla: RLS no funcionará.
    
    Requiere una instancia PostgreSQL desechable configurada por variable.
    """
    from sqlalchemy.orm import Session
    from backend.core.tenant.context import _set_postgres_tenant

    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere AXS_TEST_POSTGRES_URL de una base PostgreSQL desechable")
    engine_pg = create_engine(url)
    if engine_pg.dialect.name != "postgresql":
        engine_pg.dispose()
        pytest.fail("AXS_TEST_POSTGRES_URL debe apuntar a PostgreSQL")
    try:
        with Session(engine_pg) as session:
            _set_postgres_tenant(session, "test-tenant-123")
            assert session.execute(text("SELECT current_setting('app.tenant_id', true)")).scalar() == "test-tenant-123"
            session.rollback()
    finally:
        engine_pg.dispose()


# ═══════════════════════════════════════════════════════════════════════════
# RESUMEN DE TESTS
# ═══════════════════════════════════════════════════════════════════════════

"""
RESULTADO ESPERADO:
  ✅ test_sin_scope_devuelve_403           → PASS
  ✅ test_usuario_ve_solo_su_tenant        → PASS  
  ✅ test_set_app_tenant_id_funciona       → PASS (o SKIP en SQLite)

Si alguno FALLA:
  ❌ NO arrancar el piloto
  ❌ Volver a Fase 1
  ❌ Revisar set_tenant_context()

CÓMO EJECUTAR:
  pytest tests/smoke/test_tenant_isolation.py -v

CÓMO VERIFICAR EN LOGS:
  # Durante el test, buscar:
  grep "TENANT-CONTEXT" logs/test.log
  grep "SET exitoso" logs/test.log
  grep "ACCESO DENEGADO" logs/test.log
"""
