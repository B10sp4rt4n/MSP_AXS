# FASE 3: MODELO DE EVENT SOURCING FUERTE

**Sistema:** MSP_AXS  
**Versión:** 3.0.0  
**Fecha:** 2026-01-01  
**Clasificación:** Especificación de Auditoría y Reconstrucción

---

## OBJETIVO

Permitir que `events_aup` sea la **fuente única de verdad histórica** para:
- Reconstruir estado de cualquier entidad en cualquier punto temporal
- Responder preguntas de auditoría forense
- Defender decisiones del sistema ante reguladores

---

## 1. CATÁLOGO DE EVENTOS CANÓNICOS

### 1.1 Convención de Nomenclatura

```
{entidad}_{accion}
```

| Campo | Valores permitidos |
|-------|-------------------|
| `entidad` | `sistema`, `identity`, `tenant`, `scope`, `authority`, `policy`, `delegation`, `session` |
| `accion` | `crear`, `revocar`, `suspender`, `reactivar`, `modificar`, `eliminar`, `denegar`, `expirar` |

### 1.2 Eventos de SISTEMA

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `sistema_bootstrap` | sistema | crear | Inicialización del sistema | **CRÍTICO** |
| `sistema_migracion` | sistema | modificar | Ejecución de migración de schema | DERIVADO |

### 1.3 Eventos de IDENTITY

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `identity_crear` | identity | crear | Registro de nuevo usuario | **CRÍTICO** |
| `identity_modificar` | identity | modificar | Cambio de datos no críticos (nombre, email) | DERIVADO |
| `identity_suspender` | identity | suspender | Suspensión administrativa | **CRÍTICO** |
| `identity_reactivar` | identity | reactivar | Reactivación tras suspensión | **CRÍTICO** |
| `identity_eliminar` | identity | eliminar | Eliminación física (raro) | **CRÍTICO** |

### 1.4 Eventos de TENANT

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `tenant_crear` | tenant | crear | Creación de condominio | **CRÍTICO** |
| `tenant_modificar` | tenant | modificar | Cambio de nombre u otros datos | DERIVADO |
| `tenant_suspender` | tenant | suspender | Suspensión de tenant | **CRÍTICO** |
| `tenant_reactivar` | tenant | reactivar | Reactivación de tenant | **CRÍTICO** |

### 1.5 Eventos de SCOPE

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `scope_crear` | scope | crear | Asignación de alcance a identidad | **CRÍTICO** |
| `scope_modificar` | scope | modificar | Cambio de access_level | **CRÍTICO** |
| `scope_suspender` | scope | suspender | Suspensión temporal | **CRÍTICO** |
| `scope_revocar` | scope | revocar | Revocación permanente | **CRÍTICO** |
| `scope_reactivar` | scope | reactivar | Reactivación (con flag autorizado) | **CRÍTICO** |
| `scope_expirar` | scope | expirar | Expiración por vigencia | DERIVADO |

### 1.6 Eventos de AUTHORITY

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `authority_crear` | authority | crear | Otorgamiento de autoridad | **CRÍTICO** |
| `authority_suspender` | authority | suspender | Suspensión temporal | **CRÍTICO** |
| `authority_revocar` | authority | revocar | Revocación permanente | **CRÍTICO** |
| `authority_reactivar` | authority | reactivar | Reactivación (con flag autorizado) | **CRÍTICO** |
| `authority_eliminar` | authority | eliminar | Eliminación física (detectada por trigger) | **CRÍTICO** |

### 1.7 Eventos de POLICY

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `policy_crear` | policy | crear | Definición de nueva política | **CRÍTICO** |
| `policy_modificar` | policy | modificar | Cambio de límites o vigencia | **CRÍTICO** |
| `policy_suspender` | policy | suspender | Suspensión de política | **CRÍTICO** |
| `policy_revocar` | policy | revocar | Revocación permanente | **CRÍTICO** |
| `policy_expirar` | policy | expirar | Expiración por valida_hasta | DERIVADO |

### 1.8 Eventos de DELEGATION

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `delegation_crear` | delegation | crear | Delegación de permisos | **CRÍTICO** |
| `delegation_revocar` | delegation | revocar | Revocación de delegación | **CRÍTICO** |
| `delegation_expirar` | delegation | expirar | Expiración por valida_hasta | DERIVADO |

