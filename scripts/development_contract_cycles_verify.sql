-- Read-only verification: development branch br-blue-frog-b5o2ccsk, neondb.
-- Execute these statements in one transaction (RLS tenant setting is local).
SELECT set_config('app.tenant_id','lab261009_cycles_v1_condo',true);
SELECT contract_id,version,msp_id,opened_by,closed_at,open_event_uid,close_event_uid,close_receipt
 FROM provider_contracts WHERE condominio_id='lab261009_cycles_v1_condo' ORDER BY version;
SELECT id,usuario_id,tenant_id,estado,revoked_at,metadata_json
 FROM user_tenant_scope WHERE tenant_id IN ('lab261009_cycles_v1_condo','lab261009_cycles_v1_control') ORDER BY id;
SELECT event_uid,payload,delivered_at,attempts,last_error
 FROM event_outbox WHERE condominio_id='lab261009_cycles_v1_condo' ORDER BY created_at,event_uid;
SELECT condominio_id,msp_id FROM condominios_exo
 WHERE condominio_id IN ('lab261009_cycles_v1_condo','lab261009_cycles_v1_control') ORDER BY condominio_id;
SELECT md5(row_to_json(v)::text) AS visit_digest FROM visitas v WHERE visita_id='lab261009_cycles_v1_visit';
SELECT md5(row_to_json(e)::text) AS evidence_digest FROM evidencias e WHERE evidencia_id='lab261009_cycles_v1_evidence';
