# 🗄️ ESTRUCTURA COMPLETA DE TABLAS - MSP_AXS

**Sistema:** MSP_AXS (Control de Accesos Residenciales)  
**Arquitectura:** AUP (Architecture from Unified Principles)  
**Fecha:** 31 de diciembre de 2025  
**Versión:** 3.0.0-aup-gov

---

## 📦 ORGANIZACIÓN EN 3 BASES DE DATOS

El sistema separa responsabilidades en **3 dominios independientes**:

| Base de Datos | Responsabilidad | Tablas |
|---------------|-----------------|--------|
| **aup_core** | Identidad, Alcance, Negocio | 7 tablas |
| **aup_event** | Verdad Histórica Inmutable | 1 tabla |
| **aup_gov** | Gobierno y Poder Explícito | 3 tablas |

**Total:** 11 tablas

---

## 🔵 BASE DE DATOS: aup_core

### Responsabilidad
- AUP_IDENTITY: Quién existe en el sistema
- AUP_SCOPE: Dónde puede actuar cada identidad
- AUP_TENANT: Contexto de aislamiento multi-tenant
- Entidades de negocio: Visitas, Evidencias, Casetas

---

### 1. msps_exo

**Propósito:** Proveedores de servicios de seguridad (top-level)

```sql
CREATE TABLE msps_exo (
    id SERIAL PRIMARY KEY,
    msp_id VARCHAR(36) UNIQUE NOT NULL,
    nombre VARCHAR(255),
    
    -- Índices
    CREATE INDEX idx_msps_msp_id ON msps_exo(msp_id);
);
```

**Campos:**
- `id`: PK técnico (autoincremental)
- `msp_id`: PK de negocio (UUID como String)
- `nombre`: Nombre del MSP

---

### 2. condominios_exo

**Propósito:** Tenants (contexto de aislamiento operativo)

```sql
CREATE TABLE condominios_exo (
    id SERIAL PRIMARY KEY,
    condominio_id VARCHAR(36) UNIQUE NOT NULL,
    msp_id VARCHAR(36) REFERENCES msps_exo(msp_id),
    nombre VARCHAR(255),
    
    -- Índices
    CREATE INDEX idx_condominios_condominio_id ON condominios_exo(condominio_id);
    CREATE INDEX idx_condominios_msp_id ON condominios_exo(msp_id);
);
```

**Campos:**
- `id`: PK técnico
- `condominio_id`: PK de negocio (UUID)
- `msp_id`: FK a MSP propietario
- `nombre`: Nombre del condominio

**Axioma AUP_TENANT:**
> Cada condominio es un universo independiente. Los datos de Condo A no se ven en Condo B.

---

### 3. usuarios

**Propósito:** Identidades que pueden autenticarse (AUP_IDENTITY)

```sql
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    usuario_id VARCHAR(36) UNIQUE NOT NULL,
    msp_id VARCHAR(36),
    condominio_id VARCHAR(36),  -- Legacy, usar user_tenant_scope
    casa_unidad VARCHAR(50),
    nombre VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    rol VARCHAR(50),  -- MSP_ADMIN, ADMIN_CONDOMINIO, GUARDIA, RESIDENTE
    password_hash TEXT,
    creado TIMESTAMPTZ DEFAULT now(),
    
    -- Índices
    CREATE INDEX idx_usuarios_usuario_id ON usuarios(usuario_id);
    CREATE INDEX idx_usuarios_email ON usuarios(email);
);
```

**Campos:**
- `id`: PK técnico
- `usuario_id`: PK de negocio (UUID)
- `email`: Identificador único de login
- `password_hash`: Contraseña con bcrypt
- `rol`: Rol base (usado para contexto general)
- `condominio_id`: Tenant principal (legacy, usar scopes)

**Axioma AUP_IDENTITY:**
> Usuario sin scope válido no puede operar en ningún tenant.

---

### 4. user_tenant_scope

**Propósito:** Alcance explícito de identidad sobre tenant (AUP_SCOPE)

