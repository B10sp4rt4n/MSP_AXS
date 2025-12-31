# BATERÍA DE TESTS AUP — POST-GOBIERNO
## 16 Tests Esenciales para Validar Arquitectura Completa

---

## FILOSOFÍA DE TESTING AUP

**Axiomas:**
1. Test valida PLANO, no feature individual
2. Test falla si violación de principio, no solo de funcionalidad 
3. Test es AUDITABLE (debe leer igual que especificación AUP)

**Estructura:**
- **GRUPO 1:** SESSION (Identidad)
- **GRUPO 2:** SCOPE (Alcance)
- **GRUPO 3:** EVENT (Evidencia)
- **GRUPO 4:** GOV (Gobierno)

---

## GRUPO 1: SESSION (IDENTIDAD CERTIFICADA)

### TEST 1.1 — Login genera token JWT válido
**Objetivo:** Verificar que autenticación produce identidad certificada

**Precondiciones:**
- Usuario existe en BD: `test@example.com` / `password123`
- Usuario tiene `scope_id` asignado

**Steps:**
```python
# 1. POST /auth/login
response = client.post("/auth/login", json={
    "email": "test@example.com",
    "password": "password123"
})

# 2. Validar respuesta
assert response.status_code == 200
assert "access_token" in response.json()
token = response.json()["access_token"]

# 3. Decodificar token y validar claims esenciales
# ⚠️ AJUSTE AUP: No acoplar scope_id en JWT (se resuelve en runtime desde BD)
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
assert payload["sub"] == "test@example.com"  # Identity
assert "exp" in payload  # Expiration timestamp
assert "session_id" in payload  # Session tracking (opcional pero recomendado)
```

**Criterio de éxito:** Token contiene `sub`, `exp`, `session_id` (scope se resuelve en runtime)

**Nota AUP:** Scope NO debe estar hardcoded en JWT para permitir multi-tenancy dinámico y delegaciones.

**Falla si:** Token no tiene claims necesarios o no es verificable

---

### TEST 1.2 — Token expirado rechaza acceso
**Objetivo:** Verificar que identidad caduca (no es eterna)

**Precondiciones:**
- Token JWT con `exp` en el pasado (manualmente generado)

**Steps:**
```python
# 1. Crear token expirado
expired_payload = {
    "sub": "test@example.com",
    "scope_id": 1,
    "exp": datetime.utcnow() - timedelta(hours=2)  # 2 horas atrás
}
expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm="HS256")

# 2. Intentar acceder a endpoint protegido
response = client.get(
    "/visitas/mis-visitas",
    headers={"Authorization": f"Bearer {expired_token}"}
)

# 3. Validar rechazo
assert response.status_code == 401
assert "token expired" in response.json()["detail"].lower()
```

**Criterio de éxito:** Status 401 + mensaje de token expirado

**Falla si:** Token expirado permite acceso

---

### TEST 1.3 — Contraseña incorrecta deniega login
**Objetivo:** Verificar que identidad requiere credencial válida

**Precondiciones:**
- Usuario existe: `test@example.com`

**Steps:**
```python
# 1. POST /auth/login con contraseña incorrecta
response = client.post("/auth/login", json={
    "email": "test@example.com",
    "password": "WRONG_PASSWORD"
})

# 2. Validar rechazo
assert response.status_code == 401
assert "incorrect" in response.json()["detail"].lower()
```

**Criterio de éxito:** Status 401 + sin token en respuesta

**Falla si:** Contraseña incorrecta permite login

---

### TEST 1.4 — Endpoint protegido sin token rechaza
**Objetivo:** Verificar que operaciones requieren identidad

**Steps:**
```python
# 1. GET /visitas/mis-visitas SIN header Authorization
response = client.get("/visitas/mis-visitas")

# 2. Validar rechazo
assert response.status_code == 401
assert "not authenticated" in response.json()["detail"].lower()
```

**Criterio de éxito:** Status 401 sin token

**Falla si:** Endpoint permite acceso anónimo

---

## GRUPO 2: SCOPE (ALCANCE EXPLÍCITO)

### TEST 2.1 — Usuario solo ve recursos de su scope
**Objetivo:** Verificar aislamiento de alcance

**Preconditions:**
- Usuario A: `scope_id=1`, tiene 2 visitas en scope 1
- Usuario B: `scope_id=2`, tiene 3 visitas en scope 2

