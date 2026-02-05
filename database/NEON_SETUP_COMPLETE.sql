-- ═══════════════════════════════════════════════════════════════
-- SCRIPTS SQL PARA NEON - MSP_AXS AUP SYSTEM
-- ═══════════════════════════════════════════════════════════════
-- Fecha: 2026-01-07
-- Sistema: Multi-tenant Access Management
-- Arquitectura: AUP (Architecture from Unified Principles)
-- ═══════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════
-- INSTRUCCIONES DE USO
-- ═══════════════════════════════════════════════════════════════
-- 1. Crear 3 bases de datos en Neon:
--    - aup_core   (identidades, scopes, datos de negocio)
--    - aup_event  (auditoria, trazabilidad)
--    - aup_gov    (gobierno, políticas, límites)
--
-- 2. Ejecutar secciones correspondientes:
--    - SECCIÓN 1 → En base de datos aup_core
--    - SECCIÓN 2 → En base de datos aup_event
--    - SECCIÓN 3 → En base de datos aup_gov
--
-- 3. Tiempo estimado: 5-10 minutos
-- ═══════════════════════════════════════════════════════════════


-- ═══════════════════════════════════════════════════════════════
-- SECCIÓN 1: BASE DE DATOS aup_core
-- ═══════════════════════════════════════════════════════════════
-- IMPORTANTE: Ejecutar SOLO en base de datos "aup_core"
-- ═══════════════════════════════════════════════════════════════

