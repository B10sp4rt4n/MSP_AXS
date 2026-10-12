-- Additive migration. Test on an isolated development child before applying.
CREATE TABLE IF NOT EXISTS public.identity_retention (
 visita_id varchar PRIMARY KEY REFERENCES public.visitas(visita_id),
 condominio_id varchar NOT NULL REFERENCES public.condominios_exo(condominio_id),
 captura_id varchar NOT NULL, policy_version varchar NOT NULL,
 captured_at timestamp NOT NULL, base_at timestamp NOT NULL, expires_at timestamp NOT NULL,
 state varchar NOT NULL DEFAULT 'active' CHECK (state IN ('active','pending','purged','review')),
 hold_until timestamp, hold_owner varchar, hold_incident varchar, hold_reason varchar,
 snapshots json NOT NULL, audit_context json NOT NULL,
 operation_id varchar, claim_token varchar, claim_until timestamp,
 attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
 next_attempt_at timestamp NOT NULL, last_error varchar, purged_at timestamp, event_uid varchar,
 CHECK (expires_at >= base_at),
 CHECK ((hold_until IS NULL AND hold_owner IS NULL AND hold_incident IS NULL AND hold_reason IS NULL)
     OR (hold_until IS NOT NULL AND hold_owner IS NOT NULL AND hold_incident IS NOT NULL AND hold_reason IS NOT NULL)),
 CHECK (state != 'purged' OR (purged_at IS NOT NULL AND event_uid IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_identity_retention_due
 ON public.identity_retention(condominio_id,state,next_attempt_at);
ALTER TABLE public.identity_retention ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identity_retention FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.identity_retention'::regclass AND polname='identity_retention_tenant') THEN
  CREATE POLICY identity_retention_tenant ON public.identity_retention
   USING (condominio_id = current_setting('app.tenant_id',true)
      AND EXISTS (SELECT 1 FROM public.visitas v WHERE v.visita_id=identity_retention.visita_id AND v.condominio_id=identity_retention.condominio_id))
   WITH CHECK (condominio_id = current_setting('app.tenant_id',true)
      AND EXISTS (SELECT 1 FROM public.visitas v WHERE v.visita_id=identity_retention.visita_id AND v.condominio_id=identity_retention.condominio_id));
 END IF;
END $$;
GRANT SELECT,INSERT,UPDATE ON public.identity_retention TO axs_core_app;
