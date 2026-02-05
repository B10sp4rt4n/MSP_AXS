-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN 05: Dominio Meta-Operativo v1.0 (CONGELADO)
-- ═══════════════════════════════════════════════════════════════════════════
-- Fecha: 1 de enero de 2026
-- Propósito: Crear tabla de relaciones Identity ↔ Tenant
-- Norma: ACTA_CONGELAMIENTO_META_OPERATIVO_v1.0.md
-- ═══════════════════════════════════════════════════════════════════════════

-- Tabla de asignaciones meta-operativas
CREATE TABLE IF NOT EXISTS identity_tenant_assignments (
    -- Identificación única
    assignment_id VARCHAR(64) PRIMARY KEY,
    
    -- Relación (QUÉ se asigna)
    identity_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    assignment_type VARCHAR(32) NOT NULL,
    
    -- Trazabilidad de creación (QUIÉN y CUÁNDO)
    assigned_by_identity_id VARCHAR(64) NOT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT now(),
    
    -- Trazabilidad de revocación
    revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_by_identity_id VARCHAR(64) NULL,
    revoked_at TIMESTAMP NULL,
    revocation_reason TEXT NULL,
    
    -- Claves foráneas
    CONSTRAINT fk_meta_identity 
        FOREIGN KEY (identity_id) 
        REFERENCES usuarios(usuario_id)
        ON DELETE RESTRICT,
    
    CONSTRAINT fk_meta_tenant 
        FOREIGN KEY (tenant_id) 
        REFERENCES condominios_exo(condominio_id)
        ON DELETE RESTRICT,
    
    CONSTRAINT fk_meta_assigned_by 
        FOREIGN KEY (assigned_by_identity_id) 
        REFERENCES usuarios(usuario_id)
        ON DELETE RESTRICT,
    
    CONSTRAINT fk_meta_revoked_by 
        FOREIGN KEY (revoked_by_identity_id) 
        REFERENCES usuarios(usuario_id)
        ON DELETE RESTRICT,
    
    -- Invariante: Una identity solo puede tener UNA asignación activa por tenant
    CONSTRAINT uq_meta_active_assignment 
        UNIQUE (identity_id, tenant_id)
        WHERE (revoked = false),
    
    -- Validaciones de estado
    CONSTRAINT chk_meta_revocation_fields
        CHECK (
            (revoked = false AND revoked_by_identity_id IS NULL AND revoked_at IS NULL)
            OR
            (revoked = true AND revoked_by_identity_id IS NOT NULL AND revoked_at IS NOT NULL)
        ),
    
    -- Validación de assignment_type
    CONSTRAINT chk_meta_assignment_type
        CHECK (assignment_type IN ('FIRST_TIER_ADMIN', 'REGULAR_ADMIN', 'OPERATOR'))
);

-- Índices para consultas meta-operativas
CREATE INDEX idx_meta_identity ON identity_tenant_assignments(identity_id);
CREATE INDEX idx_meta_tenant ON identity_tenant_assignments(tenant_id);
CREATE INDEX idx_meta_active ON identity_tenant_assignments(identity_id, tenant_id, revoked) 
    WHERE revoked = false;
CREATE INDEX idx_meta_assigned_by ON identity_tenant_assignments(assigned_by_identity_id);

-- Comentarios de documentación
COMMENT ON TABLE identity_tenant_assignments IS 
    'Dominio Meta-Operativo v1.0 (CONGELADO) - Relaciones Identity ↔ Tenant';

COMMENT ON COLUMN identity_tenant_assignments.assignment_id IS 
    'Identificador único de la asignación';

COMMENT ON COLUMN identity_tenant_assignments.identity_id IS 
    'Identidad que recibe la asignación (FK usuarios.usuario_id)';

COMMENT ON COLUMN identity_tenant_assignments.tenant_id IS 
    'Tenant sobre el cual aplica la asignación (FK condominios_exo.condominio_id)';

COMMENT ON COLUMN identity_tenant_assignments.assignment_type IS 
    'Tipo de asignación: FIRST_TIER_ADMIN | REGULAR_ADMIN | OPERATOR';

COMMENT ON COLUMN identity_tenant_assignments.assigned_by_identity_id IS 
    'Quién realizó la asignación (DEBE tener authority GLOBAL)';

COMMENT ON COLUMN identity_tenant_assignments.revoked IS 
    'Indica si la asignación fue revocada (inmutable una vez true)';

COMMENT ON CONSTRAINT uq_meta_active_assignment ON identity_tenant_assignments IS 
    'Invariante: Una identity solo puede tener UNA asignación activa por tenant';

-- ═══════════════════════════════════════════════════════════════════════════
-- ROLLBACK
-- ═══════════════════════════════════════════════════════════════════════════
-- Para revertir esta migración:
-- 
-- DROP TABLE IF EXISTS identity_tenant_assignments CASCADE;
-- ═══════════════════════════════════════════════════════════════════════════
