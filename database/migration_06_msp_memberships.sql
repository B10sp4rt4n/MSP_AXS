-- Fase 1: membresía explícita de administradores MSP en AUP_CORE.
-- Ejecutar solo después de verificar que CORE contiene usuarios y msps_exo
-- con la estructura del ORM. No asignar permisos a partir de rol/msp_id legado.
CREATE TABLE IF NOT EXISTS msp_memberships (
    id SERIAL PRIMARY KEY,
    usuario_id VARCHAR NOT NULL REFERENCES usuarios(usuario_id),
    msp_id VARCHAR NOT NULL REFERENCES msps_exo(msp_id),
    estado VARCHAR NOT NULL DEFAULT 'activo'
        CHECK (estado IN ('activo', 'revocado')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP NULL,
    CONSTRAINT uq_msp_membership UNIQUE (usuario_id, msp_id)
);
CREATE INDEX IF NOT EXISTS ix_msp_memberships_usuario_id ON msp_memberships(usuario_id);
CREATE INDEX IF NOT EXISTS ix_msp_memberships_msp_id ON msp_memberships(msp_id);

-- La asignación inicial debe ser una lista revisada de pares (usuario_id, msp_id)
-- y la autoridad GLOBAL del operador debe verificarse en AUP_GOV.
-- No incluye INSERT ni cambios en producción.
