-- ONLY project patient-tree-68362559 / branch br-blue-frog-b5o2ccsk / neondb.
-- Execute in ONE transaction. Fresh fixture only: uniqueness failures must abort.
INSERT INTO msps_exo(msp_id,nombre) VALUES ('lab261009_cycles_v1_msp','Synthetic contract cycles MSP');
INSERT INTO condominios_exo(condominio_id,msp_id,nombre) VALUES
 ('lab261009_cycles_v1_condo',NULL,'Synthetic contract cycles'),
 ('lab261009_cycles_v1_control',NULL,'Synthetic scope isolation control');
INSERT INTO usuarios(usuario_id,condominio_id,nombre,email,rol,creado) VALUES
 ('lab261009_cycles_v1_operator',NULL,'Synthetic cycles operator','cycles-operator@example.invalid','MSP_ADMIN',now()),
 ('lab261009_cycles_v1_guard','lab261009_cycles_v1_condo','Synthetic cycles guard','cycles-guard@example.invalid','GUARDIA',now()),
 ('lab261009_cycles_v1_stale','lab261009_cycles_v1_condo','Synthetic stale guard','cycles-stale@example.invalid','GUARDIA',now()),
 ('lab261009_cycles_v1_local','lab261009_cycles_v1_condo','Synthetic local admin','cycles-local@example.invalid','ADMIN_CONDOMINIO',now());
INSERT INTO user_tenant_scope(usuario_id,tenant_id,access_level,estado,created_at,metadata_json) VALUES
 ('lab261009_cycles_v1_local','lab261009_cycles_v1_condo','ADMIN_CONDOMINIO','ACTIVO',now(),'{"grant_origin":{"kind":"condominio","evidence_ref":"lab261009_cycles_v1/local"}}'),
 ('lab261009_cycles_v1_guard','lab261009_cycles_v1_control','GUARDIA','ACTIVO',now(),'{"grant_origin":{"kind":"condominio","evidence_ref":"lab261009_cycles_v1/control"}}');
SELECT set_config('app.tenant_id','lab261009_cycles_v1_condo',true);
INSERT INTO visitas(visita_id,condominio_id,nombre_visitante,estado,tipo_visita,created_at) VALUES
 ('lab261009_cycles_v1_visit','lab261009_cycles_v1_condo','Synthetic historical visit','cancelada','eventual',now());
INSERT INTO evidencias(evidencia_id,visita_id,categoria,archivo_url,hash_sha256,guardia_id,created_at) VALUES
 ('lab261009_cycles_v1_evidence','lab261009_cycles_v1_visit','synthetic','https://example.invalid/synthetic-evidence',repeat('a',64),'lab261009_cycles_v1_guard',now());
