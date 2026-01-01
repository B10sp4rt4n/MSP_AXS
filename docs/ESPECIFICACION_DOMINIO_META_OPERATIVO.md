# Especificación Técnica: Dominio Meta-Operativo MSP_AXS

**Versión:** 1.0  
**Fecha:** 1 de enero de 2026  
**Estado:** Especificación técnica para implementación  
**Prerequisito:** Dictamen arquitectónico aprobado

---

## 1. Definición del Dominio Meta-Operativo

### 1.1 Acciones Permitidas (exhaustivas)

```
META_ACTION {
    ASSIGN_IDENTITY_TO_TENANT     // Crear relación Identity→Tenant
    REVOKE_IDENTITY_FROM_TENANT   // Revocar relación Identity→Tenant
    LIST_TENANT_ASSIGNMENTS       // Listar qué identidades tiene un tenant
    LIST_IDENTITY_ASSIGNMENTS     // Listar en qué tenants está una identidad
}
```

**NO existen otras acciones.** Cualquier otra operación está FUERA del dominio meta-operativo.

### 1.2 Acciones Explícitamente PROHIBIDAS

El dominio meta-operativo NO puede:

```
❌ Ver datos operativos de un tenant (visitas, QRs, evidencias)
❌ Modificar datos operativos (crear visitas, aprobar accesos)
❌ Ejecutar flujos de negocio (login de usuarios, validación de QRs)
❌ Definir permisos internos del tenant (eso es responsabilidad del FIRST_TIER)
❌ Bypassar tenant_id en consultas RLS
❌ Operar con tenant_id activo
❌ Leer tablas operativas (visitas, evidencias, casetas)
❌ Inyectar lógica en flujos existentes
```

### 1.3 Límite de Responsabilidad

**Comienza:** Cuando una identity autorizada solicita asignar/revocar relación  
**Termina:** Cuando el registro en `identity_tenant_assignments` es creado/marcado como revocado

**Después del límite:**
- La lógica operativa existente toma control
- El sistema valida scope con `user_tenant_scope` (tabla existente)
- Los endpoints operativos funcionan sin cambios

---

## 2. Modelo de Datos Mínimo

### 2.1 Nueva Entidad: `identity_tenant_assignments`

```
IDENTITY_TENANT_ASSIGNMENT {
    // Identificación
    assignment_id: STRING PK
    
    // Relación (QUÉ se asigna)
    identity_id: STRING FK(usuarios.usuario_id) NOT NULL
    tenant_id: STRING FK(condominios_exo.condominio_id) NOT NULL
    assignment_type: ENUM('FIRST_TIER_ADMIN', 'REGULAR_ADMIN') NOT NULL
    
    // Trazabilidad (QUIÉN y CUÁNDO)
    assigned_by_identity_id: STRING FK(usuarios.usuario_id) NOT NULL
    assigned_at: TIMESTAMP NOT NULL DEFAULT now()
    
    // Revocación
    revoked: BOOLEAN NOT NULL DEFAULT false
    revoked_by_identity_id: STRING FK(usuarios.usuario_id) NULL
    revoked_at: TIMESTAMP NULL
    revocation_reason: TEXT NULL
    
    // Índices
    INDEX idx_identity (identity_id)
    INDEX idx_tenant (tenant_id)
    INDEX idx_active (identity_id, tenant_id, revoked) WHERE revoked = false
    
    // Constraint: Una identidad solo puede tener UNA asignación activa por tenant
    UNIQUE (identity_id, tenant_id) WHERE revoked = false
}
```

### 2.2 Relación con Entidades Existentes

```
usuarios (existente)
    ↓
    1:N
    ↓
identity_tenant_assignments (NUEVA)
    ↓
    N:1
    ↓
condominios_exo (existente)
```

**NO se modifica ninguna tabla existente.**

### 2.3 Sincronización con Tabla Operativa

Una vez creada la asignación, el sistema PUEDE crear el scope operativo:

```
identity_tenant_assignments (META)
    ↓
    triggers/observa
    ↓
user_tenant_scope (OPERATIVA)
```

**Decisión de implementación:** 
- Opción A: Trigger DB que crea `user_tenant_scope` al insertar `identity_tenant_assignments`
- Opción B: Función aplicativa que crea ambos registros en transacción
- **Recomendación:** Opción B (control aplicativo explícito)

---

## 3. Flujo Funcional Canónico

### 3.1 Flujo: ASSIGN_IDENTITY_TO_TENANT

