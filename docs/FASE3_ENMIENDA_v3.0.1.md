# ENMIENDA FASE 3 — v3.0.1

**Sistema:** MSP_AXS  
**Documento base:** FASE3_EVENT_SOURCING_MODELO.md (v3.0.0)  
**Fecha de enmienda:** 2026-01-01  
**Clasificación:** Corrección de Especificación

---

## RESUMEN DE CAMBIOS

| Sección | Cambio | Impacto |
|---------|--------|---------|
| 5.3 | Clarificación de unicidad vs integridad | Previene colisiones de hash |
| 5.1 | Nueva regla de orden garantizable | Elimina dependencia de monotonicidad |
| 4.4, 7.x | Uso de columna tenant_id como fuente primaria | Consultas correctas |

---

## 1. CAMBIO: UNICIDAD vs INTEGRIDAD DE EVENTOS

### 1.1 Problema

La especificación original indica:
- `hash_evento` es UNIQUE
- `hash_input_fields` no incluye `metadata`

**Riesgo:** Dos eventos distintos con mismos campos base en el mismo timestamp colisionan.

Ejemplo de colisión:
```
Evento A: identity_crear para user_001 en 2026-01-01T00:00:00Z
Evento B: identity_crear para user_001 en 2026-01-01T00:00:00Z (retry por timeout)
→ Mismo hash → INSERT falla → Evento perdido
```

### 1.2 Corrección

**NUEVA INVARIANTE HASH-001:**

| Concepto | Campo | Constraint | Propósito |
|----------|-------|------------|-----------|
| **Unicidad primaria** | `event_id` | PRIMARY KEY | Identificación única del evento |
| **Integridad de contenido** | `hash_evento` | UNIQUE | Detectar duplicados lógicos |

**NUEVA INVARIANTE HASH-002:**

El `hash_evento` DEBE incluir un componente de entropía para evitar colisiones:

```
hash_evento = SHA-256(
  event_id +           -- ← AÑADIDO: garantiza unicidad
  identity_id + 
  tenant_id + 
  entidad + 
  entidad_id + 
  accion + 
  resultado + 
  timestamp
)
```

**Justificación:**
- `event_id` es único por generación (UUID/random)
- Al incluirlo en el hash, el hash es único por definición
- `hash_evento` pasa de "detectar duplicados" a "verificar integridad del contenido"

### 1.3 Nueva Fórmula de Hash

```sql
-- ANTES (riesgo de colisión):
v_hash_input := COALESCE(p_identity_id, 'SYSTEM') || 
                COALESCE(p_tenant_id, 'GLOBAL') || 
                p_entidad || 
                p_entidad_id || 
                p_accion || 
                p_resultado ||
                v_timestamp::TEXT;

-- DESPUÉS (sin colisión):
v_hash_input := v_event_id ||                          -- ← AÑADIDO
                COALESCE(p_identity_id, 'SYSTEM') || 
                COALESCE(p_tenant_id, 'GLOBAL') || 
                p_entidad || 
                p_entidad_id || 
                p_accion || 
                p_resultado ||
                v_timestamp::TEXT;
```

### 1.4 Verificación de Integridad (Corregida)

```sql
SELECT event_id,
       hash_evento,
       encode(sha256(
         (event_id ||                                  -- ← AÑADIDO
          COALESCE(identity_id, 'SYSTEM') || 
          COALESCE(tenant_id, 'GLOBAL') || 
          entidad || 
          entidad_id || 
          accion || 
          resultado || 
          timestamp::TEXT)::bytea
       ), 'hex') AS hash_calculado,
       CASE 
         WHEN hash_evento = encode(sha256(
           (event_id || COALESCE(identity_id, 'SYSTEM') || 
            COALESCE(tenant_id, 'GLOBAL') || entidad || 
            entidad_id || accion || resultado || timestamp::TEXT)::bytea
         ), 'hex') 
         THEN 'VÁLIDO' 
         ELSE '⚠️ CORRUPTO' 
       END AS verificacion
FROM events_aup;
```

---

## 2. CAMBIO: REGLA DE ORDEN GARANTIZABLE

### 2.1 Problema

La especificación original indica:
> "event_id debe ser único y monótono creciente dentro de una sesión"

**Riesgo:** `event_id` se genera con `gen_random_bytes(16)` → NO es monótono.

### 2.2 Corrección

**ELIMINAR INVARIANTE ORDEN-003 (original):**
```
❌ event_id debe ser único y monótono creciente dentro de una sesión
```