### 1.9 Eventos de SESSION

| Nombre Canónico | Entidad | Acción | Cuándo se emite | Tipo |
|-----------------|---------|--------|-----------------|------|
| `session_crear` | session | crear | Login exitoso | DERIVADO |
| `session_denegar` | session | denegar | Login fallido | **CRÍTICO** |
| `session_revocar` | session | revocar | Logout o invalidación | DERIVADO |

### 1.10 Resumen de Eventos

| Categoría | Eventos CRÍTICOS | Eventos DERIVADOS | Total |
|-----------|------------------|-------------------|-------|
| Sistema | 1 | 1 | 2 |
| Identity | 4 | 1 | 5 |
| Tenant | 3 | 1 | 4 |
| Scope | 5 | 1 | 6 |
| Authority | 5 | 0 | 5 |
| Policy | 4 | 1 | 5 |
| Delegation | 2 | 1 | 3 |
| Session | 1 | 2 | 3 |
| **TOTAL** | **25** | **8** | **33** |

---

## 2. EVENTO DE GÉNESIS FORMAL

### 2.1 Definición

El evento `sistema_bootstrap` es el **primer evento** del sistema y debe contener toda la información necesaria para reconstruir el estado inicial.

### 2.2 Estructura Obligatoria

| Campo | Valor | Obligatorio |
|-------|-------|-------------|
| `event_id` | `evt_genesis_000000000001` | ✅ |
| `identity_id` | ID del usuario root | ✅ |
| `session_hash` | `GENESIS_BOOTSTRAP` | ✅ (valor especial) |
| `scope_id` | `NULL` | ✅ (no aplica en génesis) |
| `tenant_id` | ID del tenant inicial | ✅ |
| `entidad` | `sistema` | ✅ |
| `entidad_id` | `sistema_genesis` | ✅ |
| `accion` | `bootstrap` | ✅ |
| `resultado` | `exito` | ✅ |
| `motivo` | `Inicialización del sistema MSP_AXS` | ✅ |
| `timestamp` | UTC del momento de bootstrap | ✅ |
| `hash_evento` | SHA-256 calculado | ✅ |
| `metadata` | Objeto JSON estructurado (ver 2.3) | ✅ |

### 2.3 Estructura de metadata (Obligatoria)

```json
{
  "genesis": true,
  "version": "1.0.0",
  "bootstrap_timestamp_utc": "2026-01-01T00:00:00Z",
  
  "entities_created": {
    "msp": {
      "msp_id": "msp_root_00000000000000000001",
      "nombre": "MSP_ROOT_PLATFORM",
      "order": 1
    },
    "tenant": {
      "condominio_id": "tenant_demo_0000000000000001",
      "msp_id": "msp_root_00000000000000000001",
      "nombre": "Demo Sandbox",
      "order": 2
    },
    "identity": {
      "usuario_id": "user_root_000000000000000001",
      "email": "root@mspaxs.platform",
      "identity_label": "MSP_ADMIN",
      "order": 3
    },
    "scope": {
      "usuario_id": "user_root_000000000000000001",
      "tenant_id": "tenant_demo_0000000000000001",
      "access_level": "msp_admin",
      "estado": "activo",
      "order": 4
    },
    "authority": {
      "authority_id": "auth_global_root_0000000001",
      "identity_id": "user_root_000000000000000001",
      "tipo": "global",
      "tenant_id": null,
      "estado": "activo",
      "order": 5
    },
    "policies": [
      {
        "policy_id": "policy_global_crear_tenant",
        "nombre": "Política Global: Crear Tenants",
        "ambito": "global",
        "accion_objetivo": "crear_tenant",
        "order": 6
      },
      {
        "policy_id": "policy_tenant_demo_qr_vigencia",
        "nombre": "Política Demo: Vigencia QR",
        "ambito": "tenant",
        "target_tenant_id": "tenant_demo_0000000000000001",
        "accion_objetivo": "generar_qr",
        "order": 7
      }
    ]
  },
  
  "creation_order": [
    "msp",
    "tenant", 
    "identity",
    "scope",
    "authority",
    "policies"
  ],
  
  "hash_algorithm": "SHA-256",
  "hash_input_fields": [
    "event_id",
    "identity_id", 
    "tenant_id",
    "entidad",
    "entidad_id",
    "accion",
    "resultado",
    "timestamp"
  ]
}
```