```
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1: Autenticación                                           │
│ • POST /meta/assignments                                        │
│ • JWT en header                                                 │
│ • Decodificar identity del actor                                │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 2: Validación de Authority (CRÍTICO)                      │
│                                                                 │
│ Query: SELECT * FROM authorities_gov                            │
│        WHERE identity_id = actor.usuario_id                     │
│        AND tipo = 'GLOBAL'                                      │
│        AND estado = 'ACTIVO'                                    │
│                                                                 │
│ Si NO existe: FALLAR DURO con 403                              │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 3: Validación de Entidades                                │
│ • Verificar que identity_id existe en usuarios                  │
│ • Verificar que tenant_id existe en condominios_exo             │
│ • Verificar que NO existe asignación activa previa              │
│                                                                 │
│ Si alguna falla: FALLAR DURO con 400/409                       │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: Creación de Asignación (SIN TENANT ACTIVO)             │
│                                                                 │
│ BEGIN TRANSACTION                                               │
│                                                                 │
│   INSERT INTO identity_tenant_assignments (                     │
│     assignment_id,                                              │
│     identity_id,                                                │
│     tenant_id,                                                  │
│     assignment_type,                                            │
│     assigned_by_identity_id,                                    │
│     assigned_at                                                 │
│   )                                                             │
│                                                                 │
│ COMMIT                                                          │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 5: Registro de Evento (AUP_EVENT)                         │
│                                                                 │
│ INSERT INTO events_aup (                                        │
│   identity_id: actor.usuario_id,                                │
│   session_token_hash: SHA256(JWT),                              │
│   tenant_id: NULL,  // ← NO hay tenant activo                  │
│   entidad: 'IDENTITY_TENANT_ASSIGNMENT',                        │
│   entidad_id: assignment_id,                                    │
│   accion: 'ASSIGN',                                             │
│   resultado: 'PERMITIDO',                                       │
│   metadata: {                                                   │
│     target_identity_id,                                         │
│     target_tenant_id,                                           │
│     assignment_type                                             │
│   }                                                             │
│ )                                                               │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 6: Sincronización con Scope Operativo (OPCIONAL)          │
│                                                                 │
│ SI assignment_type requiere scope operativo:                    │
│                                                                 │
│   INSERT INTO user_tenant_scope (                               │
│     usuario_id: identity_id,                                    │
│     tenant_id: tenant_id,                                       │
│     access_level: derivar de assignment_type,                   │
│     estado: 'ACTIVO'                                            │
│   )                                                             │
│                                                                 │
│ Esto permite que la identidad opere dentro del tenant           │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ RESPUESTA: 201 Created                                          │
│ {                                                               │
│   "assignment_id": "...",                                       │
│   "identity_id": "...",                                         │
│   "tenant_id": "...",                                           │
│   "assigned_at": "..."                                          │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Flujo: REVOKE_IDENTITY_FROM_TENANT

```
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1-3: Igual que ASSIGN (autenticación y validaciones)      │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: Revocación (SIN TENANT ACTIVO)                         │
│                                                                 │
│ BEGIN TRANSACTION                                               │
│                                                                 │
│   UPDATE identity_tenant_assignments                            │
│   SET revoked = true,                                           │
│       revoked_by_identity_id = actor.usuario_id,                │
│       revoked_at = now(),                                       │
│       revocation_reason = ?                                     │
│   WHERE assignment_id = ?                                       │
│   AND revoked = false                                           │
│                                                                 │
│ COMMIT                                                          │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 5: Registro de Evento (AUP_EVENT)                         │
│   accion: 'REVOKE'                                              │
│   resultado: 'PERMITIDO'                                        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 6: Sincronización con Scope Operativo                     │
│                                                                 │
│   UPDATE user_tenant_scope                                      │
│   SET estado = 'REVOCADO'                                       │
│   WHERE usuario_id = identity_id                                │
│   AND tenant_id = tenant_id                                     │
│                                                                 │
│ La identidad pierde acceso operativo inmediatamente             │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Puntos Críticos de NO-TENANT

**Dónde NO se inyecta tenant_id:**

```sql
-- ✅ CORRECTO: Consulta meta-operativa
SELECT * FROM identity_tenant_assignments
WHERE identity_id = ?;

-- ❌ INCORRECTO: Intentar usar RLS en tabla meta
SELECT * FROM identity_tenant_assignments
WHERE tenant_id = current_setting('app.tenant_id')::text;
```

