-- AUP_EVENT: preservar los insumos de la huella para eventos nuevos.
-- Aplicar en EVENT antes de desplegar el código; no backfill de valores
-- históricos que nunca fueron persistidos.
ALTER TABLE events_aup ADD COLUMN IF NOT EXISTS event_uid VARCHAR NULL;
ALTER TABLE events_aup ADD COLUMN IF NOT EXISTS session_hash VARCHAR NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_events_aup_event_uid ON events_aup(event_uid);
-- El verificador devuelve false para filas históricas sin estos campos.
