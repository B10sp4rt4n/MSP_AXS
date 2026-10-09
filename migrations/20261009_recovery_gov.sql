-- GOV (aup_gov): apply as migration owner. Existing GOV owner retains access.
CREATE TABLE IF NOT EXISTS public.recovery_gov_checkpoints (
    incident_id VARCHAR PRIMARY KEY,
    phase VARCHAR NOT NULL,
    release_nonce VARCHAR
);
