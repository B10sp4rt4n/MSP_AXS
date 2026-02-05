# Acta de Congelamiento e Implementación Fase Mínima
# Dominio Meta-Operativo MSP_AXS v1.0

**Fecha de congelamiento:** 1 de enero de 2026  
**Versión:** 1.0 (CONGELADA)  
**Estado:** Especificación cerrada / Implementación mínima autorizada  
**Prerequisito:** ESPECIFICACION_DOMINIO_META_OPERATIVO.md v1.0

---

## 1. Declaración de Congelamiento

### 1.1 Confirmación Formal

```
El Dominio Meta-Operativo v1.0 está FORMALMENTE CONGELADO.

Alcance cerrado:
  - ASSIGN_IDENTITY_TO_TENANT
  - REVOKE_IDENTITY_FROM_TENANT
  - LIST_TENANT_ASSIGNMENTS
  - LIST_IDENTITY_ASSIGNMENTS

NO existen otras acciones.
NO se aceptan extensiones.
NO hay "fase 2" planificada.

El dominio es SUFICIENTE y COMPLETO para su propósito:
crear y revocar relaciones Identidad ↔ Tenant de forma auditable.
```

### 1.2 Confirmación de Implementabilidad

```
✅ El dominio v1.0 NO requiere extensiones para ser implementable
✅ El dominio v1.0 NO requiere capacidades adicionales
✅ El dominio v1.0 NO requiere vistas operativas
✅ El dominio v1.0 NO requiere integración con UI
✅ El dominio v1.0 puede funcionar solo con API

Cualquier solicitud de:
  - "agregar solo una cosa más"
  - "sería útil poder ver..."
  - "deberíamos permitir también..."
  
DEBE SER RECHAZADA en revisión de código.
```

### 1.3 Límite de Responsabilidad Declarado

```
EL DOMINIO META-OPERATIVO:
  ✅ Crea relación Identity → Tenant
  ✅ Revoca relación Identity → Tenant
  ✅ Lista relaciones existentes
  ✅ Registra evidencia de quién asignó/revocó

EL DOMINIO META-OPERATIVO NO:
  ❌ Define permisos internos del tenant
  ❌ Opera dentro del tenant
  ❌ Ve datos operativos
  ❌ Bypassa RLS
  ❌ Crea tenants
  ❌ Modifica usuarios
  ❌ Ejecuta lógica de negocio
```

---

## 2. Modelo de Datos Mínimo

### 2.1 Entidad: identity_tenant_assignments

```
Propósito: Registrar relaciones Identidad ↔ Tenant de forma auditable.

Estructura:

identity_tenant_assignments {
    // Identificación única
    assignment_id: VARCHAR(64) PRIMARY KEY
    
    // Relación (QUÉ)
    identity_id: VARCHAR(64) NOT NULL
    tenant_id: VARCHAR(64) NOT NULL
    assignment_type: VARCHAR(32) NOT NULL
    
    // Trazabilidad de creación (QUIÉN y CUÁNDO)
    assigned_by_identity_id: VARCHAR(64) NOT NULL
    assigned_at: TIMESTAMP NOT NULL DEFAULT now()
    
    // Trazabilidad de revocación
    revoked: BOOLEAN NOT NULL DEFAULT false
    revoked_by_identity_id: VARCHAR(64) NULL
    revoked_at: TIMESTAMP NULL
    revocation_reason: TEXT NULL
    
    // Relaciones
    FOREIGN KEY (identity_id) REFERENCES usuarios(usuario_id)
    FOREIGN KEY (tenant_id) REFERENCES condominios_exo(condominio_id)
    FOREIGN KEY (assigned_by_identity_id) REFERENCES usuarios(usuario_id)
    FOREIGN KEY (revoked_by_identity_id) REFERENCES usuarios(usuario_id)
    
    // Índices
    INDEX idx_meta_identity (identity_id)
    INDEX idx_meta_tenant (tenant_id)
    INDEX idx_meta_active (identity_id, tenant_id, revoked) WHERE revoked = false
    
    // Unicidad: Una identity solo puede tener UNA asignación activa por tenant
    UNIQUE (identity_id, tenant_id) WHERE revoked = false
}
```

