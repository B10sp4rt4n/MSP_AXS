-- ONLY Development br-blue-frog-b5o2ccsk; four new synthetic fixture photos.
-- Guarded test clock change, not a product API or production migration.
DO $$ DECLARE n integer; BEGIN
 UPDATE evidencias SET created_at=(now() AT TIME ZONE 'UTC')-interval '31 days'
 WHERE evidencia_id IN ('76fed74a-13d1-4224-b5f1-ffccb6995c4a','cf44bc92-558a-47a8-8ec7-3c98592aa76a','96402bd4-cb63-49ca-bfdf-5d630e093d32','a591d91b-f663-4387-8963-77aff1ca5e1a') AND visita_id IN ('VIS-4e27d34dc2','VIS-ca466ea1a5') AND hash_sha256='5d4f9493923a4d6269234e24c7b591df4f65fe00313ccccbddd95ecf00e23bab'
 AND metadata_json->>'nombre'='AXS documento ficticio - prueba automatica' AND metadata_json->>'captura_id' IN ('488784ee-fd19-474a-8999-4b3ed4a1862d','edc7841b-79ec-4d60-b760-d4138cd77898');
 GET DIAGNOSTICS n=ROW_COUNT; IF n!=4 THEN RAISE EXCEPTION 'Synthetic photo clock guard failed'; END IF;
 UPDATE identity_retention SET captured_at=(now() AT TIME ZONE 'UTC')-interval '31 days',base_at=(now() AT TIME ZONE 'UTC')-interval '31 days',
 expires_at=(now() AT TIME ZONE 'UTC')-interval '1 day',next_attempt_at=(now() AT TIME ZONE 'UTC')-interval '1 day'
 WHERE visita_id IN ('VIS-4e27d34dc2','VIS-ca466ea1a5') AND captura_id IN ('488784ee-fd19-474a-8999-4b3ed4a1862d','edc7841b-79ec-4d60-b760-d4138cd77898') AND policy_version='30d-dev-synthetic-v1' AND state='active';
 GET DIAGNOSTICS n=ROW_COUNT; IF n!=2 THEN RAISE EXCEPTION 'Synthetic pair clock guard failed'; END IF;
 END $$;
