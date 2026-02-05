# FASE 2: ENDURECIMIENTO DE SEGURIDAD Y TRAZABILIDAD EN DB

**Sistema:** MSP_AXS  
**Versión:** 2.0.0  
**Fecha:** 2026-01-01  
**Clasificación:** Migración de Seguridad Estructural

---

## PRINCIPIOS DE ESTA FASE

| Principio | Implementación |
|-----------|----------------|
| DB NO decide permisos de negocio | Sin lógica de autorización en triggers |
| DB SÍ impide bypass obvios | RLS + constraints |
| DB SÍ deja rastro forense | Triggers de auditoría |
| Tenant isolation como defensa en profundidad | RLS mínimo viable |

---

## 1. ROW LEVEL SECURITY (RLS) MÍNIMO VIABLE

### 1.1 Tablas CON RLS

| Tabla | Razón | Política |
|-------|-------|----------|
| `visitas` | Datos operativos de tenant | Filtro por `condominio_id` |
| `evidencias` | Artefactos de operación | Filtro por `condominio_id` |
| `casetas` | Infraestructura de tenant | Filtro por `condominio_id` |
| `user_tenant_scope` | Alcances por tenant | Filtro por `tenant_id` |

### 1.2 Tablas SIN RLS (y por qué)

| Tabla | Razón para NO aplicar RLS |
|-------|---------------------------|
| `usuarios` | Identidad es global (multi-tenant por diseño) |
| `msps_exo` | Entidad top-level, no aislable por tenant |
| `condominios_exo` | Son los tenants mismos, no se filtran por tenant |
| `authorities_gov` | Gobierno es cross-tenant (autoridades globales) |
| `policies_gov` | Políticas pueden ser globales o por tenant |
| `delegations_gov` | Delegaciones pueden cruzar tenants |
| `events_aup` | Auditoría debe ser visible para forense cross-tenant |

### 1.3 Configuración de Aplicación

**Prerrequisito:** La aplicación DEBE ejecutar antes de cada operación:
```sql
SET app.tenant_id = '<tenant_id_del_contexto>';
```

**Usuario de aplicación:**
```sql
-- Crear rol de aplicación (si no existe)
CREATE ROLE app_user NOINHERIT LOGIN PASSWORD 'secure_password';

-- Habilitar RLS para este rol
ALTER TABLE visitas FORCE ROW LEVEL SECURITY;
ALTER TABLE evidencias FORCE ROW LEVEL SECURITY;
ALTER TABLE casetas FORCE ROW LEVEL SECURITY;
ALTER TABLE user_tenant_scope FORCE ROW LEVEL SECURITY;
```

### 1.4 SQL de Implementación

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- RLS: VISITAS
-- ═══════════════════════════════════════════════════════════════════════════
-- Protege: Datos de visitas solo visibles para su tenant
-- NO protege: Acceso cross-tenant si app.tenant_id es manipulado

ALTER TABLE visitas ENABLE ROW LEVEL SECURITY;

CREATE POLICY visitas_tenant_isolation ON visitas
    FOR ALL
    TO app_user
    USING (condominio_id = current_setting('app.tenant_id', true))
    WITH CHECK (condominio_id = current_setting('app.tenant_id', true));

COMMENT ON POLICY visitas_tenant_isolation ON visitas IS
'Aislamiento por tenant. Requiere SET app.tenant_id antes de operaciones.';

-- ═══════════════════════════════════════════════════════════════════════════
-- RLS: EVIDENCIAS
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE evidencias ENABLE ROW LEVEL SECURITY;

CREATE POLICY evidencias_tenant_isolation ON evidencias
    FOR ALL
    TO app_user
    USING (condominio_id = current_setting('app.tenant_id', true))
    WITH CHECK (condominio_id = current_setting('app.tenant_id', true));

COMMENT ON POLICY evidencias_tenant_isolation ON evidencias IS
'Aislamiento por tenant. Requiere SET app.tenant_id antes de operaciones.';

-- ═══════════════════════════════════════════════════════════════════════════
-- RLS: CASETAS
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE casetas ENABLE ROW LEVEL SECURITY;