**Middleware separado:**

```
/api/visitas       → usa middleware RequireTenant (inyecta tenant_id)
/api/auth          → NO usa middleware de tenant
/meta/assignments  → NO usa middleware de tenant (dominio meta)
```

---

## 4. Eventos y Evidencia

### 4.1 Eventos Registrados

Cada acción meta-operativa genera UN evento:

```
AUP_EVENT {
    // Identidad que ejecuta la acción meta
    identity_id: actor.usuario_id
    session_token_hash: SHA256(JWT)
    
    // NO hay tenant activo en acciones meta
    tenant_id: NULL
    
    // Entidad afectada
    entidad: 'IDENTITY_TENANT_ASSIGNMENT'
    entidad_id: assignment_id
    
    // Acción
    accion: 'ASSIGN' | 'REVOKE' | 'LIST'
    resultado: 'PERMITIDO' | 'DENEGADO'
    
    // Contexto específico
    metadata: {
        target_identity_id: string,
        target_tenant_id: string,
        assignment_type?: string,
        revocation_reason?: string
    }
    
    // Temporal
    timestamp: datetime
    hash: SHA256(campos_anteriores)
}
```

### 4.2 Reconstrucción de Auditoría

**Pregunta 1: ¿Quién asignó a Juan como admin del Condominio A?**

```sql
SELECT e.identity_id as quien_asigno,
       e.metadata->>'target_identity_id' as a_quien,
       e.metadata->>'target_tenant_id' as en_que_tenant,
       e.timestamp as cuando
FROM events_aup e
WHERE e.entidad = 'IDENTITY_TENANT_ASSIGNMENT'
  AND e.accion = 'ASSIGN'
  AND e.metadata->>'target_identity_id' = 'juan_id'
  AND e.metadata->>'target_tenant_id' = 'condo_a'
ORDER BY e.timestamp DESC
LIMIT 1;
```

**Pregunta 2: ¿Qué asignaciones ha hecho el Super Admin X?**

```sql
SELECT e.metadata->>'target_identity_id' as identidad_asignada,
       e.metadata->>'target_tenant_id' as tenant,
       e.accion,
       e.timestamp
FROM events_aup e
WHERE e.identity_id = 'super_admin_x'
  AND e.entidad = 'IDENTITY_TENANT_ASSIGNMENT'
ORDER BY e.timestamp DESC;
```

**Pregunta 3: ¿Ha sido revocado el acceso de María al Condominio B?**

```sql
SELECT e.accion,
       e.resultado,
       e.timestamp,
       e.metadata->>'revocation_reason' as motivo
FROM events_aup e
WHERE e.entidad = 'IDENTITY_TENANT_ASSIGNMENT'
  AND e.metadata->>'target_identity_id' = 'maria_id'
  AND e.metadata->>'target_tenant_id' = 'condo_b'
ORDER BY e.timestamp DESC
LIMIT 1;
```

### 4.3 Información Mínima Obligatoria

Todo evento meta-operativo DEBE contener:

```
OBLIGATORIO:
- identity_id (quién actúa)
- session_token_hash (contexto de sesión)
- entidad = 'IDENTITY_TENANT_ASSIGNMENT'
- accion (ASSIGN/REVOKE/LIST)
- resultado (PERMITIDO/DENEGADO)
- metadata.target_identity_id (a quién afecta)
- metadata.target_tenant_id (en qué tenant)
- timestamp (cuándo)
- hash (integridad)

OPCIONAL pero RECOMENDADO:
- motivo (para REVOKE)
- metadata.assignment_type (tipo de asignación)
```

---

## 5. Controles de Seguridad

### 5.1 Validaciones que DEBEN FALLAR DURO

```
VALIDACIÓN 1: Authority GLOBAL activa
IF NOT EXISTS (
    SELECT 1 FROM authorities_gov
    WHERE identity_id = actor.usuario_id
    AND tipo = 'GLOBAL'
    AND estado = 'ACTIVO'
):
    FAIL 403 "No tiene authority GLOBAL para acciones meta-operativas"
```

```
VALIDACIÓN 2: No self-assignment operativo
IF actor.usuario_id == target_identity_id
   AND assignment_type implica scope operativo:
    FAIL 400 "GLOBAL authority no puede asignarse scope operativo"
```

```
VALIDACIÓN 3: Tenant existe
IF NOT EXISTS (
    SELECT 1 FROM condominios_exo
    WHERE condominio_id = target_tenant_id
):
    FAIL 400 "Tenant no existe"
```

