-- Reviewed proposal: manual owner operation, NOT a startup migration.
-- Read access serves the application control plane; writes only manage scoped
-- corporate quotas. Authority/delegation/recovery maintenance remains offline.
BEGIN;
DO $$ BEGIN
 IF current_database() <> 'aup_gov' THEN RAISE EXCEPTION 'Wrong GOV database'; END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_gov_app') THEN
  RAISE EXCEPTION 'Runtime role exists: inspect before applying';
 END IF;
END $$;
CREATE ROLE axs_gov_app NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
REVOKE ALL ON DATABASE aup_gov FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON public.authorities_gov,public.delegations_gov,public.policies_gov,public.recovery_gov_checkpoints FROM PUBLIC;
GRANT CONNECT ON DATABASE aup_gov TO axs_gov_app;
GRANT USAGE ON SCHEMA public TO axs_gov_app;
GRANT SELECT ON public.authorities_gov,public.delegations_gov,public.policies_gov,public.recovery_gov_checkpoints TO axs_gov_app;
GRANT INSERT ON public.policies_gov TO axs_gov_app;
GRANT UPDATE (limites,metadata_json,estado,valida_desde,valida_hasta) ON public.policies_gov TO axs_gov_app;
ALTER TABLE public.authorities_gov ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.authorities_gov FORCE ROW LEVEL SECURITY;
ALTER TABLE public.delegations_gov ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.delegations_gov FORCE ROW LEVEL SECURITY;
ALTER TABLE public.recovery_gov_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recovery_gov_checkpoints FORCE ROW LEVEL SECURITY;
ALTER TABLE public.policies_gov ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.policies_gov FORCE ROW LEVEL SECURITY;
CREATE POLICY gov_runtime_authority_read ON public.authorities_gov FOR SELECT TO axs_gov_app USING(true);
CREATE POLICY gov_runtime_delegation_read ON public.delegations_gov FOR SELECT TO axs_gov_app USING(true);
CREATE POLICY gov_runtime_checkpoint_read ON public.recovery_gov_checkpoints FOR SELECT TO axs_gov_app USING(true);
CREATE POLICY gov_runtime_policy_read ON public.policies_gov FOR SELECT TO axs_gov_app USING(true);
CREATE POLICY gov_runtime_quota_insert ON public.policies_gov FOR INSERT TO axs_gov_app
 WITH CHECK (ambito::text='TENANT' AND target_tenant_id::text=current_setting('app.tenant_id',true)
 AND accion_objetivo::text=ANY(ARRAY['crear_sede_corporativa','crear_destino_corporativo']::text[]));
CREATE POLICY gov_runtime_quota_update ON public.policies_gov FOR UPDATE TO axs_gov_app
 USING (ambito::text='TENANT' AND target_tenant_id::text=current_setting('app.tenant_id',true)
 AND accion_objetivo::text=ANY(ARRAY['crear_sede_corporativa','crear_destino_corporativo']::text[]))
 WITH CHECK (ambito::text='TENANT' AND target_tenant_id::text=current_setting('app.tenant_id',true)
 AND accion_objetivo::text=ANY(ARRAY['crear_sede_corporativa','crear_destino_corporativo']::text[]));
COMMIT;