CREATE POLICY casetas_tenant_isolation ON casetas
    FOR ALL
    TO app_user
    USING (condominio_id = current_setting('app.tenant_id', true))
    WITH CHECK (condominio_id = current_setting('app.tenant_id', true));

COMMENT ON POLICY casetas_tenant_isolation ON casetas IS
'Aislamiento por tenant. Requiere SET app.tenant_id antes de operaciones.';

-- ═══════════════════════════════════════════════════════════════════════════
-- RLS: USER_TENANT_SCOPE
-- ═══════════════════════════════════════════════════════════════════════════
-- Nota: Scopes son visibles solo para operaciones dentro de su tenant
-- Excepción: Usuarios con autoridad global pueden necesitar ver todos

ALTER TABLE user_tenant_scope ENABLE ROW LEVEL SECURITY;

CREATE POLICY scope_tenant_isolation ON user_tenant_scope
    FOR ALL
    TO app_user
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMENT ON POLICY scope_tenant_isolation ON user_tenant_scope IS
'Aislamiento por tenant. Scopes solo visibles dentro de su tenant.';
```

### 1.5 Bypass Administrativo

```sql
-- Para operaciones administrativas cross-tenant, usar rol superuser
-- o crear rol admin con bypass:

CREATE ROLE admin_bypass NOINHERIT LOGIN PASSWORD 'admin_secure_password';
ALTER ROLE admin_bypass BYPASSRLS;

COMMENT ON ROLE admin_bypass IS
'⚠️ ROL ADMINISTRATIVO: Bypass de RLS. Usar solo para mantenimiento y forense.';
```

### 1.6 Riesgos Residuales

| Riesgo | Mitigación |
|--------|------------|
| App no setea `app.tenant_id` | Operación falla (current_setting retorna NULL) |
| Manipulación de `app.tenant_id` | **RIESGO RESIDUAL A CARGO DE LA APLICACIÓN** |
| Usuario con acceso directo a DB | Usar `admin_bypass` solo para mantenimiento |

---

## 2. TRIGGERS DE AUDITORÍA ESTRUCTURAL

### 2.1 Función Generadora de Eventos

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- FUNCIÓN: Generar evento de auditoría
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION fn_generate_audit_event(
    p_identity_id VARCHAR(255),
    p_tenant_id VARCHAR(255),
    p_entidad VARCHAR(50),
    p_entidad_id VARCHAR(255),
    p_accion VARCHAR(50),
    p_resultado VARCHAR(50),
    p_motivo TEXT,
    p_metadata JSONB
) RETURNS VOID AS $$
DECLARE
    v_event_id VARCHAR(255);
    v_hash_input TEXT;
    v_hash_evento VARCHAR(64);
    v_timestamp TIMESTAMPTZ;
BEGIN
    -- Timestamp UTC consistente
    v_timestamp := now() AT TIME ZONE 'UTC';
    
    -- Generar event_id único
    v_event_id := 'evt_audit_' || encode(gen_random_bytes(16), 'hex');
    
    -- Generar hash de inmutabilidad
    v_hash_input := COALESCE(p_identity_id, 'SYSTEM') || 
                    COALESCE(p_tenant_id, 'GLOBAL') || 
                    p_entidad || 
                    p_entidad_id || 
                    p_accion || 
                    p_resultado ||
                    v_timestamp::TEXT;
    v_hash_evento := encode(sha256(v_hash_input::bytea), 'hex');
    
    -- Insertar evento
    INSERT INTO events_aup (
        event_id,
        identity_id,
        session_hash,
        scope_id,
        tenant_id,
        entidad,
        entidad_id,
        accion,
        resultado,
        motivo,
        timestamp,
        hash_evento,
        metadata
    ) VALUES (
        v_event_id,
        COALESCE(p_identity_id, 'SYSTEM_TRIGGER'),
        'DB_TRIGGER_AUDIT',  -- Marca especial para eventos de trigger
        NULL,                -- Scope no aplica en triggers
        COALESCE(p_tenant_id, 'GLOBAL'),
        p_entidad,
        p_entidad_id,
        p_accion,
        p_resultado,
        p_motivo,
        v_timestamp,
        v_hash_evento,
        p_metadata
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION fn_generate_audit_event IS
'Genera evento de auditoría inmutable. Usado por triggers de seguridad.
session_hash = DB_TRIGGER_AUDIT indica evento generado por trigger, no por aplicación.';
```

