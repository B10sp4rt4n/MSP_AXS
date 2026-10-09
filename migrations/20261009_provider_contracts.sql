-- CORE migration owner: control-plane catalog like MSPMembership, never exposed directly.
CREATE TABLE IF NOT EXISTS public.provider_contracts (
    contract_id VARCHAR PRIMARY KEY,
    condominio_id VARCHAR NOT NULL REFERENCES public.condominios_exo(condominio_id),
    msp_id VARCHAR NOT NULL REFERENCES public.msps_exo(msp_id),
    version INTEGER NOT NULL,
    evidence_ref VARCHAR NOT NULL,
    opened_by VARCHAR NOT NULL,
    opened_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    closed_at TIMESTAMP WITHOUT TIME ZONE,
    open_event_uid VARCHAR NOT NULL,
    close_event_uid VARCHAR,
    close_receipt JSON,
    CONSTRAINT uq_provider_contract_version UNIQUE (condominio_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_contract_active
ON public.provider_contracts(condominio_id) WHERE closed_at IS NULL;
GRANT SELECT, INSERT, UPDATE ON public.provider_contracts TO axs_core_app;
