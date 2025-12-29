# AUP_SCOPE - Arquitectura de Alcance Estructural

## 🎯 PASO 2 de Arquitectura AUP

Sistema de validación de alcance (scope) que define **DÓNDE** una identidad puede actuar dentro del sistema multi-tenant.

---

## 📐 Declaración de Entidades AUP

### **AUP_TENANT** (Entidad Contenedora)

**Qué es:** Frontera estructural de datos, operación y auditoría

**En MSP_AXS:** Tenant = Condominio

**Propósito:**
- Segregación de datos
- Límite de operaciones
- Unidad de auditoría

**Mapeo en código:**
- Tabla: `condominios_exo`
- Identificador: `condominio_id`

---

### **AUP_SCOPE** (Entidad Relacional Viva)

**Qué es:** Declaración explícita del alcance permitido de una identidad sobre un tenant

**NO ES:**
- ❌ Un rol (el rol define QUÉ, el scope define DÓNDE)
- ❌ Permisos RBAC tradicionales
- ❌ Inferible o implícito

**ES:**
- ✅ Declaración explícita de alcance
- ✅ Validable estructuralmente
- ✅ Dinámico (no se serializa en JWT)

**Atributos:**
```python
AUP_SCOPE {
    identity_id: str      # AUP_IDENTITY que posee este alcance
    tenant_id: str        # AUP_TENANT sobre el que aplica
    access_level: enum    # Nivel de acceso en el tenant
    estado: enum          # activo/inactivo/suspendido/revocado
    created_at: datetime
    revoked_at: datetime?
}
```

**Mapeo en código:**
- Tabla: `user_tenant_scope`
- Modelo: `UserTenantScope`

---

## 🔗 Relaciones AUP

```
AUP_IDENTITY (Usuario)
     │
     │ tiene múltiples
     ▼
AUP_SCOPE ───────────> AUP_TENANT (Condominio)
     │                      │
     │ autoriza             │ contiene
     │ acciones en          │ recursos
     ▼                      ▼
Acción/Recurso ◄─── pertenece a ─── AUP_TENANT
```

**Ejemplo concreto:**
```
Usuario "Juan Pérez" (AUP_IDENTITY)
  ├── SCOPE en Condominio A (Guardia)
  ├── SCOPE en Condominio B (Residente)
  └── SCOPE en Condominio C (Admin)

Intenta ver visitas de Condominio A:
  ✅ Tiene SCOPE (Guardia) → Permitido
  
Intenta ver visitas de Condominio D:
  ❌ No tiene SCOPE → 403 Forbidden
```

---

## ⚖️ Axiomas (Reglas Inmutables)

### **1. AXIOMA DE FRONTERA**
```
Ninguna acción ocurre fuera de un AUP_TENANT.
```
**Implicación:** Todo endpoint debe conocer el tenant objetivo explícitamente.

### **2. AXIOMA DE ALCANCE EXPLÍCITO**
```
El rol define QUÉ puedes hacer.
El scope define DÓNDE puedes hacerlo.
```
**Implicación:** `rol="ADMIN"` sin scope en un tenant = sin acceso.

### **3. AXIOMA DE NO-INFERENCIA**
```
El sistema NO infiere alcance.
El sistema VALIDA alcance declarado.
```
**Implicación:** No asumir "si es admin global, puede en todos los tenants".

### **4. AXIOMA DE EXISTENCIA OPERATIVA**
```
Una AUP_IDENTITY sin AUP_SCOPE válido en un tenant
no existe operativamente en ese tenant.
```
**Implicación:** Sin scope = sin operaciones, como si no existiera.

### **5. AXIOMA DE DINAMISMO**
```
AUP_SCOPE NO se serializa en AUP_SESSION (JWT).
Se valida en tiempo de ejecución.
```
**Implicación:** Revocar scope tiene efecto inmediato (no esperar a que expire JWT).

---

## 🗂️ Estructura de Archivos