```sql
CREATE TABLE user_tenant_scope (
    id SERIAL PRIMARY KEY,
    usuario_id VARCHAR(36) NOT NULL REFERENCES usuarios(usuario_id),
    tenant_id VARCHAR(36) NOT NULL REFERENCES condominios_exo(condominio_id),
    access_level VARCHAR(50) NOT NULL,  -- msp_admin, admin_condominio, guardia, residente, lectura
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',  -- activo, inactivo, suspendido, revocado
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    metadata_json JSONB,
    
    -- Índices
    CREATE INDEX idx_scope_usuario ON user_tenant_scope(usuario_id);
    CREATE INDEX idx_scope_tenant ON user_tenant_scope(tenant_id);
    CREATE INDEX idx_scope_estado ON user_tenant_scope(estado);
    CREATE INDEX idx_scope_usuario_tenant ON user_tenant_scope(usuario_id, tenant_id);
);
```

**Campos:**
- `usuario_id`: FK a identidad
- `tenant_id`: FK a condominio (tenant)
- `access_level`: Nivel de acceso (DÓNDE puede actuar)
- `estado`: activo/revocado/suspendido
- `revoked_at`: Timestamp de revocación

**Axioma AUP_SCOPE:**
> 1. Scope NO se serializa en JWT (es dinámico)  
> 2. Sistema NO infiere alcance, lo VALIDA  
> 3. Revocación es inmediata (no espera expiración de token)

**Niveles de access_level:**
- `msp_admin` (100): Todo en toda la plataforma
- `admin_condominio` (80): Todo en su condominio
- `guardia` (60): Registrar accesos, validar QR
- `residente` (40): Crear visitas, ver sus propias visitas
- `lectura` (20): Solo consulta

---

### 5. casetas

**Propósito:** Puntos de control de acceso físico

```sql
CREATE TABLE casetas (
    id SERIAL PRIMARY KEY,
    caseta_id VARCHAR(36) UNIQUE NOT NULL,
    condominio_id VARCHAR(36) REFERENCES condominios_exo(condominio_id),
    nombre VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Índices
    CREATE INDEX idx_casetas_caseta_id ON casetas(caseta_id);
    CREATE INDEX idx_casetas_condominio ON casetas(condominio_id);
);
```

**Campos:**
- `caseta_id`: PK de negocio (UUID)
- `condominio_id`: FK a tenant
- `nombre`: Nombre de la caseta (ej: "Caseta Norte")

---

### 6. visitas

**Propósito:** Registro de visitas autorizadas a condominios

```sql
CREATE TABLE visitas (
    id SERIAL PRIMARY KEY,
    visita_id VARCHAR(36) UNIQUE NOT NULL,
    condominio_id VARCHAR(36) REFERENCES condominios_exo(condominio_id),
    nombre_visitante VARCHAR(255),
    casa_unidad VARCHAR(50),
    tipo_visita VARCHAR(50),  -- frecuente, eventual, proveedor
    vigencia TIMESTAMPTZ,
    qr_token VARCHAR(255) UNIQUE,
    qr_vigencia TIMESTAMPTZ,
    estado VARCHAR(50) DEFAULT 'pendiente',  -- pendiente, activa, completada, cancelada
    entrada_registrada_en TIMESTAMPTZ,
    salida_registrada_en TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Índices
    CREATE INDEX idx_visitas_visita_id ON visitas(visita_id);
    CREATE INDEX idx_visitas_condominio ON visitas(condominio_id);
    CREATE INDEX idx_visitas_qr_token ON visitas(qr_token);
    CREATE INDEX idx_visitas_estado ON visitas(estado);
);
```

**Campos:**
- `visita_id`: PK de negocio (UUID)
- `condominio_id`: FK a tenant
- `nombre_visitante`: Nombre del visitante
- `qr_token`: Token único del QR (firmado)
- `qr_vigencia`: Expiración del QR
- `estado`: Ciclo de vida de la visita
- `entrada_registrada_en`: Timestamp de ingreso
- `salida_registrada_en`: Timestamp de salida

---

### 7. evidencias

**Propósito:** Evidencia fotográfica de entrada/salida