**Steps:**
```python
# 1. Login como Usuario A
token_A = login("userA@example.com", "password123")

# 2. GET /visitas/mis-visitas con token A
response = client.get(
    "/visitas/mis-visitas",
    headers={"Authorization": f"Bearer {token_A}"}
)

# 3. Validar que solo ve sus 2 visitas
assert response.status_code == 200
visitas = response.json()
assert len(visitas) == 2
assert all(v["condominio_id"] == 1 for v in visitas)  # Todas scope 1
```

**Criterio de éxito:** Usuario A NO ve visitas de scope 2

**Falla si:** Query trae visitas cross-scope

---

### TEST 2.2 — Crear recurso sin scope válido rechaza
**Objetivo:** Verificar que recursos requieren alcance explícito

**Preconditions:**
- Usuario autenticado con `scope_id=1`

**Steps:**
```python
# 1. Login
token = login("test@example.com", "password123")

# 2. POST /preregistro SIN condominio_id (o con condominio_id=999 inexistente)
response = client.post(
    "/preregistro/crear",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "nombre_visitante": "Juan Perez",
        "condominio_id": 999,  # No existe
        # ... otros campos
    }
)

# 3. Validar rechazo
assert response.status_code in [403, 404]
```

**Criterio de éxito:** Status 403/404 al intentar crear en scope inválido

**Falla si:** Sistema permite crear recurso fuera de scope

---

### TEST 2.3 — Acceder a recurso de otro scope rechaza (403)
**Objetivo:** Verificar validación cross-scope en lectura

**Preconditions:**
- Usuario A: `scope_id=1`
- Visita X: `id=100`, `condominio_id=2` (scope diferente)

**Steps:**
```python
# 1. Login como Usuario A (scope 1)
token_A = login("userA@example.com", "password123")

# 2. GET /visitas/100 (recurso de scope 2)
response = client.get(
    "/visitas/100",
    headers={"Authorization": f"Bearer {token_A}"}
)

# 3. Validar rechazo
assert response.status_code == 403
assert "scope" in response.json()["detail"].lower()
```

**Criterio de éxito:** Status 403 + mensaje de scope

**Falla si:** Usuario puede leer recurso de otro scope

---

### TEST 2.4 — Modificar recurso de otro scope rechaza (403)
**Objetivo:** Verificar validación cross-scope en escritura

**Preconditions:**
- Usuario A: `scope_id=1`
- Visita X: `id=100`, `condominio_id=2`

**Steps:**
```python
# 1. Login como Usuario A (scope 1)
token_A = login("userA@example.com", "password123")

# 2. PUT /visitas/100 (recurso de scope 2)
response = client.put(
    "/visitas/100",
    headers={"Authorization": f"Bearer {token_A}"},
    json={"estado": "completada"}
)

# 3. Validar rechazo
assert response.status_code == 403
```

**Criterio de éxito:** Status 403

**Falla si:** Usuario puede modificar recurso de otro scope

---

## GRUPO 3: EVENT (TRAZABILIDAD INMUTABLE)

### TEST 3.1 — Login registra evento con hash SHA-256
**Objetivo:** Verificar que operación crítica genera evento auditable

**Steps:**
```python
# 1. Contar eventos antes de login
count_before = db.query(AupEvent).count()

# 2. POST /auth/login
response = client.post("/auth/login", json={
    "email": "test@example.com",
    "password": "password123"
})
assert response.status_code == 200

# 3. Verificar que se creó evento
count_after = db.query(AupEvent).count()
assert count_after == count_before + 1

# 4. Validar estructura del evento
evento = db.query(AupEvent).order_by(AupEvent.id.desc()).first()
assert evento.tipo_evento == "sesion_iniciada"
assert evento.usuario_id is not None
assert evento.alcance_id is not None
assert len(evento.evento_hash) == 64  # SHA-256 = 64 chars hex
assert evento.metadata is not None  # JSON con detalles
```

**Criterio de éxito:** Evento tiene tipo, usuario, alcance, hash SHA-256

**Falla si:** Login no genera evento o evento sin hash

---

### TEST 3.2 — Generar QR registra evento con metadata
**Objetivo:** Verificar que operación de negocio genera evento

**Preconditions:**
- Usuario autenticado
- Visita existe en BD

