-- CORE. Aplicar antes de desplegar el código; no habilita restricciones.
BEGIN;
ALTER TABLE condominios_exo ADD COLUMN IF NOT EXISTS reglas_acceso JSON;
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS proposito TEXT;
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS autorizada_por VARCHAR REFERENCES usuarios(usuario_id);
ALTER TABLE visitas ADD COLUMN IF NOT EXISTS autorizada_en TIMESTAMP;
COMMIT;