### 2.2 Valores Permitidos

```
assignment_type ENUM:
  - 'FIRST_TIER_ADMIN'     // Authority FIRST_TIER sobre el tenant
  - 'REGULAR_ADMIN'        // Scope operativo como admin
  - 'OPERATOR'             // Scope operativo como operador

assigned_by_identity_id:
  - DEBE tener authority GLOBAL activa
  - Verificado en tiempo de ejecución

revoked:
  - true: Asignación revocada (histórica)
  - false: Asignación activa
```

### 2.3 Invariantes de Datos

```
INVARIANTE 1: Unicidad activa
  No pueden existir dos registros con:
    identity_id = X
    tenant_id = Y
    revoked = false

INVARIANTE 2: Revocación inmutable
  Si revoked = true:
    revoked_by_identity_id NOT NULL
    revoked_at NOT NULL
    
  NO se puede cambiar revoked de true → false

INVARIANTE 3: Secuencia temporal
  assigned_at < revoked_at (si revoked = true)

INVARIANTE 4: Existencia de entidades
  identity_id DEBE existir en usuarios
  tenant_id DEBE existir en condominios_exo
  assigned_by_identity_id DEBE existir en usuarios
```

---

## 3. Dominio Funcional

### 3.1 Acción: ASSIGN_IDENTITY_TO_TENANT

**Entrada:**
```
actor_identity_id: string       // Quién ejecuta
target_identity_id: string      // A quién se asigna
target_tenant_id: string        // En qué tenant
assignment_type: enum           // Tipo de asignación
```

**Precondiciones (DEBEN cumplirse):**
```
1. actor tiene authority GLOBAL activa
2. target_identity existe en usuarios
3. target_tenant existe en condominios_exo
4. NO existe asignación activa previa (identity + tenant)
5. SI assignment_type implica scope operativo:
     target_identity ≠ actor_identity
```

**Postcondiciones (garantizadas si éxito):**
```
1. Registro creado en identity_tenant_assignments
2. Evento registrado en events_aup
3. Si assignment_type requiere scope operativo:
     Registro creado en user_tenant_scope
```

**Condiciones de Fallo Duro:**
```
FALLO 1: actor NO tiene authority GLOBAL
  → 403 "No tiene authority GLOBAL para acciones meta-operativas"

FALLO 2: target_identity NO existe
  → 400 "Identidad no encontrada"

FALLO 3: target_tenant NO existe
  → 400 "Tenant no existe"

FALLO 4: Asignación activa ya existe
  → 409 "Ya existe asignación activa para esta identidad en este tenant"

FALLO 5: Self-assignment con scope operativo
  → 400 "GLOBAL authority no puede asignarse scope operativo a sí misma"
```

**Límites:**
```
- NO valida si target_identity tiene otros scopes
- NO modifica datos operativos del tenant
- NO crea el tenant si no existe
- NO modifica permisos internos del tenant
```

### 3.2 Acción: REVOKE_IDENTITY_FROM_TENANT

**Entrada:**
```
actor_identity_id: string       // Quién ejecuta
assignment_id: string           // Qué asignación revocar
revocation_reason: string?      // Por qué (opcional)
```

**Precondiciones:**
```
1. actor tiene authority GLOBAL activa
2. assignment_id existe
3. Asignación NO está ya revocada (revoked = false)
```

**Postcondiciones:**
```
1. Campo revoked = true
2. Campos revoked_by_identity_id, revoked_at, revocation_reason actualizados
3. Evento registrado en events_aup
4. Si existe scope operativo asociado:
     Scope marcado como REVOCADO
```

