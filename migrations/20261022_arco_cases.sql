-- Apply in an isolated branch and validate RLS before any production enablement.
-- The API remains disabled unless both feature flag and operator designations exist.
BEGIN;
CREATE TABLE IF NOT EXISTS public.arco_cases (
 case_id varchar(36) PRIMARY KEY,
 condominio_id varchar NOT NULL REFERENCES public.condominios_exo(condominio_id),
 received_at timestamp NOT NULL, determination_due timestamp NOT NULL,
 execution_due timestamp, "right" varchar(20) NOT NULL,
 subject_ref varchar(100) NOT NULL, owner_id varchar(100) NOT NULL,
 state varchar(20) NOT NULL, outcome varchar(20), version integer NOT NULL,
 pending_actions integer NOT NULL, history json NOT NULL,
 CONSTRAINT arco_state CHECK (state IN ('recibida','verificada','resuelta','ejecutando','cerrada')),
 CONSTRAINT arco_version CHECK (version > 0 AND pending_actions >= 0)
);
CREATE INDEX IF NOT EXISTS ix_arco_cases_condominio_id ON public.arco_cases(condominio_id);
ALTER TABLE public.arco_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.arco_cases FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS arco_cases_tenant ON public.arco_cases;
CREATE POLICY arco_cases_tenant ON public.arco_cases
 USING (condominio_id = current_setting('app.tenant_id',true))
 WITH CHECK (condominio_id = current_setting('app.tenant_id',true));
GRANT SELECT,INSERT,UPDATE ON public.arco_cases TO axs_core_app;
COMMIT;