```sql
CREATE TABLE evidencias (
    id SERIAL PRIMARY KEY,
    evidencia_id VARCHAR(36) UNIQUE NOT NULL,
    visita_id VARCHAR(36) NOT NULL REFERENCES visitas(visita_id) ON DELETE CASCADE,
    categoria VARCHAR(20) NOT NULL,  -- 'entrada' | 'salida'
    sub_tipo VARCHAR(50) NOT NULL,   -- 'visitante', 'ine_frente', 'ine_reverso', 'placas', 'vehiculo', 'documento'
    archivo_url TEXT NOT NULL,       -- S3/storage path
    hash_sha256 TEXT,                -- SHA-256 del archivo (integridad)
    guardia_id VARCHAR(36) NOT NULL REFERENCES usuarios(usuario_id),
    metadata_json JSONB,             -- {device, gps, app_version, file_size, mime_type}
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    -- Índices
    CREATE INDEX idx_evidencias_evidencia_id ON evidencias(evidencia_id);
    CREATE INDEX idx_evidencias_visita ON evidencias(visita_id);
    CREATE INDEX idx_evidencias_categoria ON evidencias(categoria);
    CREATE INDEX idx_evidencias_guardia ON evidencias(guardia_id);
    CREATE INDEX idx_evidencias_created ON evidencias(created_at DESC);
);
```

**Campos clave:**
- `guardia_id`: **Quién capturó la evidencia** (AUP_IDENTITY)
- `archivo_url`: Path del archivo en storage
- `hash_sha256`: Verificación de integridad
- `metadata_json`: Contexto extensible (GPS, dispositivo, etc.)

**Axioma AUP_IDENTITY:**
> Toda evidencia DEBE tener identidad responsable (guardia_id). No se infiere quién capturó.

---

## 🟢 BASE DE DATOS: aup_event

### Responsabilidad
- AUP_EVENT: Declaración inmutable de hechos
- Append-only (solo INSERT, nunca UPDATE/DELETE)
- Base para auditoría y reconstrucción de estado

---

### 8. events_aup

**Propósito:** Registro inmutable de todos los eventos del sistema

```sql
CREATE TABLE events_aup (
    id SERIAL PRIMARY KEY,
    tipo_evento VARCHAR(50) NOT NULL,           -- sesion_iniciada, qr_generado, visita_creada, politica_evaluada
    
    -- AUP_IDENTITY: Quién ejecutó
    identity_id VARCHAR(36) NOT NULL,
    
    -- AUP_TENANT: Dónde ocurrió
    tenant_id VARCHAR(36) NOT NULL,
    
    -- Declaración del hecho
    entidad VARCHAR(50) NOT NULL,               -- visita, qr, evidencia, usuario, scope
    entidad_id VARCHAR(36) NOT NULL,
    accion VARCHAR(50) NOT NULL,                -- crear, validar, registrar, revocar, denegar
    resultado VARCHAR(50) NOT NULL,             -- permitido, denegado, error, exito, fallo
    motivo TEXT,
    
    -- Inmutabilidad
    timestamp TIMESTAMPTZ DEFAULT now() NOT NULL,
    hash_evento VARCHAR(64) UNIQUE NOT NULL,    -- SHA-256 de campos críticos
    
    -- Metadata adicional
    metadata_json JSONB,
    
    -- Índices compuestos para queries forenses
    CREATE INDEX idx_event_identity_tenant_time ON events_aup(identity_id, tenant_id, timestamp);
    CREATE INDEX idx_event_entidad_time ON events_aup(entidad, entidad_id, timestamp);
    CREATE INDEX idx_event_resultado_time ON events_aup(resultado, timestamp);
    CREATE INDEX idx_event_tipo_time ON events_aup(tipo_evento, timestamp);
    CREATE INDEX idx_event_timestamp ON events_aup(timestamp DESC);
);
```

**Campos clave:**
- `identity_id`: Quién ejecutó (AUP_IDENTITY)
- `tenant_id`: Dónde ocurrió (AUP_TENANT)
- `accion` + `resultado`: Qué pasó (permitido/denegado)
- `hash_evento`: SHA-256 para detectar manipulación
- `timestamp`: Cuándo ocurrió (inmutable)

**Axioma AUP_EVENT:**
> 1. Si no hay evento, no ocurrió para el sistema  
> 2. Estado del sistema se puede reconstruir desde eventos  
> 3. Hash cambiado = manipulación detectable

**Ejemplos de eventos:**
```json
{
  "tipo_evento": "qr_generado",
  "identity_id": "usr-123",
  "tenant_id": "condo-abc",
  "entidad": "visita",
  "entidad_id": "vis-456",
  "accion": "generar_qr",
  "resultado": "exito",
  "motivo": "Dentro de límite de política max_qr_dias=3"
}
```

