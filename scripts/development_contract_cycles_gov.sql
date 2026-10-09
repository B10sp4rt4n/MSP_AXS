-- ONLY project patient-tree-68362559 / branch br-blue-frog-b5o2ccsk / aup_gov.
-- Temporary synthetic operator. Revoke after execution with the cleanup statement in the runbook.
INSERT INTO authorities_gov(authority_id,identity_id,tipo,estado,created_at,metadata_json) VALUES
 ('lab261009_cycles_v1_authority','lab261009_cycles_v1_operator','GLOBAL','ACTIVO',now(),'{"synthetic":true,"run":"lab261009_cycles_v1"}');
