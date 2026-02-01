-- =========================================================================
-- MIGRACIÓN: Extender tabla visitas para Modo Guardia
-- =========================================================================
-- OBJETIVO: Agregar campos para visitas creadas in-situ por guardia
--
-- NUEVOS CAMPOS:
-- - telefono: Teléfono del visitante
-- - residente_anfitrion: Nombre del residente anfitrión
-- - motivo: Motivo de la visita
-- - placa_vehiculo: Placa del vehículo
-- - hora_entrada: Timestamp de entrada registrada
-- - hora_salida: Timestamp de salida registrada
-- - creada_por: ID del usuario (guardia) que creó la visita
-- - tipo_visitante: Cambiar nombre de tipo_visita
--
-- ESTADO: Agregar nuevo valor "creada_sin_qr"
-- =========================================================================

-- 1. Agregar nuevos campos a la tabla visitas
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS telefono VARCHAR(15);
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS residente_anfitrion VARCHAR(100);
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS motivo VARCHAR(200);
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS placa_vehiculo VARCHAR(20);
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS hora_entrada TIMESTAMP;
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS hora_salida TIMESTAMP;
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS creada_por VARCHAR(50);

-- 2. Renombrar tipo_visita a tipo_visitante (si existe)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='visitas' AND column_name='tipo_visita'
    ) THEN
        ALTER TABLE visitas RENAME COLUMN tipo_visita TO tipo_visitante;
    ELSE
        -- Si no existe, agregamos directamente tipo_visitante
        ALTER TABLE visitas ADD COLUMN IF NOT EXISTS tipo_visitante VARCHAR(50);
    END IF;
END $$;

-- 3. Modificar vigencia para permitir NULL (visitas sin QR previo)
ALTER TABLE visitas ALTER COLUMN vigencia DROP NOT NULL;

-- 4. Agregar FK para creada_por (referencia a usuarios.usuario_id)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_visita_creada_por'
    ) THEN
        ALTER TABLE visitas ADD CONSTRAINT fk_visita_creada_por 
            FOREIGN KEY (creada_por) REFERENCES usuarios(usuario_id) 
            ON DELETE SET NULL;
    END IF;
END $$;

-- 5. Actualizar valores existentes para tipo_visitante (si había tipo_visita)
UPDATE visitas SET tipo_visitante = 'eventual' WHERE tipo_visitante IS NULL;

-- 6. Crear índice para búsquedas por guardia creador
CREATE INDEX IF NOT EXISTS idx_visita_creada_por ON visitas(creada_por);

-- 7. Agregar comentarios
COMMENT ON COLUMN visitas.telefono IS 'Teléfono del visitante';
COMMENT ON COLUMN visitas.residente_anfitrion IS 'Nombre del residente anfitrión';
COMMENT ON COLUMN visitas.motivo IS 'Motivo de la visita';
COMMENT ON COLUMN visitas.placa_vehiculo IS 'Placa del vehículo del visitante';
COMMENT ON COLUMN visitas.hora_entrada IS 'Hora de entrada registrada por guardia';
COMMENT ON COLUMN visitas.hora_salida IS 'Hora de salida registrada por guardia';
COMMENT ON COLUMN visitas.creada_por IS 'ID del usuario guardia que creó la visita';
COMMENT ON COLUMN visitas.tipo_visitante IS 'Tipo: frecuente, eventual, proveedor, cliente, entrega, consulta, familia';

-- =========================================================================
-- VERIFICACIÓN
-- =========================================================================
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'visitas'
ORDER BY ordinal_position;