### 2.4 Orden de Creación Implícito

| Orden | Entidad | Dependencias |
|-------|---------|--------------|
| 1 | MSP | Ninguna |
| 2 | Tenant | MSP |
| 3 | Identity | MSP (opcional), Tenant (opcional) |
| 4 | Scope | Identity, Tenant |
| 5 | Authority | Identity, Tenant (si first_tier) |
| 6+ | Policies | Tenant (si ámbito tenant) |

### 2.5 Validación de Génesis

Para verificar un evento de génesis válido:

1. `event_id` empieza con `evt_genesis_`
2. `session_hash` = `GENESIS_BOOTSTRAP`
3. `entidad` = `sistema`
4. `accion` = `bootstrap`
5. `metadata.genesis` = `true`
6. `metadata.entities_created` contiene al menos: msp, tenant, identity, authority
7. `metadata.creation_order` es array no vacío

---

## 3. REGLAS DE EMISIÓN DE EVENTOS

### 3.1 Operaciones que SIEMPRE generan evento

| Operación | Evento | Emisor |
|-----------|--------|--------|
| Crear usuario | `identity_crear` | Aplicación |
| Crear tenant | `tenant_crear` | Aplicación |
| Crear scope | `scope_crear` | Trigger DB |
| Modificar scope.access_level | `scope_modificar` | Trigger DB |
| Modificar scope.estado | `scope_revocar` / `scope_suspender` / `scope_reactivar` | Trigger DB |
| Crear authority | `authority_crear` | Trigger DB |
| Modificar authority.estado | `authority_revocar` / `authority_suspender` / `authority_reactivar` | Trigger DB |
| Crear policy | `policy_crear` | Aplicación |
| Modificar policy.estado | `policy_revocar` / `policy_suspender` | Aplicación |
| Crear delegation | `delegation_crear` | Aplicación |
| Login exitoso | `session_crear` | Aplicación |
| Login fallido | `session_denegar` | Aplicación |
| Bootstrap del sistema | `sistema_bootstrap` | Script de inicialización |

### 3.2 Operaciones que NO generan evento

| Operación | Razón |
|-----------|-------|
| Consulta SELECT | No modifica estado |
| Cambio de nombre de usuario | No afecta poder ni alcance (DERIVADO opcional) |
| Cambio de email | No afecta poder ni alcance (DERIVADO opcional) |
| Actualización de metadata no crítica | No afecta estado de negocio |
| Refresh de token JWT | No es cambio de sesión |

### 3.3 Eventos DERIVADOS

Los eventos DERIVADOS son opcionales pero recomendados. Se marcan con:

```json
{
  "metadata": {
    "derived": true,
    "derived_from": "event_id_del_evento_padre",
    "derived_reason": "Expiración automática por valida_hasta"
  }
}
```

| Evento | Derivado de | Condición |
|--------|-------------|-----------|
| `scope_expirar` | `scope_crear` | `now() > scope.valida_hasta` |
| `policy_expirar` | `policy_crear` | `now() > policy.valida_hasta` |
| `delegation_expirar` | `delegation_crear` | `now() > delegation.valida_hasta` |
| `sistema_migracion` | `sistema_bootstrap` | Ejecución de script de migración |

### 3.4 Distinción de Origen de Evento

| `session_hash` | Origen | Descripción |
|----------------|--------|-------------|
| `GENESIS_BOOTSTRAP` | Sistema | Evento de inicialización |
| `DB_TRIGGER_AUDIT` | Trigger DB | Evento generado automáticamente por trigger |
| `SYSTEM_BATCH_JOB` | Sistema | Evento de job programado (expiraciones) |
| `[hash SHA-256 de JWT]` | Aplicación | Evento generado por operación de usuario |

---

## 4. RECONSTRUCCIÓN DE ESTADO (CONCEPTUAL)

### 4.1 Algoritmo General

```
FUNCIÓN reconstruir_estado(entidad_tipo, entidad_id, fecha_corte):
    
    1. FILTRAR eventos WHERE:
       - entidad = entidad_tipo
       - entidad_id = entidad_id
       - timestamp <= fecha_corte
    
    2. ORDENAR por timestamp ASC, event_id ASC
    
    3. INICIALIZAR estado = {}
    
    4. PARA CADA evento en orden:
       APLICAR_TRANSICION(estado, evento)
    
    5. RETORNAR estado
```