**NUEVA INVARIANTE ORDEN-003:**
```
event_id es único globalmente pero NO garantiza orden.
El orden se determina EXCLUSIVAMENTE por (timestamp, event_id).
event_id actúa como desempate lexicográfico, no como indicador temporal.
```

### 2.3 Reglas de Orden (Actualizadas)

| Regla | Descripción |
|-------|-------------|
| **ORDEN-001** | Eventos se ordenan primariamente por `timestamp` ASC |
| **ORDEN-002** | Si `timestamp` es igual, ordenar por `event_id` ASC (lexicográfico) |
| **ORDEN-003** | `event_id` NO implica orden temporal, solo unicidad |
| **ORDEN-004** | Eventos de trigger (`DB_TRIGGER_AUDIT`) comparten timestamp de transacción |
| **ORDEN-005** | Para eventos en misma transacción, el orden de inserción NO está garantizado |

### 2.4 Implicación para Reconstrucción

Cuando múltiples eventos tienen mismo timestamp:
- El orden entre ellos es **determinista** (lexicográfico por event_id)
- El orden entre ellos es **arbitrario** respecto a causalidad real
- **Aceptable** porque eventos en misma transacción son atómicos

---

## 3. CAMBIO: USO DE COLUMNA tenant_id

### 3.1 Problema

Las consultas de reconstrucción filtran por:
```sql
metadata->>'tenant_id' = 'tenant_xxx'
```

**Riesgos:**
- `metadata` es JSONB sin schema → puede no existir el campo
- Rendimiento inferior (sin índice en campo JSON)
- Inconsistencia si `events_aup.tenant_id` difiere de `metadata->>'tenant_id'`

### 3.2 Corrección

**NUEVA INVARIANTE TENANT-001:**

```
El campo events_aup.tenant_id es la FUENTE PRIMARIA del contexto de tenant.
metadata.tenant_id solo se usa para contexto extendido (ej: tenant origen en operaciones cross-tenant).
```

**NUEVA INVARIANTE TENANT-002:**

```
Para eventos con tenant conocido:
  - events_aup.tenant_id DEBE estar poblado
  - metadata.tenant_id es OPCIONAL (solo si difiere o aporta contexto adicional)

Para eventos globales (sin tenant):
  - events_aup.tenant_id = 'GLOBAL'
  - metadata puede especificar tenants afectados si aplica
```

### 3.3 Consultas Corregidas

#### 3.3.1 Reconstrucción de Tenant (Corregida)

**ANTES:**
```sql
-- Listar scopes asociados
SELECT * FROM events_aup 
WHERE entidad = 'scope' 
  AND metadata->>'tenant_id' = 'tenant_demo_0000000000000001'  -- ❌
ORDER BY timestamp ASC;

-- Listar authorities asociadas
SELECT * FROM events_aup 
WHERE entidad = 'authority' 
  AND (metadata->>'tenant_id' = 'tenant_demo_0000000000000001'  -- ❌
       OR metadata->>'tipo' = 'global')
ORDER BY timestamp ASC;
```

**DESPUÉS:**
```sql
-- Listar scopes asociados (usa columna tenant_id)
SELECT * FROM events_aup 
WHERE entidad = 'scope' 
  AND tenant_id = 'tenant_demo_0000000000000001'               -- ✅
ORDER BY timestamp ASC, event_id ASC;

-- Listar authorities asociadas (usa columna tenant_id + metadata para tipo)
SELECT * FROM events_aup 
WHERE entidad = 'authority' 
  AND (tenant_id = 'tenant_demo_0000000000000001'              -- ✅
       OR (tenant_id = 'GLOBAL' AND metadata->>'tipo' = 'global'))
ORDER BY timestamp ASC, event_id ASC;
```

#### 3.3.2 Query 7.3 Eventos Críticos (Corregida)

**ANTES:**
```sql
SELECT 
  timestamp,
  entidad,
  entidad_id,
  accion,
  identity_id,
  motivo
FROM events_aup
WHERE timestamp BETWEEN '2026-01-01' AND '2026-06-30'
  ...
```

**DESPUÉS:**
```sql
SELECT 
  timestamp,
  tenant_id,                                                   -- ✅ AÑADIDO
  entidad,
  entidad_id,
  accion,
  identity_id,
  motivo
FROM events_aup
WHERE timestamp BETWEEN '2026-01-01' AND '2026-06-30'
  AND (tenant_id = 'tenant_especifico' OR tenant_id = 'GLOBAL') -- ✅ Filtro opcional
  AND resultado IN ('exito', 'alerta')
  AND accion IN (
    'authority_crear', 'authority_revocar', 'authority_reactivar',
    'scope_crear', 'scope_revocar', 'scope_modificar', 'scope_reactivar',
    'policy_crear', 'policy_revocar'
  )
ORDER BY timestamp ASC, event_id ASC;                          -- ✅ Orden completo
```