```
VALIDACIÓN 4: No duplicados activos
IF EXISTS (
    SELECT 1 FROM identity_tenant_assignments
    WHERE identity_id = target_identity_id
    AND tenant_id = target_tenant_id
    AND revoked = false
):
    FAIL 409 "Ya existe asignación activa"
```

```
VALIDACIÓN 5: Asignación existe para revocación
IF NOT EXISTS (
    SELECT 1 FROM identity_tenant_assignments
    WHERE assignment_id = ?
    AND revoked = false
):
    FAIL 404 "Asignación no encontrada o ya revocada"
```

### 5.2 Errores que NO se deben "Suavizar"

```
❌ NO hacer: "Si falla, crear authority automáticamente"
✅ Hacer: FAIL explícito con mensaje claro

❌ NO hacer: "Permitir si es admin de condominio"
✅ Hacer: Solo GLOBAL authority puede ejecutar acciones meta

❌ NO hacer: "Crear tenant si no existe"
✅ Hacer: FAIL, el tenant debe existir previamente

❌ NO hacer: "Ignorar assignment duplicado"
✅ Hacer: FAIL, operación idempotente pero con error explícito

❌ NO hacer: "Permitir lista global de datos operativos"
✅ Hacer: Solo listar relaciones meta, no datos operativos
```

### 5.3 Límites de Alcance Rígidos

```python
# ✅ PERMITIDO (meta-operativo)
def assign_identity_to_tenant(actor, target_identity, target_tenant):
    validate_global_authority(actor)
    create_assignment(target_identity, target_tenant)
    log_event()

# ❌ PROHIBIDO (operativo)
def list_visitas_all_tenants(actor):
    # NO. Esto es operativo y cross-tenant.
    # Viola RLS y separación de dominios
    pass

# ❌ PROHIBIDO (bypass)
def assign_with_bypass(actor, target_identity, target_tenant):
    # NO. No hay "bypass mode" ni "special access"
    pass
```

---

## 6. Pruebas de Correctitud

### 6.1 Casos que DEBEN PASAR

```
TEST 1: Asignación válida
DADO: Actor con GLOBAL authority activa
CUANDO: Asigna identity_id='user_1' a tenant_id='condo_a'
ENTONCES: 
  - Registro creado en identity_tenant_assignments
  - Evento registrado en events_aup
  - HTTP 201

TEST 2: Revocación válida
DADO: Asignación activa existente
CUANDO: Actor GLOBAL revoca la asignación
ENTONCES:
  - Campo revoked=true en identity_tenant_assignments
  - Evento de REVOKE registrado
  - Scope operativo marcado como REVOCADO
  - HTTP 200

TEST 3: Listar asignaciones de un tenant
DADO: Tenant con 3 asignaciones activas
CUANDO: Actor GLOBAL lista asignaciones del tenant
ENTONCES:
  - Retorna 3 registros
  - NO retorna datos operativos del tenant
  - HTTP 200

TEST 4: Listar asignaciones de una identidad
DADO: Identity con asignaciones en 2 tenants
CUANDO: Actor GLOBAL lista asignaciones de la identity
ENTONCES:
  - Retorna 2 registros
  - Incluye tenant_ids
  - HTTP 200
```

### 6.2 Casos que DEBEN FALLAR

```
TEST 5: Sin authority GLOBAL
DADO: Actor con FIRST_TIER authority (no GLOBAL)
CUANDO: Intenta asignar identity a tenant
ENTONCES: HTTP 403 "No tiene authority GLOBAL"

TEST 6: Tenant inexistente
DADO: Actor GLOBAL válido
CUANDO: Intenta asignar a tenant_id='inexistente'
ENTONCES: HTTP 400 "Tenant no existe"

TEST 7: Asignación duplicada
DADO: Identity ya asignada a tenant (activa)
CUANDO: Intenta asignar nuevamente
ENTONCES: HTTP 409 "Ya existe asignación activa"

TEST 8: Self-assignment con scope operativo
DADO: Actor GLOBAL intenta asignarse a sí mismo
CUANDO: Con assignment_type que crea scope operativo
ENTONCES: HTTP 400 "GLOBAL authority no puede tener scope operativo"

TEST 9: Revocación de asignación ya revocada
DADO: Asignación con revoked=true
CUANDO: Intenta revocar nuevamente
ENTONCES: HTTP 404 "Asignación no encontrada o ya revocada"

TEST 10: Intentar ver datos operativos desde meta
DADO: Actor GLOBAL
CUANDO: Intenta GET /meta/tenants/condo_a/visitas
ENTONCES: HTTP 404 "Endpoint no existe" (no se implementa)
```

