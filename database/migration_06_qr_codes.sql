-- ═══════════════════════════════════════════════════════════════════════════
-- Migración: QR_CODES - Códigos alfanuméricos para compartir acceso
-- ═══════════════════════════════════════════════════════════════════════════
-- Fecha: 2026-02-01
-- Propósito: Permitir compartir QR por WhatsApp/SMS/Email usando códigos
-- ═══════════════════════════════════════════════════════════════════════════

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- Tabla: qr_codes
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS qr_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Código alfanumérico (ej: V-260201-123)
    codigo TEXT NOT NULL UNIQUE,
    
    -- Referencias
    visita_id TEXT NOT NULL,
    condominio_id TEXT NOT NULL,
    
    -- Vigencia
    vigencia_desde TEXT NOT NULL DEFAULT (datetime('now')),
    vigencia_hasta TEXT NOT NULL,
    
    -- Estado de uso
    usado INTEGER NOT NULL DEFAULT 0,  -- 0=no usado, 1=usado
    usado_en TEXT,  -- Timestamp cuando fue usado
    
    -- Auditoría de compartición
    compartido_via TEXT,  -- whatsapp, sms, email, pantalla
    compartido_a TEXT,    -- Teléfono o email destinatario
    compartido_por TEXT,  -- usuario_id del guardia/admin que compartió
    compartido_en TEXT,   -- Timestamp cuando se compartió
    
    -- Metadata adicional (JSON)
    metadata_json TEXT,
    
    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Foreign Keys
    FOREIGN KEY (visita_id) REFERENCES visitas(visita_id) ON DELETE CASCADE,
    FOREIGN KEY (condominio_id) REFERENCES condominios_exo(condominio_id) ON DELETE CASCADE,
    FOREIGN KEY (compartido_por) REFERENCES usuarios(usuario_id) ON DELETE SET NULL
);

-- ═══════════════════════════════════════════════════════════════════════════
-- Índices para optimización
-- ═══════════════════════════════════════════════════════════════════════════

-- Búsqueda rápida por código
CREATE UNIQUE INDEX IF NOT EXISTS idx_qrcode_codigo ON qr_codes(codigo);

-- Búsqueda por visita (un QR puede tener múltiples códigos)
CREATE INDEX IF NOT EXISTS idx_qrcode_visita ON qr_codes(visita_id);

-- Búsqueda por vigencia (cleanup de códigos expirados)
CREATE INDEX IF NOT EXISTS idx_qrcode_vigencia ON qr_codes(vigencia_hasta);

-- Búsqueda por estado de uso
CREATE INDEX IF NOT EXISTS idx_qrcode_usado ON qr_codes(usado);

-- Búsqueda por condominio (reporte de códigos activos por tenant)
CREATE INDEX IF NOT EXISTS idx_qrcode_condominio ON qr_codes(condominio_id);

-- Búsqueda compuesta: códigos activos no usados
CREATE INDEX IF NOT EXISTS idx_qrcode_activos ON qr_codes(usado, vigencia_hasta)
    WHERE usado = 0;

-- ═══════════════════════════════════════════════════════════════════════════
-- Datos de prueba (opcional - comentar en producción)
-- ═══════════════════════════════════════════════════════════════════════════

-- Ejemplo: Código para visita existente
-- INSERT INTO qr_codes (codigo, visita_id, condominio_id, vigencia_hasta, compartido_via, compartido_a)
-- VALUES (
--     'V-260201-001',
--     'vis_123',
--     'condo_001',
--     datetime('now', '+8 hours'),
--     'whatsapp',
--     '+34666777888'
-- );

-- ═══════════════════════════════════════════════════════════════════════════
-- Validaciones
-- ═══════════════════════════════════════════════════════════════════════════

-- Verificar que la tabla se creó correctamente
SELECT name, type FROM sqlite_master WHERE type='table' AND name='qr_codes';

-- Verificar índices
SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='qr_codes';

-- Contar registros
SELECT COUNT(*) as total_qr_codes FROM qr_codes;

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════
-- Rollback (en caso de error)
-- ═══════════════════════════════════════════════════════════════════════════
-- DROP TABLE IF EXISTS qr_codes;