-- Tabla MSPs (Proveedores de Servicio)
CREATE TABLE IF NOT EXISTS msps (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla Usuarios (AUP_IDENTITY - Identidades del sistema)
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(50),  -- DEPRECADO - usar user_tenant_scopes
    msp_id INTEGER REFERENCES msps(id),
    tenant_id VARCHAR(255),
    telefono VARCHAR(50),
    direccion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para usuarios
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_msp ON usuarios(msp_id);

-- Tabla Condominios (AUP_TENANT - Tenants del sistema)
CREATE TABLE IF NOT EXISTS condominios (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    direccion TEXT,
    telefono VARCHAR(50),
    msp_id INTEGER REFERENCES msps(id),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para condominios
CREATE INDEX IF NOT EXISTS idx_condominios_tenant ON condominios(tenant_id);
CREATE INDEX IF NOT EXISTS idx_condominios_msp ON condominios(msp_id);

-- Tabla Scopes (AUP_SCOPE - CRÍTICA PARA MULTI-TENANT)
-- Define DÓNDE una identidad puede actuar
CREATE TABLE IF NOT EXISTS user_tenant_scopes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    access_level VARCHAR(50) NOT NULL,  -- 'msp_admin', 'admin_condominio', 'guardia', 'residente', 'lectura'
    status VARCHAR(20) DEFAULT 'activo',  -- 'activo', 'inactivo', 'suspendido', 'revocado'
    granted_by_id INTEGER REFERENCES usuarios(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, tenant_id)
);

-- Índices para scopes (performance crítica)
CREATE INDEX IF NOT EXISTS idx_scopes_usuario ON user_tenant_scopes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_scopes_tenant ON user_tenant_scopes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_scopes_status ON user_tenant_scopes(status);
CREATE INDEX IF NOT EXISTS idx_scopes_access_level ON user_tenant_scopes(access_level);

-- Tabla Casetas (infraestructura operativa)
CREATE TABLE IF NOT EXISTS casetas (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    ubicacion VARCHAR(255),
    activa BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_casetas_tenant ON casetas(tenant_id);

-- Tabla Visitas (entidad de negocio multi-tenant)
CREATE TABLE IF NOT EXISTS visitas (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    visitante_nombre VARCHAR(255) NOT NULL,
    visitante_identificacion VARCHAR(100),
    visitante_foto_url VARCHAR(500),
    residente_id INTEGER REFERENCES usuarios(id),
    caseta_id INTEGER REFERENCES casetas(id),
    fecha_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_salida TIMESTAMP,
    motivo TEXT,
    autorizado_por_id INTEGER REFERENCES usuarios(id),
    qr_code VARCHAR(500),
    status VARCHAR(50) DEFAULT 'pendiente',  -- 'pendiente', 'activa', 'finalizada', 'cancelada'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para visitas
CREATE INDEX IF NOT EXISTS idx_visitas_tenant ON visitas(tenant_id);
CREATE INDEX IF NOT EXISTS idx_visitas_residente ON visitas(residente_id);
CREATE INDEX IF NOT EXISTS idx_visitas_fecha ON visitas(fecha_entrada);
CREATE INDEX IF NOT EXISTS idx_visitas_status ON visitas(status);

-- Tabla Evidencias (artefactos multimedia)
CREATE TABLE IF NOT EXISTS evidencias (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,  -- 'foto', 'video', 'documento'
    descripcion TEXT,
    file_url VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes INTEGER,
    visita_id INTEGER REFERENCES visitas(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidencias_tenant ON evidencias(tenant_id);
CREATE INDEX IF NOT EXISTS idx_evidencias_visita ON evidencias(visita_id);

-- ═══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS) - CRÍTICO PARA AISLAMIENTO
-- ═══════════════════════════════════════════════════════════════

-- Habilitar RLS en tablas multi-tenant
ALTER TABLE visitas ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE casetas ENABLE ROW LEVEL SECURITY;

-- Política RLS: Solo ver datos del propio tenant
CREATE POLICY tenant_isolation_visitas ON visitas
    USING (tenant_id = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation_evidencias ON evidencias
    USING (tenant_id = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation_casetas ON casetas
    USING (tenant_id = current_setting('app.tenant_id', TRUE));

-- Política para bypass (admin MSP o tests)
CREATE POLICY tenant_bypass_visitas ON visitas
    USING (
        current_setting('app.bypass_rls', TRUE)::boolean = true
        OR current_user = 'postgres'
    );

CREATE POLICY tenant_bypass_evidencias ON evidencias
    USING (
        current_setting('app.bypass_rls', TRUE)::boolean = true
        OR current_user = 'postgres'
    );

CREATE POLICY tenant_bypass_casetas ON casetas
    USING (
        current_setting('app.bypass_rls', TRUE)::boolean = true
        OR current_user = 'postgres'
    );

-- ═══════════════════════════════════════════════════════════════
-- DATOS BOOTSTRAP aup_core
-- ═══════════════════════════════════════════════════════════════

-- MSP principal
INSERT INTO msps (nombre, descripcion) 
VALUES ('MSP_AXS', 'Multi-tenant Security Platform - Access Control System')
ON CONFLICT (nombre) DO NOTHING;

-- Usuario administrador del sistema
INSERT INTO usuarios (nombre, email, password_hash, rol, msp_id)
VALUES (
    'Admin Sistema',
    'admin@msp-axs.com',
    '$2b$12$KIX8qhkGpZ.rYvhvhJq5ZObO.wqJZGv4YQyNZPJYQp5vZPJYQp5vZ',  -- password: Admin2026!
    'msp_admin',
    (SELECT id FROM msps WHERE nombre = 'MSP_AXS')
)
ON CONFLICT (email) DO NOTHING;

-- NOTA: Cambiar password en producción con bcrypt


-- ═══════════════════════════════════════════════════════════════
-- SECCIÓN 2: BASE DE DATOS aup_event
-- ═══════════════════════════════════════════════════════════════
-- IMPORTANTE: Ejecutar SOLO en base de datos "aup_event"
-- ═══════════════════════════════════════════════════════════════

-- Tabla de eventos para auditoria
CREATE TABLE IF NOT EXISTS events_aup (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,  -- 'identity.login', 'scope.grant', 'data.access'
    identity_id INTEGER NOT NULL,  -- Usuario que ejecutó la acción
    tenant_id VARCHAR(255),  -- Tenant en el que ocurrió
    resource_type VARCHAR(100),  -- 'visita', 'usuario', 'scope'
    resource_id VARCHAR(255),
    action VARCHAR(50) NOT NULL,  -- 'create', 'read', 'update', 'delete'
    outcome VARCHAR(20) NOT NULL,  -- 'success', 'failure', 'denied'
    metadata JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    hash_chain VARCHAR(64),  -- SHA-256 del evento anterior + este evento
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsqueda de eventos
CREATE INDEX IF NOT EXISTS idx_events_identity ON events_aup(identity_id);
CREATE INDEX IF NOT EXISTS idx_events_tenant ON events_aup(tenant_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events_aup(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events_aup(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_events_outcome ON events_aup(outcome);

-- Vista para eventos de seguridad críticos
CREATE OR REPLACE VIEW security_events AS
SELECT 
    id,
    event_type,
    identity_id,
    tenant_id,
    action,
    outcome,
    event_timestamp
FROM events_aup
WHERE 
    event_type IN ('identity.login', 'scope.grant', 'scope.revoke', 'access.denied')
    OR outcome = 'denied'
ORDER BY event_timestamp DESC;


-- ═══════════════════════════════════════════════════════════════
-- SECCIÓN 3: BASE DE DATOS aup_gov
-- ═══════════════════════════════════════════════════════════════
-- IMPORTANTE: Ejecutar SOLO en base de datos "aup_gov"
-- ═══════════════════════════════════════════════════════════════

-- Tabla de planes comerciales
CREATE TABLE IF NOT EXISTS planes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    precio_mensual DECIMAL(10,2),
    max_usuarios INTEGER,
    max_visitas_mes INTEGER,
    max_condominios INTEGER,
    caracteristicas JSONB,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de límites de uso por tenant
CREATE TABLE IF NOT EXISTS tenant_limits (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL UNIQUE,
    plan_id INTEGER REFERENCES planes(id),
    usuarios_actuales INTEGER DEFAULT 0,
    visitas_mes_actual INTEGER DEFAULT 0,
    storage_mb_usado DECIMAL(10,2) DEFAULT 0,
    ultimo_reset_mensual TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_limits_tenant ON tenant_limits(tenant_id);

-- Tabla de políticas de gobierno
CREATE TABLE IF NOT EXISTS policies (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL,  -- 'rate_limit', 'access_control', 'data_retention'
    reglas JSONB NOT NULL,
    scope VARCHAR(50),  -- 'global', 'msp', 'tenant'
    scope_id VARCHAR(255),
    activo BOOLEAN DEFAULT true,
    prioridad INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_policies_tipo ON policies(tipo);
CREATE INDEX IF NOT EXISTS idx_policies_scope ON policies(scope, scope_id);

-- ═══════════════════════════════════════════════════════════════
-- DATOS BOOTSTRAP aup_gov
-- ═══════════════════════════════════════════════════════════════

-- Plan Free por defecto
INSERT INTO planes (
    nombre, 
    descripcion, 
    precio_mensual, 
    max_usuarios, 
    max_visitas_mes, 
    max_condominios,
    caracteristicas
) VALUES (
    'Free',
    'Plan gratuito con limitaciones básicas',
    0.00,
    10,
    100,
    1,
    '{"features": ["visitas_basicas", "qr_codes", "reportes_basicos"]}'::jsonb
)
ON CONFLICT (nombre) DO NOTHING;

-- Plan Pro
INSERT INTO planes (
    nombre, 
    descripcion, 
    precio_mensual, 
    max_usuarios, 
    max_visitas_mes, 
    max_condominios,
    caracteristicas
) VALUES (
    'Pro',
    'Plan profesional para condominios medianos',
    99.00,
    50,
    1000,
    5,
    '{"features": ["visitas_avanzadas", "qr_codes", "reportes_avanzados", "integraciones", "soporte_prioritario"]}'::jsonb
)
ON CONFLICT (nombre) DO NOTHING;


-- ═══════════════════════════════════════════════════════════════
-- FIN DEL SCRIPT
-- ═══════════════════════════════════════════════════════════════

-- Verificación post-ejecución:
-- SELECT COUNT(*) FROM usuarios;       -- Debe ser > 0 (admin creado)
-- SELECT COUNT(*) FROM events_aup;     -- Puede ser 0 (se llena en uso)
-- SELECT COUNT(*) FROM planes;         -- Debe ser >= 2 (Free y Pro)