**Steps:**
```python
# 1. Login
token = login("test@example.com", "password123")

# 2. POST /qr/generar
response = client.post(
    "/qr/generar",
    headers={"Authorization": f"Bearer {token}"},
    json={"visita_id": 1, "dias_vigencia": 3}
)
assert response.status_code == 200

# 3. Verificar evento "qr_generado"
evento = db.query(AupEvent).filter_by(tipo_evento="qr_generado").order_by(AupEvent.id.desc()).first()
assert evento is not None
assert evento.metadata["visita_id"] == 1
assert evento.metadata["dias_vigencia"] == 3
assert len(evento.evento_hash) == 64
```

**Criterio de éxito:** Evento contiene metadata de operación

**Falla si:** QR se genera sin evento

---

### TEST 3.3 — Evento deja evidencia de manipulación (inmutabilidad)
**Objetivo:** Verificar que modificación de eventos es DETECTABLE, no bloqueada

**Axioma AUP:** No bloqueamos edición técnica (SQLAlchemy lo permite),
detectamos manipulación vía hash SHA-256 que NO coincide con payload.

**Steps:**
```python
# 1. Crear evento
evento = registrar_evento_aup(
    tipo_evento="test_evento",
    alcance_id=1,
    usuario_id=1,
    metadata={"dato": "original"}
)
db.add(evento)
db.commit()

original_hash = evento.evento_hash

# 2. Simular manipulación maliciosa (editar metadata en BD)
evento.metadata = {"dato": "MODIFICADO"}
db.commit()

# 3. DETECTAR manipulación: hash ya no coincide con payload
db.refresh(evento)
nuevo_hash_calculado = calcular_hash_evento(
    tipo_evento="test_evento",
    alcance_id=1,
    usuario_id=1,
    metadata={"dato": "MODIFICADO"}  # Payload actual
)
assert evento.evento_hash == original_hash  # Hash NO se actualiza automáticamente
assert evento.evento_hash != nuevo_hash_calculado  # ⚠️ EVIDENCIA DE CORRUPCIÓN
```

**Criterio de éxito:** Hash desacoplado de metadata → manipulación DETECTABLE en auditoría

**Falla si:** Hash se actualiza automáticamente al editar (perdería trazabilidad)

**Nota AUP:** Este test NO previene edición, DETECTA alteración post-facto (correcto para auditoría forense).

---

### TEST 3.4 — Query de auditoría forense funciona
**Objetivo:** Verificar que eventos son queryables para investigación

**Preconditions:**
- 10 eventos de tipo "qr_generado" en últimas 24h
- 5 eventos de usuario X

**Steps:**
```python
# 1. Query: Todos los QR generados hoy por usuario X
eventos = db.query(AupEvent).filter(
    AupEvent.tipo_evento == "qr_generado",
    AupEvent.usuario_id == X,
    AupEvent.timestamp >= datetime.utcnow() - timedelta(days=1)
).all()

# 2. Validar resultados
assert len(eventos) == 5
assert all(e.usuario_id == X for e in eventos)
assert all(e.tipo_evento == "qr_generado" for e in eventos)

# 3. Validar que cada evento tiene hash válido
for evento in eventos:
    hash_recalculado = calcular_hash_evento(
        tipo_evento=evento.tipo_evento,
        alcance_id=evento.alcance_id,
        usuario_id=evento.usuario_id,
        metadata=evento.metadata
    )
    assert evento.evento_hash == hash_recalculado  # Integridad verificada
```

**Criterio de éxito:** Query trae eventos correctos + hashes verificables

**Falla si:** Eventos no son queryables o hashes no coinciden

---

## GRUPO 4: GOV (GOBIERNO PRECEDE OPERACIÓN)

### TEST 4.1 — Política deniega QR si excede vigencia permitida
**Objetivo:** Verificar que gobierno bloquea operación

**Preconditions:**
- Usuario tiene política "qr_vigencia_dias" con límite 7 días
- Usuario intenta generar QR con 30 días

**Steps:**
```python
# 1. Crear política restrictiva
politica = crear_politica(
    nombre="qr_vigencia_dias",
    tipo="threshold",
    limite=7  # Máximo 7 días
)
asignar_politica_a_usuario(usuario_id=1, politica_id=politica.id)

# 2. Login
token = login("test@example.com", "password123")

# 3. POST /qr/generar con 30 días
response = client.post(
    "/qr/generar",
    headers={"Authorization": f"Bearer {token}"},
    json={"visita_id": 1, "dias_vigencia": 30}  # EXCEDE límite
)

# 4. Validar bloqueo
assert response.status_code == 403
assert "política" in response.json()["detail"].lower()
assert "qr_vigencia_dias" in response.json()["detail"]
```