### 6.3 Casos Frontera Importantes

```
TEST 11: Actor pierde authority durante operación
DADO: Actor con GLOBAL authority
CUANDO: Authority es revocada en otra sesión
Y LUEGO: Intenta asignar identity
ENTONCES: HTTP 403 (validación en tiempo real)

TEST 12: Asignación + Revocación + Re-asignación
DADO: Identity asignada a tenant
CUANDO: Se revoca
Y LUEGO: Se re-asigna
ENTONCES: 
  - Nuevo registro en identity_tenant_assignments
  - Ambos eventos (REVOKE y ASSIGN) auditables
  - HTTP 201

TEST 13: Múltiples asignaciones diferentes tenants
DADO: Identity sin asignaciones
CUANDO: Se asigna a tenant_a y tenant_b
ENTONCES:
  - 2 registros independientes
  - 2 scopes operativos independientes
  - Identity puede operar en ambos tenants
  - HTTP 201 para cada asignación

TEST 14: Revocación en cascada (conceptual)
DADO: Identity con scope operativo activo en tenant
CUANDO: Se revoca assignment
ENTONCES:
  - Scope operativo se marca REVOCADO
  - Próximo intento de operar en tenant → HTTP 403
  - Eventos pasados NO se borran (inmutables)

TEST 15: Listar sin filtros (límite de seguridad)
DADO: Actor GLOBAL
CUANDO: GET /meta/assignments sin filtros
ENTONCES: HTTP 400 "Debe especificar identity_id o tenant_id"
(evita volcar toda la tabla)
```

---

## 7. Implementación por Capas

### 7.1 Capa de Dominio

```
backend/core/meta/
├── __init__.py              # Enums: MetaAction, AssignmentType
├── assignments.py           # Funciones: create, revoke, list
└── validators.py            # Validaciones de autoridad y existencia
```

**Responsabilidad:** Lógica pura sin dependencias HTTP.

### 7.2 Capa de Datos

```
backend/db/models.py
  + IdentityTenantAssignment  # Nuevo modelo

database/migrations/
  + migration_05_meta_operativo.sql
```

**Responsabilidad:** Persistencia y esquema.

### 7.3 Capa de API

```
backend/routers/meta.py      # Endpoints: POST/DELETE/GET /meta/assignments
```

**Middleware:** NO usa `RequireTenant`. Usa `RequireGlobalAuthority` (nuevo).

### 7.4 Capa de Eventos

```
backend/core/meta/events.py  # Integración con registrar_evento()
```

**Responsabilidad:** Registrar eventos meta-operativos en `events_aup`.

---

## 8. Contrato de Interfaces

### 8.1 Endpoint: Asignar Identity a Tenant

```
POST /meta/assignments

Headers:
  Authorization: Bearer <JWT>

Body:
{
  "identity_id": "user_abc123",
  "tenant_id": "condo_xyz789",
  "assignment_type": "FIRST_TIER_ADMIN"
}

Respuesta 201:
{
  "assignment_id": "assign_def456",
  "identity_id": "user_abc123",
  "tenant_id": "condo_xyz789",
  "assignment_type": "FIRST_TIER_ADMIN",
  "assigned_by": "super_admin_001",
  "assigned_at": "2026-01-01T12:00:00Z"
}

Errores:
  400 - Tenant no existe / Identity no existe / Self-assignment inválido
  403 - No tiene GLOBAL authority
  409 - Ya existe asignación activa
```

### 8.2 Endpoint: Revocar Asignación

```
DELETE /meta/assignments/{assignment_id}

Headers:
  Authorization: Bearer <JWT>

Body:
{
  "reason": "Cambio de administración del condominio"
}

Respuesta 200:
{
  "assignment_id": "assign_def456",
  "revoked": true,
  "revoked_by": "super_admin_001",
  "revoked_at": "2026-01-15T14:30:00Z",
  "reason": "Cambio de administración del condominio"
}

Errores:
  403 - No tiene GLOBAL authority
  404 - Asignación no existe o ya revocada
```

### 8.3 Endpoint: Listar Asignaciones

