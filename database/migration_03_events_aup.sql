-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN: PASO 3 - AUP_EVENT
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- Crea tabla events_aup para almacenar AUP_EVENT (declaración de hechos).
--
-- Ejecutar DESPUÉS de:
--   - database/schema_axs.sql (tablas base)
--   - PASO 2 (tabla user_tenant_scope)
--
-- ═══════════════════════════════════════════════════════════════════════════

-- Tabla de eventos estructurales (AUP_EVENT)
CREATE TABLE IF NOT EXISTS events_aup (
    -- Identificador único del evento
    event_id VARCHAR(255) PRIMARY KEY,
    
    -- -------------------------------------------------------------------------
    -- Contexto AUP (QUIÉN, DÓNDE, CÓMO)
    -- -------------------------------------------------------------------------
    
    -- AUP_IDENTITY: Quién actúa
    identity_id VARCHAR(255) NOT NULL,
    
    -- AUP_SESSION: Hash del JWT (contexto temporal)
    session_hash VARCHAR(255) NOT NULL,
    
    -- AUP_SCOPE: Alcance sobre tenant (puede ser NULL en login)
    scope_id VARCHAR(255),
    
    -- AUP_TENANT: Dónde ocurre
    tenant_id VARCHAR(255) NOT NULL,
    
    -- -------------------------------------------------------------------------
    -- Declaración del Hecho (QUÉ, RESULTADO)
    -- -------------------------------------------------------------------------
    
    -- Entidad afectada (visita, qr, evidencia, usuario, condominio, scope, session)
    entidad VARCHAR(50) NOT NULL,
    
    -- ID específico de la entidad
    entidad_id VARCHAR(255) NOT NULL,
    
    -- Acción ejecutada (crear, validar, registrar, revocar, denegar, etc.)
    accion VARCHAR(50) NOT NULL,
    
    -- Resultado de la acción (permitido, denegado, error, exito, fallo)
    resultado VARCHAR(50) NOT NULL,
    
    -- Motivo estructural (por qué ocurrió o falló)
    motivo TEXT,
    
    -- -------------------------------------------------------------------------
    -- Metadatos y Trazabilidad
    -- -------------------------------------------------------------------------
    
    -- Timestamp inmutable
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Hash de inmutabilidad (SHA-256 de campos críticos)
    hash_evento VARCHAR(64) NOT NULL UNIQUE,
    
    -- Metadata adicional estructurada (JSON)
    metadata JSONB,
    
    -- -------------------------------------------------------------------------
    -- Foreign Keys
    -- -------------------------------------------------------------------------
    
    FOREIGN KEY (identity_id) REFERENCES usuarios_exo(usuario_id) ON DELETE CASCADE,
    FOREIGN KEY (scope_id) REFERENCES user_tenant_scope(id) ON DELETE SET NULL,
    FOREIGN KEY (tenant_id) REFERENCES condominios_exo(condominio_id) ON DELETE CASCADE
);

-- ═══════════════════════════════════════════════════════════════════════════
-- Índices para Consultas Frecuentes
-- ═══════════════════════════════════════════════════════════════════════════

-- Query: "¿Qué hizo este usuario?"
CREATE INDEX idx_events_identity ON events_aup(identity_id, timestamp DESC);

-- Query: "¿Qué pasó en este tenant?"
CREATE INDEX idx_events_tenant ON events_aup(tenant_id, timestamp DESC);

-- Query: "¿Qué eventos afectaron esta entidad?"
CREATE INDEX idx_events_entidad ON events_aup(entidad, entidad_id, timestamp DESC);

-- Query: "¿Qué eventos tienen este resultado?"
CREATE INDEX idx_events_resultado ON events_aup(resultado, timestamp DESC);

-- Query: "¿Qué eventos de esta acción?"
CREATE INDEX idx_events_accion ON events_aup(accion, timestamp DESC);

-- Query: "¿Eventos en rango de tiempo?"
CREATE INDEX idx_events_timestamp ON events_aup(timestamp DESC);

-- Query: "¿Qué hizo este usuario en este tenant?" (compuesto)
CREATE INDEX idx_events_identity_tenant ON events_aup(identity_id, tenant_id, timestamp DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- Comentarios de Documentación
-- ═══════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE events_aup IS 
'Entidad estructural universal que declara que un HECHO ocurrió dentro del sistema.
AUP_EVENT NO es logging técnico. ES una entidad de dominio inmutable que declara existencia en el tiempo.
Axiomas: toda acción relevante genera evento, sin identidad/tenant es inválido, inmutable, reconstruible.';

COMMENT ON COLUMN events_aup.event_id IS 'Identificador único del evento (evt_abc123...)';
COMMENT ON COLUMN events_aup.identity_id IS 'AUP_IDENTITY: Quién actúa (FK a usuarios_exo)';
COMMENT ON COLUMN events_aup.session_hash IS 'Hash SHA-256 del JWT (contexto temporal sin exponer token)';
COMMENT ON COLUMN events_aup.scope_id IS 'AUP_SCOPE: Alcance sobre tenant (NULL en login)';
COMMENT ON COLUMN events_aup.tenant_id IS 'AUP_TENANT: Dónde ocurre (FK a condominios_exo)';
COMMENT ON COLUMN events_aup.entidad IS 'Tipo de entidad afectada (visita, qr, evidencia, usuario, etc.)';
COMMENT ON COLUMN events_aup.entidad_id IS 'ID específico de la entidad afectada';
COMMENT ON COLUMN events_aup.accion IS 'Acción ejecutada (crear, validar, registrar, revocar, denegar, etc.)';
COMMENT ON COLUMN events_aup.resultado IS 'Resultado de la acción (permitido, denegado, error, exito, fallo)';
COMMENT ON COLUMN events_aup.motivo IS 'Razón estructural del resultado (por qué ocurrió o falló)';
COMMENT ON COLUMN events_aup.timestamp IS 'Timestamp inmutable del evento';
COMMENT ON COLUMN events_aup.hash_evento IS 'Hash SHA-256 de campos críticos para verificar inmutabilidad';
COMMENT ON COLUMN events_aup.metadata IS 'Contexto adicional estructurado (JSONB)';

-- ═══════════════════════════════════════════════════════════════════════════
-- Fin de Migración
-- ═══════════════════════════════════════════════════════════════════════════
