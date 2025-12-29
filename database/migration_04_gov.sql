-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN: PASO 4 - AUP_GOV (Gobierno de Plataforma)
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- Crea tablas para AUP_AUTHORITY, AUP_POLICY y AUP_DELEGATION.
--
-- Ejecutar DESPUÉS de:
--   - database/schema_axs.sql (tablas base)
--   - PASO 2 (user_tenant_scope)
--   - PASO 3 (events_aup)
--
-- ═══════════════════════════════════════════════════════════════════════════

-- Tabla de Autoridades de Gobierno (AUP_AUTHORITY)
CREATE TABLE IF NOT EXISTS authorities_gov (
    -- Identificador único
    authority_id VARCHAR(255) PRIMARY KEY,
    
    -- AUP_IDENTITY que tiene la autoridad
    identity_id VARCHAR(255) NOT NULL,
    
    -- Tipo de autoridad (global | first_tier)
    tipo VARCHAR(50) NOT NULL,
    
    -- Tenant sobre el que tiene autoridad (NULL si GLOBAL)
    tenant_id VARCHAR(255),
    
    -- Estado (activo | suspendido | revocado)
    estado VARCHAR(50) NOT NULL DEFAULT 'activo',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    
    -- Metadata adicional (JSON)
    metadata JSONB,
    
    -- Foreign Keys
    FOREIGN KEY (identity_id) REFERENCES usuarios_exo(usuario_id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES condominios_exo(condominio_id) ON DELETE CASCADE
);

-- Índices para authorities
CREATE INDEX idx_authority_identity ON authorities_gov(identity_id, estado);
CREATE INDEX idx_authority_tenant ON authorities_gov(tenant_id, estado);
CREATE INDEX idx_authority_tipo ON authorities_gov(tipo, estado);

-- ═══════════════════════════════════════════════════════════════════════════

-- Tabla de Políticas de Gobierno (AUP_POLICY)
CREATE TABLE IF NOT EXISTS policies_gov (
    -- Identificador único
    policy_id VARCHAR(255) PRIMARY KEY,
    
    -- Nombre declarativo
    nombre VARCHAR(255) NOT NULL,
    
    -- Ámbito de aplicación (global | tenant | scope)
    ambito VARCHAR(50) NOT NULL,
    
    -- Tenant objetivo (NULL si GLOBAL)
    target_tenant_id VARCHAR(255),
    
    -- Acción que gobierna (crear_tenant, asignar_scope, generar_qr, etc.)
    accion_objetivo VARCHAR(100) NOT NULL,
    
    -- Límites estructurales (JSON)
    -- Ejemplos: {"max_count": 10}, {"max_dias_vigencia": 7}
    limites JSONB NOT NULL,
    
    -- Vigencia
    valida_desde TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valida_hasta TIMESTAMP,
    
    -- Estado (activo | suspendido | revocado)
    estado VARCHAR(50) NOT NULL DEFAULT 'activo',
    
    -- Metadata adicional (JSON)
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (target_tenant_id) REFERENCES condominios_exo(condominio_id) ON DELETE CASCADE
);

-- Índices para policies
CREATE INDEX idx_policy_ambito ON policies_gov(ambito, accion_objetivo, estado);
CREATE INDEX idx_policy_tenant ON policies_gov(target_tenant_id, estado);
CREATE INDEX idx_policy_accion ON policies_gov(accion_objetivo, estado);
CREATE INDEX idx_policy_vigencia ON policies_gov(valida_desde, valida_hasta);

-- ═══════════════════════════════════════════════════════════════════════════

-- Tabla de Delegaciones de Poder (AUP_DELEGATION)
CREATE TABLE IF NOT EXISTS delegations_gov (
    -- Identificador único
    delegation_id VARCHAR(255) PRIMARY KEY,
    
    -- AUP_AUTHORITY que delega
    authority_id VARCHAR(255) NOT NULL,
    
    -- A QUIÉN se delega (mutuamente excluyente)
    target_identity_id VARCHAR(255),
    target_scope_id VARCHAR(255),
    
    -- QUÉ se delega (array de permisos)
    permisos_delegados JSONB NOT NULL,
    
    -- Vigencia
    valida_desde TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valida_hasta TIMESTAMP,
    
    -- Estado (activo | suspendido | revocado)
    estado VARCHAR(50) NOT NULL DEFAULT 'activo',
    
    -- Metadata adicional (JSON)
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (authority_id) REFERENCES authorities_gov(authority_id) ON DELETE CASCADE,
    FOREIGN KEY (target_identity_id) REFERENCES usuarios_exo(usuario_id) ON DELETE CASCADE,
    FOREIGN KEY (target_scope_id) REFERENCES user_tenant_scope(id) ON DELETE CASCADE,
    
    -- Constraint: target_identity_id O target_scope_id (no ambos)
    CHECK (
        (target_identity_id IS NOT NULL AND target_scope_id IS NULL) OR
        (target_identity_id IS NULL AND target_scope_id IS NOT NULL)
    )
);

-- Índices para delegations
CREATE INDEX idx_delegation_authority ON delegations_gov(authority_id, estado);
CREATE INDEX idx_delegation_target_identity ON delegations_gov(target_identity_id, estado);
CREATE INDEX idx_delegation_target_scope ON delegations_gov(target_scope_id, estado);
CREATE INDEX idx_delegation_vigencia ON delegations_gov(valida_desde, valida_hasta);

-- ═══════════════════════════════════════════════════════════════════════════
-- Comentarios de Documentación
-- ═══════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE authorities_gov IS 
'AUP_AUTHORITY: Actor con potestad declarada para gobernar.
Axioma: Solo AUP_AUTHORITY puede crear o delegar poder.
Tipos: GLOBAL (plataforma) o FIRST_TIER (tenant específico).';

COMMENT ON TABLE policies_gov IS 
'AUP_POLICY: Regla declarativa que gobierna límites y delegaciones.
Axioma: La política precede a la operación (policy-first).
Ámbitos: GLOBAL (plataforma), TENANT (tenant específico), SCOPE (scopes con nivel).';

COMMENT ON TABLE delegations_gov IS 
'AUP_DELEGATION: Relación que transfiere poder desde autoridad a identidades/scopes.
Axiomas: Todo poder delegado es explícito, acotado y revocable.';

COMMENT ON COLUMN authorities_gov.tipo IS 'Tipo de autoridad: global (plataforma) o first_tier (tenant)';
COMMENT ON COLUMN authorities_gov.tenant_id IS 'Tenant sobre el que tiene autoridad (NULL si GLOBAL)';
COMMENT ON COLUMN authorities_gov.estado IS 'Estado: activo | suspendido | revocado';

COMMENT ON COLUMN policies_gov.ambito IS 'Ámbito: global | tenant | scope';
COMMENT ON COLUMN policies_gov.accion_objetivo IS 'Acción que gobierna (crear_tenant, generar_qr, etc.)';
COMMENT ON COLUMN policies_gov.limites IS 'Límites estructurales JSON (max_count, max_dias_vigencia, etc.)';
COMMENT ON COLUMN policies_gov.valida_desde IS 'Inicio de vigencia de la política';
COMMENT ON COLUMN policies_gov.valida_hasta IS 'Fin de vigencia (NULL = sin fin)';

COMMENT ON COLUMN delegations_gov.permisos_delegados IS 'Array JSON de permisos delegados';
COMMENT ON COLUMN delegations_gov.target_identity_id IS 'Usuario que recibe delegación (mutuamente excluyente con target_scope_id)';
COMMENT ON COLUMN delegations_gov.target_scope_id IS 'Scope que recibe delegación (mutuamente excluyente con target_identity_id)';
COMMENT ON COLUMN delegations_gov.valida_desde IS 'Inicio de vigencia de la delegación';
COMMENT ON COLUMN delegations_gov.valida_hasta IS 'Fin de vigencia (NULL = sin fin, pero recomendado acotarlo)';

-- ═══════════════════════════════════════════════════════════════════════════
-- Fin de Migración
-- ═══════════════════════════════════════════════════════════════════════════