**Condiciones de Fallo Duro:**
```
FALLO 1: actor NO tiene authority GLOBAL
  → 403 "No tiene authority GLOBAL"

FALLO 2: assignment_id NO existe
  → 404 "Asignación no encontrada"

FALLO 3: Asignación ya revocada
  → 404 "Asignación ya ha sido revocada"
```

**Límites:**
```
- NO elimina datos históricos
- NO elimina eventos pasados
- NO permite re-activar asignación revocada
```

### 3.3 Acción: LIST_TENANT_ASSIGNMENTS

**Entrada:**
```
actor_identity_id: string       // Quién ejecuta
tenant_id: string               // Qué tenant consultar
include_revoked: boolean        // Incluir históricas
```

**Precondiciones:**
```
1. actor tiene authority GLOBAL activa
2. tenant_id proporcionado
```

**Postcondiciones:**
```
1. Lista de asignaciones (activas o todas)
2. NO incluye datos operativos del tenant
```

**Condiciones de Fallo Duro:**
```
FALLO 1: actor NO tiene authority GLOBAL
  → 403 "No tiene authority GLOBAL"

FALLO 2: tenant_id no proporcionado
  → 400 "Debe especificar tenant_id"
```

**Límites:**
```
- Retorna SOLO registros de identity_tenant_assignments
- NO retorna visitas, QRs, evidencias del tenant
- NO retorna usuarios del tenant (solo asignaciones)
```

### 3.4 Acción: LIST_IDENTITY_ASSIGNMENTS

**Entrada:**
```
actor_identity_id: string       // Quién ejecuta
identity_id: string             // Qué identidad consultar
include_revoked: boolean        // Incluir históricas
```

**Precondiciones:**
```
1. actor tiene authority GLOBAL activa
2. identity_id proporcionado
```

**Postcondiciones:**
```
1. Lista de tenants donde identity tiene asignación
2. NO incluye datos operativos de ningún tenant
```

**Condiciones de Fallo Duro:**
```
FALLO 1: actor NO tiene authority GLOBAL
  → 403 "No tiene authority GLOBAL"

FALLO 2: identity_id no proporcionado
  → 400 "Debe especificar identity_id"
```

---

## 4. Registro de Eventos

### 4.1 Tipo de Evento: META_ASSIGN

```
Estructura en events_aup:

{
    event_id: "evt_...",
    identity_id: actor.usuario_id,          // Quién asigna
    session_token_hash: SHA256(JWT),
    tenant_id: NULL,                         // ← CRÍTICO: NO hay tenant activo
    
    entidad: "IDENTITY_TENANT_ASSIGNMENT",
    entidad_id: assignment_id,
    accion: "ASSIGN",
    resultado: "PERMITIDO" | "DENEGADO",
    
    motivo: "Asignación meta-operativa",
    metadata: {
        target_identity_id: string,
        target_tenant_id: string,
        assignment_type: string
    },
    
    timestamp: datetime,
    hash: SHA256(concatenacion_campos)
}
```

**Campos obligatorios para reconstrucción:**
```
OBLIGATORIO:
  - identity_id (quién asignó)
  - metadata.target_identity_id (a quién)
  - metadata.target_tenant_id (en qué tenant)
  - timestamp (cuándo)
  - resultado (éxito o fallo)

CRÍTICO:
  - tenant_id DEBE ser NULL (no hay contexto de tenant)
```

### 4.2 Tipo de Evento: META_REVOKE

```
Estructura en events_aup:

{
    event_id: "evt_...",
    identity_id: actor.usuario_id,          // Quién revoca
    session_token_hash: SHA256(JWT),
    tenant_id: NULL,                         // ← NO hay tenant activo
    
    entidad: "IDENTITY_TENANT_ASSIGNMENT",
    entidad_id: assignment_id,
    accion: "REVOKE",
    resultado: "PERMITIDO" | "DENEGADO",
    
    motivo: revocation_reason,
    metadata: {
        target_identity_id: string,
        target_tenant_id: string,
        revocation_reason: string
    },
    
    timestamp: datetime,
    hash: SHA256(concatenacion_campos)
}
```