### 4.2 Reconstrucción de AUTHORITY

```
ENTRADA: authority_id = "auth_global_root_0000000001", fecha = "2026-06-15"

PASO 1: Buscar eventos
  SELECT * FROM events_aup 
  WHERE entidad = 'authority' 
    AND entidad_id = 'auth_global_root_0000000001'
    AND timestamp <= '2026-06-15'
  ORDER BY timestamp ASC, event_id ASC;

PASO 2: Procesar eventos en orden

  Evento 1: authority_crear (2026-01-01)
    → estado = {
        authority_id: "auth_global_root_0000000001",
        identity_id: "user_root_000000000000000001",
        tipo: "global",
        estado: "activo",
        created_at: "2026-01-01"
      }

  Evento 2: authority_suspender (2026-03-15)
    → estado.estado = "suspendido"
    → estado.suspended_at = "2026-03-15"

  Evento 3: authority_reactivar (2026-04-01)
    → estado.estado = "activo"
    → estado.reactivated_at = "2026-04-01"

PASO 3: Retornar estado final al 2026-06-15
  → {
      authority_id: "auth_global_root_0000000001",
      identity_id: "user_root_000000000000000001",
      tipo: "global",
      estado: "activo",
      created_at: "2026-01-01",
      suspended_at: "2026-03-15",
      reactivated_at: "2026-04-01"
    }
```

### 4.3 Reconstrucción de SCOPE

```
ENTRADA: scope_id = "42", fecha = "2026-06-15"

PASO 1: Buscar eventos
  SELECT * FROM events_aup 
  WHERE entidad = 'scope' 
    AND entidad_id = '42'
    AND timestamp <= '2026-06-15'
  ORDER BY timestamp ASC, event_id ASC;

PASO 2: Procesar eventos en orden

  Evento 1: scope_crear (2026-01-15)
    → estado = {
        scope_id: 42,
        usuario_id: "user_xxx",
        tenant_id: "tenant_demo",
        access_level: "residente",
        estado: "activo"
      }

  Evento 2: scope_modificar (2026-02-20)
    → estado.access_level = "guardia"  (escalamiento)

  Evento 3: scope_revocar (2026-05-10)
    → estado.estado = "revocado"
    → estado.revoked_at = "2026-05-10"

PASO 3: Retornar estado final al 2026-06-15
  → {
      scope_id: 42,
      usuario_id: "user_xxx",
      tenant_id: "tenant_demo",
      access_level: "guardia",
      estado: "revocado",
      revoked_at: "2026-05-10"
    }

RESPUESTA A AUDITOR:
  "El usuario user_xxx tenía scope GUARDIA en tenant_demo hasta 2026-05-10,
   cuando fue revocado."
```

### 4.4 Reconstrucción de TENANT

```
ENTRADA: tenant_id = "tenant_demo_0000000000000001"

PASO 1: Buscar evento de génesis O tenant_crear
  → Si tenant_id aparece en metadata.entities_created.tenant del génesis:
      Fue creado en bootstrap
  → Si existe evento tenant_crear:
      Fue creado post-bootstrap

PASO 2: Buscar eventos de modificación
  SELECT * FROM events_aup 
  WHERE entidad = 'tenant' 
    AND entidad_id = 'tenant_demo_0000000000000001'
  ORDER BY timestamp ASC;

PASO 3: Listar scopes asociados
  SELECT * FROM events_aup 
  WHERE entidad = 'scope' 
    AND metadata->>'tenant_id' = 'tenant_demo_0000000000000001'
  ORDER BY timestamp ASC;

PASO 4: Listar authorities asociadas
  SELECT * FROM events_aup 
  WHERE entidad = 'authority' 
    AND (metadata->>'tenant_id' = 'tenant_demo_0000000000000001'
         OR metadata->>'tipo' = 'global')
  ORDER BY timestamp ASC;

PASO 5: Construir vista completa del tenant
```

### 4.5 Consultas de Auditoría Frecuentes