```
backend/core/scope/
├── __init__.py              # Declaración conceptual AUP
├── validator.py             # validar_scope() - Función central
└── dependencies.py          # Integración FastAPI

backend/db/models.py
└── UserTenantScope          # Materialización de AUP_SCOPE
    └── ScopeStatus          # Estados: activo, inactivo, suspendido, revocado
    └── AccessLevel          # Niveles: msp_admin, admin_condominio, guardia, residente, lectura
```

---

## 🔑 Función Central: `validar_scope()`

```python
def validar_scope(
    db: Session,
    usuario: Usuario,           # AUP_IDENTITY
    tenant_id: str,             # AUP_TENANT objetivo
    required_level: AccessLevel # Nivel mínimo requerido
) -> bool
```

**Qué hace:**
1. Busca AUP_SCOPE para (usuario_id, tenant_id)
2. Verifica estado == ACTIVO
3. Verifica access_level >= required_level (jerarquía)
4. Retorna True/False (NO lanza excepciones)

**Jerarquía de Access Levels:**
```
MSP_ADMIN (100)
    ↓
ADMIN_CONDOMINIO (80)
    ↓
GUARDIA (60)
    ↓
RESIDENTE (40)
    ↓
LECTURA (20)
```

Un usuario con `ADMIN_CONDOMINIO` puede hacer lo que hace `GUARDIA` o `RESIDENTE`.

---

## 🚀 Uso en Endpoints

### **Método 1: Validación Manual**
```python
@router.post("/visitas")
def crear_visita(
    data: VisitaCreate,
    usuario: Usuario = Depends(get_current_user),  # PASO 1: AUP_SESSION
    db: Session = Depends(get_db)
):
    # PASO 2: AUP_SCOPE
    validate_user_owns_resource_in_tenant(
        usuario=usuario,
        resource_tenant_id=data.condominio_id,
        db=db,
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    # Si llega aquí, tiene scope válido
    return crear_visita(...)
```

### **Método 2: Dependency (Path Param)**
```python
from backend.core.scope.dependencies import RequireAdminCondominioScope

@router.get("/condominio/{condominio_id}/visitas")
def get_visitas(
    condominio_id: str,
    _scope: None = Depends(RequireAdminCondominioScope),  # Valida automáticamente
):
    # Si llega aquí, tiene scope de ADMIN_CONDOMINIO en ese tenant
    return visitas
```

---

## 💡 Diferencia Conceptual: Antes vs Ahora

### **ANTES (Solo Roles):**
```python
@router.get("/visitas")
def get_visitas(usuario: Usuario = Depends(get_current_user)):
    if usuario.rol != "RESIDENTE":
        raise HTTPException(403)
    
    # Problema: ¿De qué condominio?
    # ¿Puede ver visitas de TODOS los condominios?
    return visitas  # ← PELIGRO: scope implícito
```

**Problema:** No hay validación de tenant, solo de rol.

### **AHORA (AUP_SCOPE):**
```python
@router.post("/visitas")
def crear_visita(
    data: VisitaCreate,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validar scope explícitamente
    validate_user_owns_resource_in_tenant(
        usuario=usuario,
        resource_tenant_id=data.condominio_id,
        db=db,
        required_level=AccessLevel.ADMIN_CONDOMINIO
    )
    
    # Ahora SÍ sabemos:
    # 1. Usuario autenticado (AUP_SESSION)
    # 2. Tiene scope en este tenant específico (AUP_SCOPE)
    # 3. Con nivel suficiente (ADMIN_CONDOMINIO)
    return crear_visita(...)
```

**Solución:** Validación explícita de alcance en tenant específico.

---

## 🎯 Casos de Uso Habilitados

### **1. First Tier Natural**
Un usuario puede operar en múltiples tenants:

```sql
-- Juan Pérez tiene múltiples scopes
INSERT INTO user_tenant_scope VALUES
  ('juan123', 'condo_a', 'guardia', 'activo'),
  ('juan123', 'condo_b', 'residente', 'activo'),
  ('juan123', 'condo_c', 'admin_condominio', 'activo');
```