---

## 🔴 BASE DE DATOS: aup_gov

### Responsabilidad
- AUP_AUTHORITY: Quién tiene poder de gobierno
- AUP_POLICY: Bajo qué límites se puede actuar
- AUP_DELEGATION: Transferencia explícita de poder

---

### 9. authorities_gov

**Propósito:** Actores con potestad declarada para gobernar

```sql
CREATE TABLE authorities_gov (
    authority_id VARCHAR(36) PRIMARY KEY,
    identity_id VARCHAR(36) NOT NULL,           -- FK a aup_core.usuarios (sin constraint cross-DB)
    tipo VARCHAR(20) NOT NULL,                  -- 'global' | 'first_tier'
    tenant_id VARCHAR(36),                      -- NULL si tipo=global
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',  -- activo, revocado, suspendido
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    revoked_at TIMESTAMPTZ,
    metadata_json JSONB,
    
    -- Índices
    CREATE INDEX idx_authority_identity ON authorities_gov(identity_id, estado);
    CREATE INDEX idx_authority_tenant ON authorities_gov(tenant_id, estado);
    CREATE INDEX idx_authority_tipo ON authorities_gov(tipo);
);
```

**Tipos de autoridad:**
- `GLOBAL`: Poder sobre toda la plataforma (ej: MSP_ADMIN)
- `FIRST_TIER`: Poder sobre tenant específico (ej: Dueño de Condominio A)

**Axioma AUP_AUTHORITY:**
> Todo poder es explícito (no heredado). Revocación es inmediata.

---

### 10. policies_gov

**Propósito:** Reglas declarativas que gobiernan límites

```sql
CREATE TABLE policies_gov (
    policy_id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,               -- qr_vigencia_dias, max_tenants, max_usuarios
    descripcion TEXT,
    ambito VARCHAR(20) NOT NULL,                -- 'global' | 'tenant'
    target_tenant_id VARCHAR(36),               -- NULL si ambito=global
    accion_objetivo VARCHAR(100) NOT NULL,      -- generar_qr, crear_tenant, asignar_scope
    limites JSONB NOT NULL,                     -- {"max_count": 10}, {"max_dias_vigencia": 7}
    valida_desde TIMESTAMPTZ DEFAULT now() NOT NULL,
    valida_hasta TIMESTAMPTZ,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    metadata_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    -- Índices
    CREATE INDEX idx_policy_ambito ON policies_gov(ambito, accion_objetivo, estado);
    CREATE INDEX idx_policy_tenant ON policies_gov(target_tenant_id, estado);
    CREATE INDEX idx_policy_nombre ON policies_gov(nombre);
);
```

**Ejemplos de políticas:**
```json
// Política global
{
  "nombre": "max_tenants_free_plan",
  "ambito": "global",
  "accion_objetivo": "crear_tenant",
  "limites": {"max_count": 2}
}

// Política por tenant
{
  "nombre": "qr_vigencia_dias",
  "ambito": "tenant",
  "target_tenant_id": "condo-abc",
  "accion_objetivo": "generar_qr",
  "limites": {"max_dias_vigencia": 3}
}
```

**Axioma AUP_POLICY:**
> La política precede a la operación (policy-first). Sin política asignada → denegado.

---

### 11. delegations_gov

**Propósito:** Transferencia explícita de poder desde autoridad

```sql
CREATE TABLE delegations_gov (
    delegation_id VARCHAR(36) PRIMARY KEY,
    authority_id VARCHAR(36) NOT NULL REFERENCES authorities_gov(authority_id),
    target_identity_id VARCHAR(36),             -- A quién se delega (identidad directa)
    target_scope_id VARCHAR(36),                -- O a un scope (mutuamente excluyente)
    permisos_delegados JSONB NOT NULL,          -- ["crear_tenant", "asignar_scope"]
    valida_desde TIMESTAMPTZ DEFAULT now() NOT NULL,
    valida_hasta TIMESTAMPTZ,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    metadata_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    revoked_at TIMESTAMPTZ,
    
    -- Índices
    CREATE INDEX idx_delegation_authority ON delegations_gov(authority_id);
    CREATE INDEX idx_delegation_target_identity ON delegations_gov(target_identity_id);
    CREATE INDEX idx_delegation_estado ON delegations_gov(estado);
);
```