### 4.3 Tipo de Evento: META_LIST

```
Estructura en events_aup:

{
    event_id: "evt_...",
    identity_id: actor.usuario_id,
    session_token_hash: SHA256(JWT),
    tenant_id: NULL,
    
    entidad: "IDENTITY_TENANT_ASSIGNMENT",
    entidad_id: "LIST_QUERY",
    accion: "LIST",
    resultado: "PERMITIDO" | "DENEGADO",
    
    motivo: "Consulta meta-operativa",
    metadata: {
        query_type: "BY_TENANT" | "BY_IDENTITY",
        filter_value: string,
        include_revoked: boolean,
        result_count: integer
    },
    
    timestamp: datetime,
    hash: SHA256(concatenacion_campos)
}
```

### 4.4 Reconstrucción de Auditoría

**Pregunta 1: ¿Quién asignó a la identidad X en el tenant Y?**
```sql
SELECT 
    e.identity_id as quien_asigno,
    u.nombre as nombre_asignador,
    e.timestamp as cuando,
    e.metadata->>'assignment_type' as tipo_asignacion
FROM events_aup e
JOIN usuarios u ON u.usuario_id = e.identity_id
WHERE e.entidad = 'IDENTITY_TENANT_ASSIGNMENT'
  AND e.accion = 'ASSIGN'
  AND e.metadata->>'target_identity_id' = 'X'
  AND e.metadata->>'target_tenant_id' = 'Y'
ORDER BY e.timestamp DESC
LIMIT 1;
```

**Pregunta 2: ¿Cuándo fue revocada la asignación Z y por qué?**
```sql
SELECT 
    e.identity_id as quien_revoco,
    e.timestamp as cuando,
    e.metadata->>'revocation_reason' as motivo
FROM events_aup e
WHERE e.entidad = 'IDENTITY_TENANT_ASSIGNMENT'
  AND e.accion = 'REVOKE'
  AND e.entidad_id = 'Z'
ORDER BY e.timestamp DESC
LIMIT 1;
```

**Pregunta 3: ¿Qué asignaciones ha realizado el actor A?**
```sql
SELECT 
    e.metadata->>'target_identity_id' as identidad_asignada,
    e.metadata->>'target_tenant_id' as tenant,
    e.accion,
    e.timestamp
FROM events_aup e
WHERE e.identity_id = 'A'
  AND e.entidad = 'IDENTITY_TENANT_ASSIGNMENT'
  AND e.accion IN ('ASSIGN', 'REVOKE')
ORDER BY e.timestamp DESC;
```

---

## 5. Pruebas Conceptuales de Correctitud

### 5.1 Casos Válidos (DEBEN pasar)

```
CASO 1: Asignación básica
DADO:
  - actor con authority GLOBAL activa
  - target_identity 'user_1' existe
  - tenant 'condo_a' existe
  - NO hay asignación activa previa
CUANDO:
  assign_identity_to_tenant('user_1', 'condo_a', 'REGULAR_ADMIN')
ENTONCES:
  - Registro creado en identity_tenant_assignments
  - revoked = false
  - Evento ASSIGN en events_aup con tenant_id = NULL
  - Retorna 201 Created

CASO 2: Revocación válida
DADO:
  - actor con authority GLOBAL activa
  - assignment 'assign_123' existe con revoked = false
CUANDO:
  revoke_identity_from_tenant('assign_123', 'Fin de contrato')
ENTONCES:
  - revoked = true
  - revoked_at poblado
  - revocation_reason = 'Fin de contrato'
  - Evento REVOKE en events_aup
  - Retorna 200 OK

CASO 3: Lista por tenant
DADO:
  - actor con authority GLOBAL activa
  - tenant 'condo_a' tiene 3 asignaciones activas
CUANDO:
  list_tenant_assignments('condo_a', include_revoked=false)
ENTONCES:
  - Retorna lista con 3 elementos
  - NO retorna visitas ni QRs del tenant
  - Evento LIST en events_aup
  - Retorna 200 OK

CASO 4: Lista por identity
DADO:
  - actor con authority GLOBAL activa
  - identity 'user_1' tiene asignaciones en 2 tenants
CUANDO:
  list_identity_assignments('user_1', include_revoked=false)
ENTONCES:
  - Retorna lista con 2 elementos
  - Incluye tenant_ids
  - NO incluye datos operativos de los tenants
  - Retorna 200 OK
```