**Criterio de éxito:** Status 403 + mensaje explícito de política denegada

**Falla si:** QR se genera ignorando política

---

### TEST 4.2 — Política permite operación dentro de límite
**Objetivo:** Verificar que gobierno permite cuando cumple límites

**Preconditions:**
- Usuario tiene política "qr_vigencia_dias" con límite 7 días

**Steps:**
```python
# 1. Login
token = login("test@example.com", "password123")

# 2. POST /qr/generar con 5 días (dentro de límite)
response = client.post(
    "/qr/generar",
    headers={"Authorization": f"Bearer {token}"},
    json={"visita_id": 1, "dias_vigencia": 5}
)

# 3. Validar éxito
assert response.status_code == 200
assert "qr_data" in response.json()

# 4. Verificar que se registró evento "qr_generado"
evento = db.query(AupEvent).filter_by(tipo_evento="qr_generado").order_by(AupEvent.id.desc()).first()
assert evento is not None
```

**Criterio de éxito:** Status 200 + QR generado + evento registrado

**Falla si:** Política deniega operación válida

---

### TEST 4.3 — Sin política asignada, operación gobernada se deniega (default deny)
**Objetivo:** Verificar axioma "sin política = sin poder" en operaciones GOBERNADAS

**Axioma AUP:** Default deny aplica SOLO a operaciones gobernadas (QR generation, tenant creation),
NO a authentication, read-only endpoints, o operaciones básicas.

**Preconditions:**
- Usuario SIN políticas asignadas (tabla `usuario_politica` vacía para ese usuario)

**Steps:**
```python
# 1. Eliminar todas las políticas del usuario
db.query(UsuarioPolitica).filter_by(usuario_id=1).delete()
db.commit()

# 2. Login (operación NO gobernada, debe funcionar)
token = login("test@example.com", "password123")
assert token is not None  # Login exitoso sin políticas

# 3. POST /qr/generar (operación GOBERNADA)
# ⚠️ Esta operación SÍ requiere política "qr_vigencia_dias"
response = client.post(
    "/qr/generar",
    headers={"Authorization": f"Bearer {token}"},
    json={"visita_id": 1, "dias_vigencia": 3}
)

# 4. Validar bloqueo SOLO en operación gobernada
assert response.status_code == 403
assert "no tiene política" in response.json()["detail"].lower()
```

**Criterio de éxito:** Status 403 en operación gobernada + login funciona sin políticas

**Falla si:** Usuario sin políticas puede ejecutar operación gobernada

**Nota AUP:** Default deny es selectivo (operaciones críticas), no global (bloquearía login).

---

### TEST 4.4 — Upgrade de plan asigna nuevas políticas inmediatamente
**Objetivo:** Verificar que cambio de plan se aplica sin cache

**Preconditions:**
- Usuario con Plan FREE (límites: QR 7 días, max_tenants 5)

**Steps:**
```python
# 1. Verificar límite actual
politica_qr = obtener_politica_usuario(usuario_id=1, nombre="qr_vigencia_dias")
assert politica_qr.limite == 7

# 2. Upgrade a Plan PRO (límites: QR 30 días, max_tenants 25)
upgrade_plan(usuario_id=1, nuevo_plan=PlanType.PRO)

# 3. Verificar nuevo límite (sin cache, consulta directa)
politica_qr_nueva = obtener_politica_usuario(usuario_id=1, nombre="qr_vigencia_dias")
assert politica_qr_nueva.limite == 30

# 4. Validar que operación con nuevo límite funciona
token = login("test@example.com", "password123")
response = client.post(
    "/qr/generar",
    headers={"Authorization": f"Bearer {token}"},
    json={"visita_id": 1, "dias_vigencia": 20}  # Ahora permitido (PRO)
)
assert response.status_code == 200

# 5. Verificar evento "politica_asignada" (upgrade)
evento = db.query(AupEvent).filter_by(tipo_evento="politica_asignada").order_by(AupEvent.id.desc()).first()
assert evento.metadata["plan"] == "PRO"
```

**Criterio de éxito:** Upgrade aplica inmediatamente + evento registrado

**Falla si:** Cache mantiene políticas antiguas

---

## RESUMEN DE COBERTURA