**Ejemplo de delegación:**
```json
{
  "authority_id": "auth-global-123",
  "target_identity_id": "usr-456",
  "permisos_delegados": ["crear_tenant", "asignar_scope"],
  "valida_hasta": "2026-12-31T23:59:59Z"
}
```

**Axioma AUP_DELEGATION:**
> Todo poder delegado es: 1) Explícito, 2) Acotado, 3) Revocable.

---

## 📊 RESUMEN DE ESTRUCTURA

### Por Dominio

| Dominio | Tablas | Propósito |
|---------|--------|-----------|
| **aup_core** | 7 | Identidad, Alcance, Negocio |
| **aup_event** | 1 | Verdad Histórica Inmutable |
| **aup_gov** | 3 | Gobierno y Poder Explícito |

### Por Responsabilidad AUP

| Principio | Tablas Involucradas |
|-----------|-------------------|
| **AUP_IDENTITY** | usuarios |
| **AUP_TENANT** | condominios_exo, msps_exo |
| **AUP_SCOPE** | user_tenant_scope |
| **AUP_EVENT** | events_aup |
| **AUP_AUTHORITY** | authorities_gov |
| **AUP_POLICY** | policies_gov |
| **AUP_DELEGATION** | delegations_gov |

### Relaciones Cross-Domain

```
aup_core.usuarios ─────────┐
                           │ (sin FK, solo UUID)
aup_event.events_aup ──────┤ identity_id
                           │
aup_gov.authorities_gov ───┘

aup_core.condominios_exo ──┐
                           │ (sin FK, solo UUID)
aup_event.events_aup ──────┤ tenant_id
                           │
aup_gov.policies_gov ──────┘
```

**Nota:** No hay foreign keys entre dominios. Solo se referencian por UUIDs.

---

## 🔑 TIPOS DE DATOS USADOS

| Tipo | Uso | Ejemplo |
|------|-----|---------|
| `SERIAL` | PK técnico autoincremental | id |
| `VARCHAR(36)` | UUID como String | usuario_id, visita_id |
| `VARCHAR(50-255)` | Strings cortos | nombre, email, rol |
| `TEXT` | Strings largos | descripcion, motivo, archivo_url |
| `TIMESTAMPTZ` | Timestamps con timezone | created_at, timestamp |
| `JSONB` | Metadata extensible | metadata_json, limites |

**Decisión:** UUID como `VARCHAR(36)` por consistencia con código Python existente.

---

## 📈 ÍNDICES CRÍTICOS

### Performance en Queries Comunes

```sql
-- Validación de scope
user_tenant_scope(usuario_id, tenant_id)

-- Auditoría forense
events_aup(identity_id, tenant_id, timestamp)
events_aup(entidad, entidad_id, timestamp)

-- Validación de QR
visitas(qr_token)

-- Evidencias por visita
evidencias(visita_id)

-- Políticas activas
policies_gov(ambito, accion_objetivo, estado)
```

---

## ✅ VALIDACIÓN DE INTEGRIDAD

### Constraints Recomendados

```sql
-- Categorías de evidencia
ALTER TABLE evidencias ADD CONSTRAINT chk_categoria 
    CHECK (categoria IN ('entrada', 'salida'));

-- Estados de visita
ALTER TABLE visitas ADD CONSTRAINT chk_estado
    CHECK (estado IN ('pendiente', 'activa', 'completada', 'cancelada'));

-- Estados de scope
ALTER TABLE user_tenant_scope ADD CONSTRAINT chk_estado_scope
    CHECK (estado IN ('activo', 'inactivo', 'suspendido', 'revocado'));
```

---

## 🚀 PRÓXIMOS PASOS

1. **Crear bases de datos en Neon/PostgreSQL**
2. **Ejecutar migraciones por dominio**
3. **Seed con datos de bootstrap** (authorities, policies)
4. **Verificar índices** con `EXPLAIN ANALYZE`
5. **Configurar backups automáticos**

---

**Generado por:** Claude (Arquitectura AUP)  
**Fecha:** 31 de diciembre de 2025  
**Versión:** 3.0.0-aup-gov