### 5.2 Casos Inválidos (DEBEN fallar)

```
CASO 5: Sin authority GLOBAL
DADO:
  - actor con authority FIRST_TIER (no GLOBAL)
CUANDO:
  assign_identity_to_tenant('user_1', 'condo_a', 'REGULAR_ADMIN')
ENTONCES:
  - FAIL 403 "No tiene authority GLOBAL"
  - NO se crea registro
  - Evento ASSIGN con resultado=DENEGADO

CASO 6: Tenant inexistente
DADO:
  - actor con authority GLOBAL activa
  - tenant 'condo_inexistente' NO existe
CUANDO:
  assign_identity_to_tenant('user_1', 'condo_inexistente', 'REGULAR_ADMIN')
ENTONCES:
  - FAIL 400 "Tenant no existe"
  - NO se crea registro
  - Evento ASSIGN con resultado=DENEGADO

CASO 7: Asignación duplicada
DADO:
  - actor con authority GLOBAL activa
  - user_1 YA tiene asignación activa en condo_a
CUANDO:
  assign_identity_to_tenant('user_1', 'condo_a', 'REGULAR_ADMIN')
ENTONCES:
  - FAIL 409 "Ya existe asignación activa"
  - NO se crea nuevo registro
  - Evento ASSIGN con resultado=DENEGADO

CASO 8: Self-assignment con scope operativo
DADO:
  - actor 'super_admin_1' con authority GLOBAL activa
CUANDO:
  assign_identity_to_tenant('super_admin_1', 'condo_a', 'REGULAR_ADMIN')
ENTONCES:
  - FAIL 400 "GLOBAL authority no puede asignarse scope operativo"
  - NO se crea registro
  - Evento ASSIGN con resultado=DENEGADO

CASO 9: Revocar asignación ya revocada
DADO:
  - assignment 'assign_123' con revoked = true
CUANDO:
  revoke_identity_from_tenant('assign_123', 'Motivo cualquiera')
ENTONCES:
  - FAIL 404 "Asignación ya ha sido revocada"
  - NO se modifica registro
  - Evento REVOKE con resultado=DENEGADO

CASO 10: Lista sin filtros
DADO:
  - actor con authority GLOBAL activa
CUANDO:
  GET /meta/assignments (sin query params)
ENTONCES:
  - FAIL 400 "Debe especificar identity_id o tenant_id"
  - NO retorna datos
```

### 5.3 Casos Frontera