### 2.2 Trigger: authorities_gov

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- TRIGGER: Auditoría de authorities_gov
-- ═══════════════════════════════════════════════════════════════════════════
-- Detecta: INSERT, UPDATE (estado), DELETE
-- Registra: Creación, revocación, suspensión, reactivación

CREATE OR REPLACE FUNCTION fn_audit_authorities_gov()
RETURNS TRIGGER AS $$
DECLARE
    v_accion VARCHAR(50);
    v_motivo TEXT;
    v_metadata JSONB;
BEGIN
    -- Determinar acción según operación
    IF TG_OP = 'INSERT' THEN
        v_accion := 'crear_autoridad';
        v_motivo := 'Nueva autoridad creada via ' || TG_NAME;
        v_metadata := jsonb_build_object(
            'authority_id', NEW.authority_id,
            'identity_id', NEW.identity_id,
            'tipo', NEW.tipo,
            'tenant_id', NEW.tenant_id,
            'estado_inicial', NEW.estado,
            'trigger_operation', TG_OP
        );
        
        PERFORM fn_generate_audit_event(
            NEW.identity_id,
            NEW.tenant_id,
            'authority',
            NEW.authority_id,
            v_accion,
            'exito',
            v_motivo,
            v_metadata
        );
        RETURN NEW;
        
    ELSIF TG_OP = 'UPDATE' THEN
        -- Solo auditar cambios de estado (críticos para seguridad)
        IF OLD.estado IS DISTINCT FROM NEW.estado THEN
            -- Determinar tipo de cambio
            IF NEW.estado = 'revocado' THEN
                v_accion := 'revocar_autoridad';
            ELSIF NEW.estado = 'suspendido' THEN
                v_accion := 'suspender_autoridad';
            ELSIF NEW.estado = 'activo' AND OLD.estado IN ('revocado', 'suspendido') THEN
                v_accion := 'reactivar_autoridad';
            ELSE
                v_accion := 'modificar_estado_autoridad';
            END IF;
            
            v_motivo := 'Cambio de estado: ' || OLD.estado || ' → ' || NEW.estado;
            v_metadata := jsonb_build_object(
                'authority_id', NEW.authority_id,
                'identity_id', NEW.identity_id,
                'estado_anterior', OLD.estado,
                'estado_nuevo', NEW.estado,
                'revoked_at_anterior', OLD.revoked_at,
                'revoked_at_nuevo', NEW.revoked_at,
                'trigger_operation', TG_OP
            );
            
            PERFORM fn_generate_audit_event(
                NEW.identity_id,
                NEW.tenant_id,
                'authority',
                NEW.authority_id,
                v_accion,
                'exito',
                v_motivo,
                v_metadata
            );
        END IF;
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        v_accion := 'eliminar_autoridad';
        v_motivo := '⚠️ AUTORIDAD ELIMINADA FÍSICAMENTE via ' || TG_NAME;
        v_metadata := jsonb_build_object(
            'authority_id', OLD.authority_id,
            'identity_id', OLD.identity_id,
            'tipo', OLD.tipo,
            'tenant_id', OLD.tenant_id,
            'estado_al_eliminar', OLD.estado,
            'trigger_operation', TG_OP,
            'warning', 'DELETE físico detectado - posible violación de auditoría'
        );
        
        PERFORM fn_generate_audit_event(
            OLD.identity_id,
            OLD.tenant_id,
            'authority',
            OLD.authority_id,
            v_accion,
            'alerta',
            v_motivo,
            v_metadata
        );
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Crear trigger
DROP TRIGGER IF EXISTS trg_audit_authorities_gov ON authorities_gov;
CREATE TRIGGER trg_audit_authorities_gov
    AFTER INSERT OR UPDATE OR DELETE ON authorities_gov
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_authorities_gov();

