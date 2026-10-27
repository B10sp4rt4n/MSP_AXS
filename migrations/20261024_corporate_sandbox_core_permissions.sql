-- PROPOSAL ONLY. Manual owner operation, exclusively on the named EMPTY sandbox DB.
-- No LOGIN, passwords, data seeding or remote execution. CORE requires C4 first.
-- One-shot: inspect a partial application; never silently replay policies/certificates.
BEGIN;
DO $$ BEGIN
 IF current_database() <> 'axs_corp_core_sbx' THEN
  RAISE EXCEPTION 'Wrong database: sandbox permission proposal refused';
 END IF;
END $$;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corp_sandbox_core') THEN
  CREATE ROLE axs_corp_sandbox_core NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corp_sandbox_core' AND
  (rolcanlogin OR rolinherit OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
 OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_core'))
 OR EXISTS (SELECT 1 FROM pg_class WHERE relowner=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_core'))
 OR EXISTS (SELECT 1 FROM pg_database WHERE datdba=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_core'))
 OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_core'))
 THEN RAISE EXCEPTION 'Runtime role must be isolated, NOLOGIN, NOINHERIT, without ownership'; END IF;
END $$;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corporate_provisioner') THEN
  CREATE ROLE axs_corporate_provisioner NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corporate_provisioner' AND
  (rolcanlogin OR rolinherit OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
 OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='axs_corporate_provisioner'))
 OR EXISTS (SELECT 1 FROM pg_class WHERE relowner=(SELECT oid FROM pg_roles WHERE rolname='axs_corporate_provisioner'))
 OR EXISTS (SELECT 1 FROM pg_database WHERE datdba=(SELECT oid FROM pg_roles WHERE rolname='axs_corporate_provisioner'))
 OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner=(SELECT oid FROM pg_roles WHERE rolname='axs_corporate_provisioner'))
 THEN RAISE EXCEPTION 'Runtime role must be isolated, NOLOGIN, NOINHERIT, without ownership'; END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE axs_corp_core_sbx FROM PUBLIC;
CREATE TABLE public.corporate_sandbox_attestation (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 run_id uuid NOT NULL,
 domain text NOT NULL CHECK(domain='CORE'),
 database_name text NOT NULL CHECK(database_name='axs_corp_core_sbx'),
 clerk_issuer text NOT NULL,
 catalog_hash varchar(64) NOT NULL,
 certified_at timestamptz NOT NULL,
 expires_at timestamptz NOT NULL CHECK(expires_at>certified_at AND expires_at<=certified_at+interval '24 hours')
);
ALTER TABLE public.corporate_sandbox_attestation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_sandbox_attestation FORCE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE axs_corp_core_sbx FROM axs_corp_sandbox_core;
GRANT CONNECT ON DATABASE axs_corp_core_sbx TO axs_corp_sandbox_core;
REVOKE ALL ON SCHEMA public FROM axs_corp_sandbox_core;
GRANT USAGE ON SCHEMA public TO axs_corp_sandbox_core;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM axs_corp_sandbox_core;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM axs_corp_sandbox_core;
GRANT SELECT ON public.usuarios TO axs_corp_sandbox_core;
GRANT SELECT ON public.msps_exo TO axs_corp_sandbox_core;
GRANT SELECT ON public.condominios_exo TO axs_corp_sandbox_core;
GRANT SELECT ON public.corporate_organizations TO axs_corp_sandbox_core;
GRANT SELECT ON public.corporate_memberships TO axs_corp_sandbox_core;
GRANT SELECT ON public.corporate_site_assignments TO axs_corp_sandbox_core;
GRANT SELECT ON public.msp_memberships TO axs_corp_sandbox_core;
GRANT SELECT ON public.user_tenant_scope TO axs_corp_sandbox_core;
GRANT SELECT ON public.provider_contracts TO axs_corp_sandbox_core;
GRANT SELECT, INSERT, UPDATE ON public.corporate_sites TO axs_corp_sandbox_core;
GRANT SELECT, INSERT, UPDATE ON public.corporate_destinations TO axs_corp_sandbox_core;
GRANT SELECT, INSERT, UPDATE ON public.arco_cases TO axs_corp_sandbox_core;
GRANT SELECT, INSERT ON public.event_outbox TO axs_corp_sandbox_core;
GRANT SELECT, INSERT ON public.security_outbox TO axs_corp_sandbox_core;
GRANT SELECT ON public.corporate_sandbox_attestation TO axs_corp_sandbox_core;
GRANT UPDATE (delivered_at, attempts, next_attempt_at, last_error) ON public.event_outbox TO axs_corp_sandbox_core;
GRANT UPDATE (delivered_at, attempts, next_attempt_at, last_error) ON public.security_outbox TO axs_corp_sandbox_core;
REVOKE ALL ON DATABASE axs_corp_core_sbx FROM axs_corporate_provisioner;
GRANT CONNECT ON DATABASE axs_corp_core_sbx TO axs_corporate_provisioner;
REVOKE ALL ON SCHEMA public FROM axs_corporate_provisioner;
GRANT USAGE ON SCHEMA public TO axs_corporate_provisioner;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM axs_corporate_provisioner;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM axs_corporate_provisioner;
GRANT SELECT ON public.condominios_exo TO axs_corporate_provisioner;
GRANT SELECT, INSERT ON public.corporate_organizations TO axs_corporate_provisioner;
GRANT SELECT, INSERT ON public.corporate_memberships TO axs_corporate_provisioner;
GRANT INSERT ON public.event_outbox TO axs_corporate_provisioner;
GRANT SELECT, INSERT ON public.corporate_provisioning_operations TO axs_corporate_provisioner;
GRANT SELECT ON public.corporate_sandbox_attestation TO axs_corporate_provisioner;
GRANT INSERT (condominio_id, msp_id, nombre, modalidad, corporativo_habilitado) ON public.condominios_exo TO axs_corporate_provisioner;
GRANT UPDATE (corporativo_habilitado) ON public.condominios_exo TO axs_corporate_provisioner;
GRANT UPDATE (estado, confirmed_at, confirmation_event_uid) ON public.corporate_provisioning_operations TO axs_corporate_provisioner;
DO $$ DECLARE seq text; BEGIN
 seq:=pg_get_serial_sequence('public.condominios_exo','id');
 IF seq IS NULL THEN RAISE EXCEPTION 'Missing expected sequence'; END IF;
 EXECUTE format('GRANT USAGE ON SEQUENCE %s TO axs_corporate_provisioner',seq);
END $$;
CREATE POLICY sandbox_attestation_read ON public.corporate_sandbox_attestation FOR SELECT TO axs_corp_sandbox_core, axs_corporate_provisioner USING(true);
-- Trusted backend identity catalog: only offline-enrolled synthetic subjects.
CREATE POLICY sandbox_identity_read ON public.usuarios FOR SELECT TO axs_corp_sandbox_core USING(true);
CREATE POLICY sandbox_provider_read ON public.msps_exo FOR SELECT TO axs_corp_sandbox_core USING(true);
CREATE POLICY sandbox_company_read ON public.condominios_exo FOR SELECT TO axs_corp_sandbox_core,axs_corporate_provisioner USING(modalidad='corporativo');
CREATE POLICY sandbox_company_insert ON public.condominios_exo FOR INSERT TO axs_corporate_provisioner WITH CHECK(modalidad='corporativo' AND condominio_id=current_setting('app.tenant_id',true));
CREATE POLICY sandbox_company_enable ON public.condominios_exo FOR UPDATE TO axs_corporate_provisioner USING(modalidad='corporativo' AND condominio_id=current_setting('app.tenant_id',true)) WITH CHECK(modalidad='corporativo' AND condominio_id=current_setting('app.tenant_id',true));
-- These three legacy guard tables have SELECT grants but no permitting policies.
-- They return no scopes, MSP membership or contracts; no residential authorization.
CREATE POLICY sandbox_arco_tenant ON public.arco_cases TO axs_corp_sandbox_core USING(condominio_id=current_setting('app.tenant_id',true)) WITH CHECK(condominio_id=current_setting('app.tenant_id',true));
CREATE POLICY sandbox_event_outbox ON public.event_outbox TO axs_corp_sandbox_core,axs_corporate_provisioner USING(condominio_id=current_setting('app.tenant_id',true)) WITH CHECK(condominio_id=current_setting('app.tenant_id',true) AND payload->>'tenant_id'=condominio_id AND payload->>'event_uid'=event_uid);
CREATE POLICY sandbox_security_outbox ON public.security_outbox TO axs_corp_sandbox_core USING(true) WITH CHECK(payload->>'tenant_id' = 'PLATFORM_SECURITY'
                AND payload->>'event_uid' = event_uid
                AND payload->>'accion' = 'denegar'
                AND payload->>'resultado' = 'denegado'
                AND payload->>'entidad' IN ('session', 'scope')
                AND payload->>'motivo' IN ('NO_SESSION','INVALID_SESSION','UNKNOWN_IDENTITY',
                    'SCOPE_DENIED','ROLE_DENIED','MSP_DENIED','PLATFORM_DENIED','RESIDENCE_DENIED',
                    'INVALID_CREDENTIALS','TENANT_MODE_DENIED','CORPORATE_DISABLED'));
-- Row-lock-only capability: SELECT FOR UPDATE otherwise requires UPDATE rights.
-- Fixed relation, qualified identifiers, no dynamic SQL, no rows returned.
CREATE FUNCTION public.corporate_sandbox_lock_company(company text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM 1 FROM public.condominios_exo WHERE condominio_id=company AND modalidad='corporativo' FOR UPDATE;
END $$;
REVOKE ALL ON FUNCTION public.corporate_sandbox_lock_company(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.corporate_sandbox_lock_company(text) TO axs_corp_sandbox_core;
COMMIT;