```
CASO 11: Asignación FIRST_TIER_ADMIN
DADO:
  - actor con authority GLOBAL activa
  - target_identity 'user_1' existe
  - tenant 'condo_a' existe
CUANDO:
  assign_identity_to_tenant('user_1', 'condo_a', 'FIRST_TIER_ADMIN')
ENTONCES:
  - Registro creado en identity_tenant_assignments
  - Se crea authority FIRST_TIER para user_1 sobre condo_a
  - user_1 puede ahora asignar scopes dentro de condo_a
  - Retorna 201 Created

CASO 12: Múltiples asignaciones (diferentes tenants)
DADO:
  - actor con authority GLOBAL activa
  - user_1 NO tiene asignaciones previas
CUANDO:
  assign_identity_to_tenant('user_1', 'condo_a', 'REGULAR_ADMIN')
  assign_identity_to_tenant('user_1', 'condo_b', 'REGULAR_ADMIN')
ENTONCES:
  - 2 registros creados independientes
  - user_1 puede operar en ambos tenants
  - Cada operación registra evento separado
  - Retorna 201 Created en ambos

CASO 13: Revocación y re-asignación
DADO:
  - user_1 tiene asignación activa en condo_a
CUANDO:
  revoke_identity_from_tenant('assign_123', 'Temporalmente suspendido')
  assign_identity_to_tenant('user_1', 'condo_a', 'REGULAR_ADMIN')
ENTONCES:
  - Primera asignación: revoked = true
  - Segunda asignación: nuevo registro, revoked = false
  - Ambos eventos auditables
  - user_1 recupera acceso con nuevo assignment_id
  - Retorna 200 + 201

CASO 14: Actor pierde authority durante operación
DADO:
  - actor con authority GLOBAL activa
  - En otra sesión: authority del actor es revocada
CUANDO:
  actor intenta assign_identity_to_tenant('user_1', 'condo_a', 'REGULAR_ADMIN')
ENTONCES:
  - Validación en tiempo real detecta authority revocada
  - FAIL 403 "No tiene authority GLOBAL"
  - NO se crea registro
  - Protección contra race conditions
```

### 5.4 Casos de Violación del Dominio (DEBEN romper)

```
VIOLACIÓN 1: Intentar ver datos operativos
INTENTO:
  GET /meta/tenants/condo_a/visitas
EXPECTATIVA:
  - 404 Not Found (endpoint NO existe)
  - NO implementar este endpoint

VIOLACIÓN 2: Bypass de tenant en asignación
INTENTO:
  assign_identity_to_tenant() sin validar que tenant existe
EXPECTATIVA:
  - FAIL 400 antes de crear registro
  - Validación obligatoria de FK

VIOLACIÓN 3: Usar rol en lugar de authority
INTENTO:
  if usuario.rol == 'MSP_ADMIN': permitir()
EXPECTATIVA:
  - Code review RECHAZA el cambio
  - DEBE validar authority GLOBAL, no rol

VIOLACIÓN 4: Permitir re-activar asignación revocada
INTENTO:
  UPDATE identity_tenant_assignments SET revoked = false
EXPECTATIVA:
  - Constraint o validación impide la operación
  - Revocación es inmutable

VIOLACIÓN 5: Operar con tenant_id activo en sesión
INTENTO:
  SET app.tenant_id = 'condo_a' antes de assign()
EXPECTATIVA:
  - NO usar middleware RequireTenant en rutas meta
  - tenant_id debe permanecer NULL en sesión
```

---

## 6. Checklist de Implementación Mínima

### 6.1 Modelo de Datos
```
□ Crear tabla identity_tenant_assignments
□ Definir claves primarias y foráneas
□ Crear índices (identity, tenant, active)
□ Crear constraint de unicidad (identity + tenant WHERE revoked = false)
□ Migración reversible (rollback definido)
```

### 6.2 Dominio Funcional
```
□ Función: validate_global_authority()
□ Función: assign_identity_to_tenant()
□ Función: revoke_identity_from_tenant()
□ Función: list_tenant_assignments()
□ Función: list_identity_assignments()
□ Validaciones obligatorias implementadas
□ Fallos duros sin try-catch suavizante
```

### 6.3 Eventos
```
□ Registrar evento META_ASSIGN
□ Registrar evento META_REVOKE
□ Registrar evento META_LIST
□ tenant_id = NULL en todos los eventos meta
□ metadata con campos obligatorios
□ Hash de integridad generado
```

### 6.4 API (mínimo)
```
□ POST /meta/assignments
□ DELETE /meta/assignments/{id}
□ GET /meta/assignments?identity_id=X
□ GET /meta/assignments?tenant_id=Y
□ Middleware RequireGlobalAuthority (NO RequireTenant)
□ Respuestas JSON con códigos HTTP correctos
```

### 6.5 Tests
```
□ 4 casos válidos implementados
□ 6 casos inválidos implementados
□ 4 casos frontera implementados
□ 5 casos de violación que rompen
```