| Grupo | Tests | Cubre |
|-------|-------|-------|
| **SESSION** | 4 | JWT válido, expiración, credenciales, protección endpoints |
| **SCOPE** | 4 | Aislamiento, validación cross-scope, rechazo de recursos externos |
| **EVENT** | 4 | Registro con hash, inmutabilidad, queryabilidad, metadata completa |
| **GOV** | 4 | Políticas bloquean/permiten, default deny, upgrade sin cache |
| **TOTAL** | **16** | **Arquitectura AUP completa validada** |

---

## IMPLEMENTACIÓN SUGERIDA

### Estructura de archivos:
```
tests/
├── __init__.py
├── conftest.py              # Fixtures globales (db, client, usuarios)
├── test_1_session.py        # Tests 1.1 a 1.4
├── test_2_scope.py          # Tests 2.1 a 2.4
├── test_3_event.py          # Tests 3.1 a 3.4
└── test_4_gov.py            # Tests 4.1 a 4.4
```

### ⚠️ ORDEN DE EJECUCIÓN RECOMENDADO (AUP-first)

**No por dependencia técnica, por dependencia conceptual:**

1. **test_1_session.py** → Valida IDENTIDAD (base de todo)
2. **test_2_scope.py** → Valida ALCANCE (contexto de operaciones)
3. **test_3_event.py** → Valida EVIDENCIA (trazabilidad de acciones)
4. **test_4_gov.py** → Valida GOBIERNO (políticas sobre operaciones)

**Razón AUP:**  
Cada plano depende conceptualmente del anterior.  
No puedes validar scope sin identidad.  
No puedes validar eventos sin scope.  
No puedes validar gobierno sin eventos.

**Comando recomendado:**
```bash
pytest tests/test_1_session.py tests/test_2_scope.py tests/test_3_event.py tests/test_4_gov.py -v
```

Esto mantiene orden lógico en reporte de fallos (si SESSION falla, no tiene sentido ver errores de GOV).

### Fixtures necesarias (`conftest.py`):
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def db():
    """Base de datos temporal para cada test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture(scope="function")
def client(db):
    """Cliente FastAPI con override de BD"""
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def usuario_base(db):
    """Usuario de prueba con scope asignado"""
    user = Usuario(
        email="test@example.com",
        password_hash=hash_password("password123"),
        scope_id=1
    )
    db.add(user)
    db.commit()
    return user

@pytest.fixture
def politica_qr_7dias(db):
    """Política QR con límite 7 días"""
    politica = Policy(
        nombre="qr_vigencia_dias",
        tipo="threshold",
        limite=7
    )
    db.add(politica)
    db.commit()
    return politica
```

### Comando de ejecución:
```bash
# Todos los tests
pytest tests/ -v

# Grupo específico
pytest tests/test_4_gov.py -v

# Test individual
pytest tests/test_4_gov.py::test_politica_deniega_qr_excede_vigencia -v

# Con coverage
pytest tests/ --cov=backend --cov-report=html
```

---

## CRITERIOS DE APROBACIÓN

**✅ Batería completa pasa si:**
- 16/16 tests en verde
- Coverage mínimo 80% en módulos críticos:
  - `backend/core/auth/jwt.py`
  - `backend/core/scope/validator.py`
  - `backend/core/event/registry.py`
  - `backend/core/gov/facade.py`

**❌ Batería falla si:**
- Cualquier test rojo
- Se detecta violación de axioma AUP (ej: operación sin evento)
- Hash SHA-256 no coincide con payload

---

## PRÓXIMOS PASOS DESPUÉS DE TESTS

1. **Si todos los tests pasan:**
   - ✅ Arquitectura AUP validada
   - ✅ Proceder a deployment piloto
   - ✅ Ejecutar validación manual (docs/AUP_GOV_VALIDACION.md)

2. **Si tests fallan:**
   - ❌ Identificar plano violado (SESSION, SCOPE, EVENT, GOV)
   - ❌ Refactorizar código para cumplir axiomas
   - ❌ Re-ejecutar batería

3. **Testing continuo:**
   - Agregar tests para nuevas operaciones críticas
   - Mantener cobertura >80%
   - Ejecutar en CI/CD antes de merge

---

**Diseño AUP-first: Tests validan principios, no solo funcionalidad**  
**Versión: 3.0.0-aup-gov**  
**Fecha: Diciembre 2024**