COMMENT ON TRIGGER trg_audit_authorities_gov ON authorities_gov IS
'Audita TODA modificación a autoridades. No permite cambios silenciosos.
Eventos marcados con session_hash = DB_TRIGGER_AUDIT.';
```

### 2.3 Trigger: user_tenant_scope

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- TRIGGER: Auditoría de user_tenant_scope
-- ═══════════════════════════════════════════════════════════════════════════
-- Detecta: INSERT, UPDATE (estado, access_level), DELETE
-- Registra: Creación, revocación, suspensión, cambio de nivel, reactivación

CREATE OR REPLACE FUNCTION fn_audit_user_tenant_scope()
RETURNS TRIGGER AS $$
DECLARE
    v_accion VARCHAR(50);
    v_motivo TEXT;
    v_metadata JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_accion := 'crear_scope';
        v_motivo := 'Nuevo scope creado via ' || TG_NAME;
        v_metadata := jsonb_build_object(
            'scope_id', NEW.id,
            'usuario_id', NEW.usuario_id,
            'tenant_id', NEW.tenant_id,
            'access_level', NEW.access_level,
            'estado_inicial', NEW.estado,
            'trigger_operation', TG_OP
        );
        
        PERFORM fn_generate_audit_event(
            NEW.usuario_id,
            NEW.tenant_id,
            'scope',
            NEW.id::VARCHAR,
            v_accion,
            'exito',
            v_motivo,
            v_metadata
        );
        RETURN NEW;
        
    ELSIF TG_OP = 'UPDATE' THEN
        -- Auditar cambios de estado
        IF OLD.estado IS DISTINCT FROM NEW.estado THEN
            IF NEW.estado = 'revocado' THEN
                v_accion := 'revocar_scope';
            ELSIF NEW.estado = 'suspendido' THEN
                v_accion := 'suspender_scope';
            ELSIF NEW.estado = 'activo' AND OLD.estado IN ('revocado', 'suspendido') THEN
                v_accion := 'reactivar_scope';
            ELSE
                v_accion := 'modificar_estado_scope';
            END IF;
            
            v_motivo := 'Cambio de estado: ' || OLD.estado || ' → ' || NEW.estado;
            v_metadata := jsonb_build_object(
                'scope_id', NEW.id,
                'usuario_id', NEW.usuario_id,
                'tenant_id', NEW.tenant_id,
                'estado_anterior', OLD.estado,
                'estado_nuevo', NEW.estado,
                'revoked_at_anterior', OLD.revoked_at,
                'revoked_at_nuevo', NEW.revoked_at,
                'trigger_operation', TG_OP
            );
            
            PERFORM fn_generate_audit_event(
                NEW.usuario_id,
                NEW.tenant_id,
                'scope',
                NEW.id::VARCHAR,
                v_accion,
                'exito',
                v_motivo,
                v_metadata
            );
        END IF;
        
        -- Auditar cambios de access_level (escalamiento/degradación)
        IF OLD.access_level IS DISTINCT FROM NEW.access_level THEN
            v_accion := 'modificar_nivel_scope';
            v_motivo := 'Cambio de nivel: ' || OLD.access_level || ' → ' || NEW.access_level;
            v_metadata := jsonb_build_object(
                'scope_id', NEW.id,
                'usuario_id', NEW.usuario_id,
                'tenant_id', NEW.tenant_id,
                'access_level_anterior', OLD.access_level,
                'access_level_nuevo', NEW.access_level,
                'trigger_operation', TG_OP,
                'warning', 'CAMBIO DE NIVEL DE ACCESO'
            );
            
            PERFORM fn_generate_audit_event(
                NEW.usuario_id,
                NEW.tenant_id,
                'scope',
                NEW.id::VARCHAR,
                v_accion,
                'alerta',
                v_motivo,
                v_metadata
            );
        END IF;
        
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        v_accion := 'eliminar_scope';
        v_motivo := '⚠️ SCOPE ELIMINADO FÍSICAMENTE via ' || TG_NAME;
        v_metadata := jsonb_build_object(
            'scope_id', OLD.id,
            'usuario_id', OLD.usuario_id,
            'tenant_id', OLD.tenant_id,
            'access_level', OLD.access_level,
            'estado_al_eliminar', OLD.estado,
            'trigger_operation', TG_OP,
            'warning', 'DELETE físico detectado - posible violación de auditoría'
        );
        
        PERFORM fn_generate_audit_event(
            OLD.usuario_id,
            OLD.tenant_id,
            'scope',
            OLD.id::VARCHAR,
            v_accion,
            'alerta',
            v_motivo,
            v_metadata
        );
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Crear trigger
DROP TRIGGER IF EXISTS trg_audit_user_tenant_scope ON user_tenant_scope;
CREATE TRIGGER trg_audit_user_tenant_scope
    AFTER INSERT OR UPDATE OR DELETE ON user_tenant_scope
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_user_tenant_scope();

COMMENT ON TRIGGER trg_audit_user_tenant_scope ON user_tenant_scope IS
'Audita TODA modificación a scopes. Detecta escalamiento de privilegios.
Eventos marcados con session_hash = DB_TRIGGER_AUDIT.';
```

