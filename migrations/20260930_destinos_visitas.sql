ALTER TABLE visitas
  ADD COLUMN IF NOT EXISTS destino_id varchar REFERENCES casas(casa_id),
  ADD COLUMN IF NOT EXISTS destino_tipo varchar,
  ADD COLUMN IF NOT EXISTS destino_motivo text;
INSERT INTO casas (casa_id, condominio_id, numero, tipo, created_at)
SELECT 'dest_' || md5(c.condominio_id || ':' || d.tipo), c.condominio_id, d.nombre, d.tipo, CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
FROM condominios_exo c CROSS JOIN (VALUES
('administracion','Administración'), ('mantenimiento','Mantenimiento'), ('area_comun','Área común')
) AS d(tipo,nombre)
WHERE NOT EXISTS (SELECT 1 FROM casas h WHERE h.condominio_id=c.condominio_id AND h.numero=d.nombre);
