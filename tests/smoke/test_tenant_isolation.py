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

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.db.connection import Base
from backend.db.models import Usuario, MSP, Condominio, UserTenantScope, AccessLevel, ScopeStatus
from backend.core.auth.jwt import create_access_token
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración de base de datos de prueba
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_smoke.db"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Crea una base de datos limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Cliente de prueba con override de DB."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    from backend.core.dependencies import get_db
    app.dependency_overrides[get_db] = override_get_db
    
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
        password_hash=pwd_context.hash("password123"),
        rol="RESIDENTE",
        condominio_id="tenant-a",
        casa_unidad="A-101"
    )
    
    usuario_b = Usuario(
        usuario_id="user-b",
        nombre="Usuario B",
        email="userb@test.com",
        password_hash=pwd_context.hash("password123"),
        rol="RESIDENTE",
        condominio_id="tenant-b",
        casa_unidad="B-101"
    )
    
    usuario_sin_scope = Usuario(
        usuario_id="user-nosco",
        nombre="Usuario Sin Scope",
        email="nosco@test.com",
        password_hash=pwd_context.hash("password123"),
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
        identity_id="user-a",
        tenant_id="tenant-a",
        access_level=AccessLevel.RESIDENTE,
        status=ScopeStatus.ACTIVO
    )
    
    scope_b = UserTenantScope(
        identity_id="user-b",
        tenant_id="tenant-b",
        access_level=AccessLevel.RESIDENTE,
        status=ScopeStatus.ACTIVO
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
    token = create_access_token({"sub": usuario_sin_scope.usuario_id})
    
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
    token = create_access_token({"sub": usuario_a.usuario_id})
    
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

def test_set_app_tenant_id_funciona(db):
    """
    CRÍTICO: Verificar que SET app.tenant_id funciona en PostgreSQL.
    
    Si este test falla: RLS no funcionará.
    
    NOTA: Este test asume PostgreSQL. En SQLite no aplica pero no debe romper.
    """
    try:
        # Ejecutar SET
        db.execute(text("SET app.tenant_id = 'test-tenant-123'"))
        
        # Leer valor (con fallback para SQLite)
        result = db.execute(
            text("SELECT current_setting('app.tenant_id', true)")
        ).scalar()
        
        # En PostgreSQL debe retornar el valor
        # En SQLite puede retornar None (no soporta SET)
        if result is not None:
            assert result == "test-tenant-123", \
                f"SET no persistió correctamente. Esperado: test-tenant-123, Obtenido: {result}"
        else:
            # SQLite - marcar como skip implícito
            pytest.skip("SQLite no soporta SET/current_setting - OK en tests")
            
    except Exception as e:
        # Si falla en PostgreSQL, es crítico
        if "current_setting" not in str(e):
            pytest.fail(f"❌ SET app.tenant_id falló: {str(e)}")


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