---

## 3. PROTECCIÓN CONTRA REPLAY LÓGICO

### 3.1 Problema

Un atacante con acceso SQL puede:
1. Revocar una autoridad: `UPDATE authorities_gov SET estado = 'revocado'`
2. Esperar que pase desapercibido
3. Reactivar: `UPDATE authorities_gov SET estado = 'activo', revoked_at = NULL`

### 3.2 Solución: Constraint + Trigger de Bloqueo

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- PROTECCIÓN: Impedir reactivación silenciosa de authorities
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION fn_block_silent_reactivation_authority()
RETURNS TRIGGER AS $$
BEGIN
    -- Bloquear reactivación si revoked_at tiene valor
    IF OLD.estado = 'revocado' AND NEW.estado = 'activo' THEN
        -- Permitir SOLO si se usa flag explícito en metadata
        IF NOT (NEW.metadata ? 'reactivation_authorized' AND 
                (NEW.metadata->>'reactivation_authorized')::BOOLEAN = TRUE) THEN
            RAISE EXCEPTION 
                'REACTIVACIÓN BLOQUEADA: Authority % fue revocada en %. '
                'Para reactivar, usar metadata.reactivation_authorized = true',
                OLD.authority_id, OLD.revoked_at;
        END IF;
        
        -- Limpiar flag después de validar (no queda en metadata permanente)
        NEW.metadata := NEW.metadata - 'reactivation_authorized';
    END IF;
    
    -- Bloquear limpieza de revoked_at si estado sigue revocado
    IF OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS NULL AND NEW.estado = 'revocado' THEN
        RAISE EXCEPTION 
            'MANIPULACIÓN BLOQUEADA: No se puede limpiar revoked_at sin cambiar estado';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_block_reactivation_authority ON authorities_gov;
CREATE TRIGGER trg_block_reactivation_authority
    BEFORE UPDATE ON authorities_gov
    FOR EACH ROW
    EXECUTE FUNCTION fn_block_silent_reactivation_authority();