#### 3.3.3 Historial de Entidad por Tenant (Nueva)

```sql
-- Todos los eventos de un tenant específico
SELECT 
  event_id,
  timestamp,
  entidad,
  entidad_id,
  accion,
  resultado,
  identity_id,
  motivo
FROM events_aup
WHERE tenant_id = 'tenant_demo_0000000000000001'
ORDER BY timestamp ASC, event_id ASC;
```

---

## 4. NUEVAS INVARIANTES (CONSOLIDADO)

### 4.1 Invariantes de Hash

| ID | Invariante |
|----|------------|
| HASH-001 | `event_id` es unicidad primaria (PK). `hash_evento` es integridad de contenido (UNIQUE). |
| HASH-002 | `hash_evento` DEBE incluir `event_id` en su cálculo para evitar colisiones. |
| HASH-003 | Fórmula: `SHA-256(event_id + identity_id + tenant_id + entidad + entidad_id + accion + resultado + timestamp)` |

### 4.2 Invariantes de Orden

| ID | Invariante |
|----|------------|
| ORDEN-001 | Orden primario: `timestamp` ASC |
| ORDEN-002 | Desempate: `event_id` ASC (lexicográfico) |
| ORDEN-003 | `event_id` NO implica orden temporal |
| ORDEN-004 | Eventos de trigger comparten timestamp de transacción |
| ORDEN-005 | Orden entre eventos de misma transacción es determinista pero arbitrario |

### 4.3 Invariantes de Tenant

| ID | Invariante |
|----|------------|
| TENANT-001 | `events_aup.tenant_id` es fuente primaria de contexto de tenant |
| TENANT-002 | Eventos globales usan `tenant_id = 'GLOBAL'` |
| TENANT-003 | `metadata.tenant_id` solo para contexto extendido, no para filtrado |
| TENANT-004 | Consultas DEBEN filtrar por columna `tenant_id`, no por `metadata->>'tenant_id'` |

---

## 5. ACTUALIZACIÓN DE FUNCIÓN fn_generate_audit_event

```sql
-- Fragmento corregido de fn_generate_audit_event

-- Generar event_id único PRIMERO
v_event_id := 'evt_audit_' || encode(gen_random_bytes(16), 'hex');

-- Generar hash de inmutabilidad INCLUYENDO event_id
v_hash_input := v_event_id ||                              -- ← CRÍTICO
                COALESCE(p_identity_id, 'SYSTEM') || 
                COALESCE(p_tenant_id, 'GLOBAL') || 
                p_entidad || 
                p_entidad_id || 
                p_accion || 
                p_resultado ||
                v_timestamp::TEXT;
v_hash_evento := encode(sha256(v_hash_input::bytea), 'hex');
```

---

## 6. ACTUALIZACIÓN DE METADATA DE GÉNESIS

```json
{
  "genesis": true,
  "version": "1.0.0",
  "bootstrap_timestamp_utc": "2026-01-01T00:00:00Z",
  
  "hash_algorithm": "SHA-256",
  "hash_input_fields": [
    "event_id",              // ← AÑADIDO (primera posición)
    "identity_id", 
    "tenant_id",
    "entidad",
    "entidad_id",
    "accion",
    "resultado",
    "timestamp"
  ],
  
  "entities_created": { ... }
}
```

---

## 7. CHECKLIST DE IMPLEMENTACIÓN (ENMIENDA)

- [ ] Actualizar `fn_generate_audit_event` para incluir `event_id` en hash
- [ ] Actualizar evento de génesis con `hash_input_fields` corregido
- [ ] Revisar consultas existentes: cambiar `metadata->>'tenant_id'` por `tenant_id`
- [ ] Verificar que triggers usen `tenant_id` columna, no metadata
- [ ] Documentar valor `'GLOBAL'` para eventos sin tenant
- [ ] Actualizar tests de verificación de integridad

---

## COMPATIBILIDAD

| Aspecto | Estado |
|---------|--------|
| Eventos existentes | ⚠️ Hash recalculado será diferente. Marcar como "pre-enmienda" en auditoría. |
| Nuevos eventos | ✅ Siguen nueva fórmula |
| Consultas existentes | ⚠️ Actualizar para usar `tenant_id` columna |
| Estructura de events_aup | ✅ Sin cambios |

---

**FIN DE ENMIENDA v3.0.1**