| Pregunta | Query Conceptual |
|----------|------------------|
| ¿Quién tuvo autoridad X en fecha Y? | Filtrar eventos de authority X hasta fecha Y, reconstruir estado |
| ¿Por qué se revocó este scope? | Buscar evento `scope_revocar` con entidad_id, leer `motivo` y `metadata` |
| ¿Qué permisos tenía usuario U en fecha F? | Reconstruir todos los scopes de U activos en F |
| ¿Cuándo se otorgó esta autoridad? | Buscar evento `authority_crear` con entidad_id |
| ¿Quién modificó este scope? | Buscar evento `scope_modificar`, leer `identity_id` del evento |

---

## 5. INMUTABILIDAD Y ORDEN

### 5.1 Reglas de Orden Temporal

| Regla | Descripción |
|-------|-------------|
| **ORDEN-001** | Eventos se ordenan primariamente por `timestamp` ASC |
| **ORDEN-002** | Si `timestamp` es igual, ordenar por `event_id` ASC |
| **ORDEN-003** | `event_id` debe ser único y monótono creciente dentro de una sesión |
| **ORDEN-004** | Eventos de trigger (`DB_TRIGGER_AUDIT`) heredan timestamp de la transacción |

### 5.2 Manejo de Timestamps Iguales

Cuando múltiples eventos tienen el mismo timestamp (misma transacción):

```
ORDEN DE PROCESAMIENTO:
1. Ordenar por event_id (lexicográfico)
2. El event_id contiene suficiente entropía para desambiguar
3. Ejemplo:
   - evt_audit_a1b2c3d4 (primero)
   - evt_audit_a1b2c3d5 (segundo)
```

**Regla de negocio:**
- Eventos de trigger se procesan en orden de inserción
- La transacción garantiza atomicidad

### 5.3 Relación timestamp ↔ hash_evento

| Campo | Propósito | Inmutabilidad |
|-------|-----------|---------------|
| `timestamp` | Orden temporal | ✅ No modificable (trigger protege) |
| `hash_evento` | Integridad del contenido | ✅ No modificable (trigger protege) |

**Fórmula de hash:**
```
hash_evento = SHA-256(
  identity_id + 
  tenant_id + 
  entidad + 
  entidad_id + 
  accion + 
  resultado + 
  timestamp
)
```

**Verificación de integridad:**
```sql
SELECT event_id,
       hash_evento,
       encode(sha256(
         (COALESCE(identity_id, '') || 
          COALESCE(tenant_id, '') || 
          entidad || 
          entidad_id || 
          accion || 
          resultado || 
          timestamp::TEXT)::bytea
       ), 'hex') AS hash_calculado,
       CASE 
         WHEN hash_evento = encode(sha256(...), 'hex') 
         THEN 'VÁLIDO' 
         ELSE '⚠️ CORRUPTO' 
       END AS verificacion
FROM events_aup;
```

### 5.4 Prevención de Inconsistencias

| Inconsistencia | Prevención |
|----------------|------------|
| Evento insertado fuera de orden | `timestamp` usa `now()` de transacción (no editable) |
| Evento con timestamp futuro | Validación en aplicación (no en DB por diseño) |
| Hash no coincide con contenido | Trigger `trg_protect_events_immutability` bloquea UPDATE |
| Evento duplicado | `hash_evento` es UNIQUE |
| Evento eliminado | Trigger bloquea DELETE |

### 5.5 Cadena de Integridad (Opcional Avanzado)

Para máxima seguridad, se puede implementar encadenamiento:

```json
{
  "metadata": {
    "previous_event_hash": "hash_del_evento_anterior",
    "chain_position": 1234
  }
}
```

**Estado actual:** NO implementado. Marcado como mejora futura.

---

## 6. RIESGOS RESIDUALES

### 6.1 Riesgos ALTOS

| Riesgo | Descripción | Mitigación |
|--------|-------------|------------|
| **Corrupción de events_aup** | Acceso superuser puede manipular | Backups + checksum externo |
| **Pérdida de eventos por bug** | Aplicación no emite evento crítico | Tests de integración + alertas |
| **Timestamps inconsistentes** | Servidor con reloj desincronizado | NTP obligatorio + monitoreo |

### 6.2 Riesgos MEDIOS

| Riesgo | Descripción | Mitigación |
|--------|-------------|------------|
| **Eventos sin metadata suficiente** | No se puede reconstruir contexto | Validación de schema en app |
| **Eventos derivados no emitidos** | Expiraciones no detectadas | Job programado de reconciliación |
| **Hash no verificado en lectura** | Corrupción no detectada | Query de verificación periódica |