---

## 7. Criterios de Aceptación Final

### 7.1 Arquitectura
```
✓ Dominio meta NO toca lógica operativa existente
✓ Dominio meta NO usa middleware de tenant
✓ Dominio meta NO bypassa RLS
✓ Tabla meta es independiente de tablas operativas
✓ Rutas meta están en /meta/* (segregadas)
```

### 7.2 Seguridad
```
✓ Solo authority GLOBAL puede ejecutar acciones meta
✓ Validaciones fallan explícitamente (no soft fail)
✓ Self-assignment con scope operativo bloqueado
✓ NO existe "modo especial" ni bypass
✓ Authority validada en cada request (no cacheada)
```

### 7.3 Trazabilidad
```
✓ Toda acción meta genera evento en events_aup
✓ tenant_id = NULL en eventos meta
✓ metadata contiene target_identity_id y target_tenant_id
✓ Eventos permiten reconstruir quién asignó qué a quién
✓ Eventos son inmutables (no se modifican)
```

### 7.4 Límites
```
✓ Dominio meta NO puede ver datos operativos
✓ Dominio meta NO puede operar dentro de tenants
✓ Solo 4 acciones implementadas (no hay más)
✓ NO hay vistas globales cross-tenant
✓ NO hay dashboards ni reporting
```

### 7.5 Correctitud
```
✓ 4 casos válidos pasan
✓ 6 casos inválidos fallan correctamente
✓ 4 casos frontera funcionan
✓ 5 violaciones rompen el sistema (como debe ser)
```

---

## 8. Declaración de Cierre

```
EL DOMINIO META-OPERATIVO v1.0 ESTÁ CERRADO.

Capacidades implementadas:
  - ASSIGN_IDENTITY_TO_TENANT
  - REVOKE_IDENTITY_FROM_TENANT
  - LIST_TENANT_ASSIGNMENTS
  - LIST_IDENTITY_ASSIGNMENTS

Capacidades NO implementadas ni planificadas:
  - Ver datos operativos
  - Operar dentro de tenants
  - Crear tenants
  - Modificar usuarios
  - Dashboards globales
  - Reportes cross-tenant
  - UI administrativa
  - Automatización
  - Heurística
  - IA

El dominio es SUFICIENTE para su propósito:
gestionar relaciones Identidad ↔ Tenant de forma auditable.

Cualquier solicitud de extensión debe:
1. Pasar por revisión arquitectónica
2. Justificar por qué v1.0 es insuficiente
3. Demostrar que no rompe separación de dominios
4. Obtener aprobación de seguridad

Por defecto: RECHAZAR extensiones.
```

---

## 9. Responsables de Implementación

```
Fase 1: Modelo de datos
  Responsable: DBA / Backend Senior
  Revisión: Arquitecto de seguridad
  
Fase 2: Dominio funcional
  Responsable: Backend Senior
  Revisión: Arquitecto de sistemas
  
Fase 3: Eventos y trazabilidad
  Responsable: Backend Senior
  Revisión: Responsable de compliance
  
Fase 4: Tests
  Responsable: QA / Backend
  Revisión: Arquitecto de sistemas
```

---

## 10. Restricciones No Negociables

```
1. tenant_id = NULL en eventos meta (OBLIGATORIO)
2. Solo authority GLOBAL puede ejecutar acciones meta (OBLIGATORIO)
3. Validaciones fallan duro (OBLIGATORIO)
4. NO usar rol para autorización (PROHIBIDO)
5. NO ver datos operativos desde meta (PROHIBIDO)
6. NO operar con tenant_id activo (PROHIBIDO)
7. NO agregar capacidades más allá de v1.0 (PROHIBIDO)
```

---

**Firmado:**  
Ingeniero Senior Backend  
Arquitecto de Cumplimiento

**Estado:** CONGELADO v1.0  
**Próxima revisión:** Solo si se demuestra insuficiencia funcional crítica

---

**FIN DEL DOCUMENTO**
