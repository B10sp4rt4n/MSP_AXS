-- CORE (neondb): apply as migration owner, never as the runtime role.
CREATE TABLE IF NOT EXISTS public.recovery_checkpoints (
    incident_id VARCHAR PRIMARY KEY,
    phase VARCHAR NOT NULL,
    release_nonce VARCHAR,
    report JSON NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);
GRANT SELECT ON public.recovery_checkpoints TO axs_core_app;