### 6.3 Riesgos BAJOS

| Riesgo | Descripción | Mitigación |
|--------|-------------|------------|
| **Orden de eventos en misma transacción** | Ambigüedad en microsegundos | event_id desambigua |
| **Eventos de sistema sin identity_id real** | `SYSTEM_TRIGGER` no es usuario | Aceptable por diseño |

### 6.4 Responsabilidades de la Aplicación

| Responsabilidad | NO resuelta por Event Sourcing |
|-----------------|-------------------------------|
| Emitir eventos completos | App debe incluir metadata adecuada |
| Validar schema de metadata | App debe validar antes de INSERT |
| Detectar expiraciones | App debe ejecutar job de verificación |
| Verificar integridad periódica | App debe correr queries de checksum |
| Backup de events_aup | Infraestructura externa |

---

## 7. CONSULTAS DE REFERENCIA PARA AUDITORÍA

### 7.1 Historial completo de una entidad

```sql
SELECT 
  event_id,
  timestamp,
  accion,
  resultado,
  motivo,
  metadata
FROM events_aup
WHERE entidad = 'authority' 
  AND entidad_id = 'auth_global_root_0000000001'
ORDER BY timestamp ASC, event_id ASC;
```

### 7.2 Estado de todas las autoridades en fecha específica

```sql
WITH eventos_hasta_fecha AS (
  SELECT 
    entidad_id,
    accion,
    metadata,
    ROW_NUMBER() OVER (PARTITION BY entidad_id ORDER BY timestamp DESC, event_id DESC) as rn
  FROM events_aup
  WHERE entidad = 'authority'
    AND timestamp <= '2026-06-15'
)
SELECT 
  entidad_id AS authority_id,
  accion AS ultima_accion,
  CASE 
    WHEN accion IN ('authority_crear', 'authority_reactivar') THEN 'activo'
    WHEN accion = 'authority_suspender' THEN 'suspendido'
    WHEN accion IN ('authority_revocar', 'authority_eliminar') THEN 'revocado'
    ELSE 'desconocido'
  END AS estado_reconstruido
FROM eventos_hasta_fecha
WHERE rn = 1;
```

### 7.3 Eventos críticos en rango de fechas

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
  AND resultado IN ('exito', 'alerta')
  AND accion IN (
    'authority_crear', 'authority_revocar', 'authority_reactivar',
    'scope_crear', 'scope_revocar', 'scope_modificar', 'scope_reactivar',
    'policy_crear', 'policy_revocar'
  )
ORDER BY timestamp ASC;
```

### 7.4 Verificación de integridad

```sql
SELECT 
  COUNT(*) FILTER (WHERE session_hash = 'DB_TRIGGER_AUDIT') AS eventos_trigger,
  COUNT(*) FILTER (WHERE session_hash = 'GENESIS_BOOTSTRAP') AS eventos_genesis,
  COUNT(*) FILTER (WHERE session_hash NOT IN ('DB_TRIGGER_AUDIT', 'GENESIS_BOOTSTRAP', 'SYSTEM_BATCH_JOB')) AS eventos_aplicacion,
  COUNT(*) AS total_eventos,
  MIN(timestamp) AS primer_evento,
  MAX(timestamp) AS ultimo_evento
FROM events_aup;
```

---

## APÉNDICE: CHECKLIST DE AUDITORÍA

Para responder preguntas de auditor:

| Pregunta | Cómo responder |
|----------|----------------|
| "¿Quién tuvo poder X en fecha Y?" | Query 7.2 + filtrar por authority_id |
| "¿Por qué se otorgó este acceso?" | Buscar evento `scope_crear` o `authority_crear`, leer `motivo` |
| "¿Qué evento originó este estado?" | Buscar primer evento con `entidad_id` correspondiente |
| "¿Ha sido manipulado este registro?" | Query de verificación de hash (5.3) |
| "¿Cuándo se inicializó el sistema?" | Buscar evento con `session_hash = 'GENESIS_BOOTSTRAP'` |
| "¿Qué cambios hubo en este período?" | Query 7.3 con rango de fechas |

---

**FIN DE ESPECIFICACIÓN FASE 3**