Juan puede:
- Validar QR en Condominio A (como guardia)
- Ver sus visitas en Condominio B (como residente)
- Administrar todo en Condominio C (como admin)

### **2. Revocación Granular**
```python
# Revocar acceso de Juan a Condominio A (sin afectar B y C)
revocar_scope(db, scope_id=123)

# Efecto inmediato (no espera a que expire JWT)
```

### **3. Auditoría Estructural**
```sql
-- ¿Quién tuvo acceso a Condominio A?
SELECT usuario_id, access_level, created_at, revoked_at
FROM user_tenant_scope
WHERE tenant_id = 'condo_a';
```

### **4. Delegación Temporal (Futuro)**
```python
# Crear scope con vigencia
crear_scope(
    usuario_id="temp_admin",
    tenant_id="condo_a",
    access_level=AccessLevel.ADMIN_CONDOMINIO,
    metadata={"expires_at": "2025-12-31"}
)
```

---

## 🔄 Integración con PASO 1 (AUP_SESSION)

### **PASO 1: AUP_SESSION (JWT)**
```
Usuario hace login
  ↓
Sistema valida credenciales
  ↓
Genera JWT: {sub: "user123", role: "RESIDENTE"}
  ↓
Cliente recibe token
```

### **PASO 2: AUP_SCOPE (Validación en Runtime)**
```
Cliente hace request: POST /visitas
  Header: Authorization: Bearer <JWT>
  Body: {condominio_id: "condo_a", ...}
  ↓
Sistema valida JWT (AUP_SESSION)
  ✓ Token válido → usuario = "user123"
  ↓
Sistema valida SCOPE (AUP_SCOPE)
  SELECT * FROM user_tenant_scope
  WHERE usuario_id = "user123"
    AND tenant_id = "condo_a"
    AND estado = "activo"
  ↓
  ✓ Scope encontrado → Permitir acción
  ❌ Scope no encontrado → 403 Forbidden
```

**Clave:** JWT NO cambia, solo valida identidad. SCOPE valida alcance.

---

## 📊 Comparación: JWT vs Scope

| Aspecto | AUP_SESSION (JWT) | AUP_SCOPE (BD) |
|---------|------------------|----------------|
| **Qué valida** | Identidad (quién es) | Alcance (dónde puede actuar) |
| **Dónde vive** | Cliente (token) | Servidor (BD) |
| **Revocación** | Solo al expirar | Inmediata |
| **Serialización** | Sí (JWT payload) | No (dinámico) |
| **Cambios** | Requiere re-login | Efecto inmediato |
| **Propósito** | Autenticación | Autorización granular |

---

## 🔮 Preparación para PASO 3: AUP_EVENT

Cada validación de scope será auditable:

```python
# Futuro: Cada validación genera evento
AUP_EVENT {
    tipo: "scope_validation",
    identity_id: "user123",
    tenant_id: "condo_a",
    accion: "crear_visita",
    resultado: "permitido",
    timestamp: "2025-12-29T10:30:00Z"
}
```

Esto habilita:
- Auditoría completa de accesos
- Detección de intentos no autorizados
- Compliance (GDPR, SOC2, etc.)

---

## ✅ Resultado Implementado

### **Archivos creados:**
- `backend/core/scope/__init__.py` - Declaración conceptual
- `backend/core/scope/validator.py` - Función `validar_scope()`
- `backend/core/scope/dependencies.py` - Integración FastAPI
- `backend/db/models.py` - Modelo `UserTenantScope` + Enums

### **Endpoints migrados (ejemplo):**
- `POST /visitas` - Valida scope antes de crear

### **Base sólida para:**
- ✅ Multi-tenant seguro (First Tier)
- ✅ Revocación granular inmediata
- ✅ Auditoría estructural
- ✅ PASO 3: AUP_EVENT (histórico de eventos)

---

**PASO 2 completado. Sistema listo para AUP_EVENT.**
