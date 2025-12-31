-- ═══════════════════════════════════════════════════════════════════════════
-- AUP_EVENT: Migración de Verdad Histórica
-- ═══════════════════════════════════════════════════════════════════════════
-- Fecha: 2025-12-29
-- Base objetivo: aup_event
-- Responsabilidad: Registrar hechos inmutables con identidad y resultado
-- ═══════════════════════════════════════════════════════════════════════════

-- Tabla única: events_aup
-- Axiomas:
--   1. Append-only (solo INSERT, nunca UPDATE/DELETE)
--   2. Si no hay evento, no ocurrió para el sistema
--   3. Hash de inmutabilidad para detectar manipulación
--   4. Estado del sistema se puede reconstruir desde eventos

CREATE TABLE IF NOT EXISTS events_aup (
    -- Identificación
    id SERIAL PRIMARY KEY,
    tipo_evento VARCHAR(100) NOT NULL,
    
    -- Contexto AUP (QUIÉN, DÓNDE, CÓMO)
    identity_id VARCHAR(50) NOT NULL,        -- AUP_IDENTITY que actúa
    session_hash VARCHAR(16) NOT NULL,       -- Hash del JWT (trazabilidad)
    scope_id VARCHAR(50),                    -- AUP_SCOPE (nullable en login)
    tenant_id VARCHAR(50) NOT NULL,          -- AUP_TENANT donde ocurre
    
    -- Declaración del Hecho (QUÉ, RESULTADO)
    entidad VARCHAR(50) NOT NULL,            -- visita, qr, evidencia, usuario, etc.
    entidad_id VARCHAR(100) NOT NULL,        -- ID específico de la entidad
    accion VARCHAR(50) NOT NULL,             -- crear, validar, denegar, revocar
    resultado VARCHAR(50) NOT NULL,          -- permitido, denegado, error, exito
    motivo TEXT,                             -- Razón estructural del resultado
    
    -- Metadatos y Trazabilidad
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    hash_evento VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 de campos críticos
    metadata_json JSONB                      -- Contexto adicional estructurado
);

-- ═══════════════════════════════════════════════════════════════════════════
-- ÍNDICES PARA QUERIES COMUNES
-- ═══════════════════════════════════════════════════════════════════════════

-- Query: "¿Qué hizo este usuario en este tenant?"
CREATE INDEX idx_events_identity_tenant 
ON events_aup(identity_id, tenant_id, timestamp DESC);

-- Query: "¿Qué eventos afectaron esta entidad?"
CREATE INDEX idx_events_entidad 
ON events_aup(entidad, entidad_id, timestamp DESC);

-- Query: "¿Qué eventos fallaron/fueron denegados?"
CREATE INDEX idx_events_resultado 
ON events_aup(resultado, timestamp DESC);

-- Query: "¿Qué tipo de eventos ocurrieron?"
CREATE INDEX idx_events_tipo 
ON events_aup(tipo_evento, timestamp DESC);

-- Query: "¿Qué eventos registró esta sesión?"
CREATE INDEX idx_events_session 
ON events_aup(session_hash, timestamp DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- COMENTARIOS ESTRUCTURALES
-- ═══════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE events_aup IS 
'AUP_EVENT: Registro inmutable de hechos estructurales. 
AXIOMAS: append-only, sin evento = no ocurrió, hash de inmutabilidad.';

COMMENT ON COLUMN events_aup.tipo_evento IS 
'Clasificación semántica del evento: sesion_iniciada, qr_generado, visita_creada, etc.';

COMMENT ON COLUMN events_aup.identity_id IS 
'UUID del usuario (AUP_IDENTITY) que ejecutó la acción';

COMMENT ON COLUMN events_aup.session_hash IS 
'Hash SHA-256 truncado del JWT para trazabilidad sin exponer token';

COMMENT ON COLUMN events_aup.scope_id IS 
'ID del scope activo (nullable en login y operaciones sin tenant)';

COMMENT ON COLUMN events_aup.tenant_id IS 
'UUID del tenant (condominio) donde ocurrió el evento';

COMMENT ON COLUMN events_aup.entidad IS 
'Tipo de entidad afectada: visita, qr, evidencia, usuario, condominio, scope, policy';

COMMENT ON COLUMN events_aup.entidad_id IS 
'ID específico de la entidad afectada';

COMMENT ON COLUMN events_aup.accion IS 
'Acción ejecutada: crear, validar, registrar, denegar, revocar, modificar';

COMMENT ON COLUMN events_aup.resultado IS 
'Resultado de la acción: permitido, denegado, error, exito, fallo';

COMMENT ON COLUMN events_aup.motivo IS 
'Razón estructural del resultado (ej: "QR vencido", "Scope inválido")';

COMMENT ON COLUMN events_aup.hash_evento IS 
'SHA-256 de campos críticos para verificar inmutabilidad';

COMMENT ON COLUMN events_aup.metadata_json IS 
'Contexto adicional estructurado (email, rol, plan, etc.)';

-- ═══════════════════════════════════════════════════════════════════════════
-- VALIDACIÓN DE INSERCIÓN
-- ═══════════════════════════════════════════════════════════════════════════

-- Ejemplo de evento válido:
-- INSERT INTO events_aup (
--     tipo_evento, identity_id, session_hash, tenant_id,
--     entidad, entidad_id, accion, resultado, hash_evento
-- ) VALUES (
--     'sesion_iniciada',
--     'usr_abc123',
--     'a1b2c3d4e5f6',
--     'condo_xyz',
--     'session',
--     'usr_abc123',
--     'login',
--     'exito',
--     'sha256_hash_here'
-- );