```
GET /meta/assignments?identity_id={id}
GET /meta/assignments?tenant_id={id}

Headers:
  Authorization: Bearer <JWT>

Query params (uno OBLIGATORIO):
  identity_id: Filtrar por identidad
  tenant_id: Filtrar por tenant
  include_revoked: boolean (default: false)

Respuesta 200:
{
  "assignments": [
    {
      "assignment_id": "assign_def456",
      "identity_id": "user_abc123",
      "tenant_id": "condo_xyz789",
      "assignment_type": "FIRST_TIER_ADMIN",
      "assigned_at": "2026-01-01T12:00:00Z",
      "revoked": false
    }
  ],
  "total": 1
}

Errores:
  400 - Debe especificar identity_id o tenant_id
  403 - No tiene GLOBAL authority
```

---

## 9. Checklist de Implementación

### Fase 1: Estructura Base
- [ ] Crear enum `AssignmentType`
- [ ] Crear enum `MetaAction`
- [ ] Definir modelo `IdentityTenantAssignment`
- [ ] Escribir migración SQL

### Fase 2: Lógica de Dominio
- [ ] Función `validate_global_authority()`
- [ ] Función `create_assignment()`
- [ ] Función `revoke_assignment()`
- [ ] Función `list_assignments()`

### Fase 3: Eventos
- [ ] Integrar con `registrar_evento()`
- [ ] Definir estructura de metadata para eventos meta

### Fase 4: API
- [ ] Middleware `RequireGlobalAuthority`
- [ ] Router `/meta/assignments`
- [ ] Endpoints POST/DELETE/GET

### Fase 5: Sincronización
- [ ] Lógica para crear `user_tenant_scope` al asignar
- [ ] Lógica para marcar scope como REVOCADO al revocar

### Fase 6: Validación
- [ ] Tests unitarios (funciones de dominio)
- [ ] Tests de integración (endpoints)
- [ ] Tests de seguridad (casos que deben fallar)

---

## 10. Criterios de Aceptación

Un revisor independiente debe verificar:

### 10.1 Arquitectura
- [ ] El dominio meta NO toca lógica operativa existente
- [ ] NO hay bypass de RLS
- [ ] NO hay middleware de tenant en rutas meta
- [ ] La tabla meta es independiente de tablas operativas

### 10.2 Seguridad
- [ ] Solo GLOBAL authority puede ejecutar acciones meta
- [ ] NO existe "modo especial" o bypass
- [ ] Validaciones fallan explícitamente
- [ ] Self-assignment con scope operativo está bloqueado

### 10.3 Trazabilidad
- [ ] Toda acción genera evento en `events_aup`
- [ ] Eventos contienen: quién, qué, cuándo, a quién, en qué tenant
- [ ] Eventos son inmutables
- [ ] La auditoría permite reconstruir quién otorgó poder

### 10.4 Correctitud
- [ ] 15 tests de correctitud pasan
- [ ] Casos frontera funcionan correctamente
- [ ] NO hay excepciones no manejadas

### 10.5 Límites
- [ ] El dominio meta NO puede ver datos operativos
- [ ] El dominio meta NO puede operar dentro de tenants
- [ ] Las rutas meta están claramente separadas (`/meta/*`)

---

## 11. Riesgos Residuales

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Actor pierde authority durante operación | Baja | Medio | Validar authority en cada request |
| Confusión entre meta y operativo | Media | Alto | Documentación clara + nombres explícitos |
| Intentos de expandir capacidades meta | Media | Alto | Code review estricto + límite documental |
| Bypass accidental de validaciones | Baja | Crítico | Tests exhaustivos de casos que deben fallar |

---

## 12. No-Alcance Explícito

Este dominio meta-operativo NO incluye:

```
❌ Gestión de roles dentro del tenant (responsabilidad del FIRST_TIER)
❌ Configuración de permisos granulares
❌ Vistas agregadas de datos operativos
❌ Dashboards globales cross-tenant
❌ Exportación masiva de datos
❌ Operaciones de datos (backup, restore)
❌ Modificación de políticas de gobierno (eso es AUP_GOV)
❌ Creación de tenants (eso es operación de negocio)
```

Cualquier solicitud de agregar estas capacidades debe pasar por:
1. Revisión arquitectónica
2. Validación de límites de dominio
3. Aprobación de seguridad

---

**Fin de Especificación Técnica v1.0**

---

**Aprobaciones requeridas:**
- [ ] Arquitecto de seguridad
- [ ] Líder técnico backend
- [ ] Responsable de compliance

**Próximo paso:** Implementación Fase 1