COMMENT ON TRIGGER trg_block_reactivation_authority ON authorities_gov IS
'Impide reactivación silenciosa. Requiere flag explícito en metadata para reactivar.';
```

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- PROTECCIÓN: Impedir reactivación silenciosa de scopes
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION fn_block_silent_reactivation_scope()
RETURNS TRIGGER AS $$
BEGIN
    -- Bloquear reactivación si revoked_at tiene valor
    IF OLD.estado = 'revocado' AND NEW.estado = 'activo' THEN
        IF NOT (NEW.metadata_json ? 'reactivation_authorized' AND 
                (NEW.metadata_json->>'reactivation_authorized')::BOOLEAN = TRUE) THEN
            RAISE EXCEPTION 
                'REACTIVACIÓN BLOQUEADA: Scope % fue revocado en %. '
                'Para reactivar, usar metadata_json.reactivation_authorized = true',
                OLD.id, OLD.revoked_at;
        END IF;
        
        NEW.metadata_json := NEW.metadata_json - 'reactivation_authorized';
    END IF;
    
    IF OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS NULL AND NEW.estado = 'revocado' THEN
        RAISE EXCEPTION 
            'MANIPULACIÓN BLOQUEADA: No se puede limpiar revoked_at sin cambiar estado';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_block_reactivation_scope ON user_tenant_scope;
CREATE TRIGGER trg_block_reactivation_scope
    BEFORE UPDATE ON user_tenant_scope
    FOR EACH ROW
    EXECUTE FUNCTION fn_block_silent_reactivation_scope();

COMMENT ON TRIGGER trg_block_reactivation_scope ON user_tenant_scope IS
'Impide reactivación silenciosa. Requiere flag explícito en metadata_json para reactivar.';
```

### 3.3 Uso Legítimo de Reactivación

```sql
-- Para reactivar legítimamente (deja rastro en auditoría):
UPDATE authorities_gov 
SET estado = 'activo',
    metadata = COALESCE(metadata, '{}'::jsonb) || 
               '{"reactivation_authorized": true, "reactivation_reason": "Solicitud aprobada por admin"}'::jsonb
WHERE authority_id = 'auth_xxx';

-- El trigger de auditoría registrará la reactivación
-- El trigger de bloqueo permitirá por flag explícito
-- El flag se elimina automáticamente después de validar
```

### 3.4 Protección de events_aup

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- PROTECCIÓN: events_aup es APPEND-ONLY
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION fn_protect_events_immutability()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'INMUTABILIDAD VIOLADA: events_aup no permite UPDATE';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'INMUTABILIDAD VIOLADA: events_aup no permite DELETE';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_protect_events_immutability ON events_aup;
CREATE TRIGGER trg_protect_events_immutability
    BEFORE UPDATE OR DELETE ON events_aup
    FOR EACH ROW
    EXECUTE FUNCTION fn_protect_events_immutability();

COMMENT ON TRIGGER trg_protect_events_immutability ON events_aup IS
'INMUTABILIDAD: events_aup es append-only. UPDATE y DELETE están bloqueados.';
```

---

## 4. LINEAMIENTOS DE TIMESTAMP Y TIMEZONE

### 4.1 Estándar UTC

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- CONFIGURACIÓN: Forzar UTC en sesiones de aplicación
-- ═══════════════════════════════════════════════════════════════════════════

-- Para rol de aplicación
ALTER ROLE app_user SET timezone TO 'UTC';

-- Verificar en cada conexión
CREATE OR REPLACE FUNCTION fn_ensure_utc_timezone()
RETURNS TRIGGER AS $$
BEGIN
    IF current_setting('TIMEZONE') != 'UTC' THEN
        RAISE WARNING 'Timezone no es UTC (actual: %). Eventos pueden tener inconsistencias.',
            current_setting('TIMEZONE');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 4.2 Función para Timestamps Consistentes

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- FUNCIÓN: Obtener timestamp UTC consistente
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION fn_utc_now()
RETURNS TIMESTAMPTZ AS $$
BEGIN
    RETURN now() AT TIME ZONE 'UTC';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION fn_utc_now IS
'Retorna timestamp UTC consistente. Usar en lugar de now() para auditoría.';
```

### 4.3 Defaults en Tablas Nuevas

Para tablas futuras o modificaciones:
```sql
-- Usar TIMESTAMPTZ (con timezone) en lugar de TIMESTAMP
-- Default: fn_utc_now() en lugar de CURRENT_TIMESTAMP

-- Ejemplo:
ALTER TABLE authorities_gov 
    ALTER COLUMN created_at SET DEFAULT fn_utc_now();
```

### 4.4 Riesgo Residual

| Riesgo | Estado |
|--------|--------|
| Columnas existentes con TIMESTAMP sin TZ | **RIESGO RESIDUAL** - No modificar en esta fase |
| Datos históricos con timezone inconsistente | **RIESGO RESIDUAL** - Reconciliación manual si es necesario |
| Clientes conectando con timezone distinto | Mitigado por `ALTER ROLE SET timezone` |

---

## 5. RESUMEN DE PROTECCIONES

### 5.1 Matriz de Protección

| Ataque | Protección | Nivel |
|--------|------------|-------|
| Acceso cross-tenant (datos operativos) | RLS en visitas, evidencias, casetas, scopes | DB |
| Modificación silenciosa de authorities | Trigger de auditoría | DB |
| Modificación silenciosa de scopes | Trigger de auditoría | DB |
| Escalamiento de access_level | Trigger de auditoría con alerta | DB |
| Reactivación de authority revocada | Trigger de bloqueo + flag | DB |
| Reactivación de scope revocado | Trigger de bloqueo + flag | DB |
| Eliminación de registros de auditoría | Trigger de inmutabilidad | DB |
| Manipulación de timestamps | UTC forzado en rol | DB |

### 5.2 Riesgos Residuales a Cargo de Aplicación

| Riesgo | Mitigación Requerida en App |
|--------|----------------------------|
| Manipulación de `app.tenant_id` | Validar tenant_id contra JWT/sesión |
| Autorización de negocio | Verificar authorities_gov + policies_gov |
| Acceso a tablas sin RLS (authorities, policies) | Filtrar en queries de aplicación |
| Validación de identity_id en triggers | App debe setear contexto de usuario |

---

## 6. SCRIPT DE MIGRACIÓN COMPLETO

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN: FASE 2 - SEGURIDAD Y TRAZABILIDAD EN DB
-- ═══════════════════════════════════════════════════════════════════════════
-- Ejecutar DESPUÉS de:
--   - Todas las migraciones previas
--   - Crear rol app_user
--
-- ORDEN DE EJECUCIÓN:
--   1. Funciones auxiliares
--   2. RLS
--   3. Triggers de auditoría
--   4. Triggers de protección
-- ═══════════════════════════════════════════════════════════════════════════

-- Ver secciones 1, 2, 3, 4 de este documento para SQL completo.
-- Copiar y ejecutar en orden.

-- ═══════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POST-MIGRACIÓN
-- ═══════════════════════════════════════════════════════════════════════════

-- Test 1: Verificar RLS activo
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename IN ('visitas', 'evidencias', 'casetas', 'user_tenant_scope');

-- Test 2: Verificar triggers
SELECT tgname, tgrelid::regclass, tgenabled 
FROM pg_trigger 
WHERE tgname LIKE 'trg_%';

-- Test 3: Intentar reactivación (debe fallar)
-- UPDATE authorities_gov SET estado = 'activo' 
-- WHERE estado = 'revocado' LIMIT 1;

-- Test 4: Intentar modificar evento (debe fallar)
-- UPDATE events_aup SET motivo = 'hack' LIMIT 1;
```

---

## APÉNDICE: Checklist de Implementación

- [ ] Crear rol `app_user` con password seguro
- [ ] Crear rol `admin_bypass` con password seguro
- [ ] Ejecutar función `fn_generate_audit_event`
- [ ] Ejecutar función `fn_utc_now`
- [ ] Habilitar RLS en `visitas`
- [ ] Habilitar RLS en `evidencias`
- [ ] Habilitar RLS en `casetas`
- [ ] Habilitar RLS en `user_tenant_scope`
- [ ] Crear trigger `trg_audit_authorities_gov`
- [ ] Crear trigger `trg_audit_user_tenant_scope`
- [ ] Crear trigger `trg_block_reactivation_authority`
- [ ] Crear trigger `trg_block_reactivation_scope`
- [ ] Crear trigger `trg_protect_events_immutability`
- [ ] Configurar timezone UTC en rol `app_user`
- [ ] Actualizar aplicación para `SET app.tenant_id`
- [ ] Documentar uso de `reactivation_authorized` para reactivaciones legítimas

---

**FIN DE ESPECIFICACIÓN FASE 2**
