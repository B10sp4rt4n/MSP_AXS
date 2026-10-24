-- PROPOSAL ONLY. Manual owner operation, exclusively on the named EMPTY sandbox DB.
-- No LOGIN, passwords, data seeding or remote execution. CORE requires C4 first.
-- One-shot: inspect a partial application; never silently replay policies/certificates.
BEGIN;
DO $$ BEGIN
 IF current_database() <> 'axs_corp_event_sbx' THEN
  RAISE EXCEPTION 'Wrong database: sandbox permission proposal refused';
 END IF;
END $$;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corp_sandbox_event') THEN
  CREATE ROLE axs_corp_sandbox_event NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corp_sandbox_event' AND
  (rolcanlogin OR rolinherit OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
 OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_event'))
 OR EXISTS (SELECT 1 FROM pg_class WHERE relowner=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_event'))
 OR EXISTS (SELECT 1 FROM pg_database WHERE datdba=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_event'))
 OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner=(SELECT oid FROM pg_roles WHERE rolname='axs_corp_sandbox_event'))
 THEN RAISE EXCEPTION 'Runtime role must be isolated, NOLOGIN, NOINHERIT, without ownership'; END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE axs_corp_event_sbx FROM PUBLIC;
CREATE TABLE public.corporate_sandbox_attestation (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 run_id uuid NOT NULL,
 domain text NOT NULL CHECK(domain='EVENT'),
 database_name text NOT NULL CHECK(database_name='axs_corp_event_sbx'),
 clerk_issuer text NOT NULL,
 catalog_hash varchar(64) NOT NULL,
 certified_at timestamptz NOT NULL,
 expires_at timestamptz NOT NULL CHECK(expires_at>certified_at AND expires_at<=certified_at+interval '24 hours')
);
ALTER TABLE public.corporate_sandbox_attestation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_sandbox_attestation FORCE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE axs_corp_event_sbx FROM axs_corp_sandbox_event;
GRANT CONNECT ON DATABASE axs_corp_event_sbx TO axs_corp_sandbox_event;
REVOKE ALL ON SCHEMA public FROM axs_corp_sandbox_event;
GRANT USAGE ON SCHEMA public TO axs_corp_sandbox_event;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM axs_corp_sandbox_event;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM axs_corp_sandbox_event;
GRANT SELECT, INSERT ON public.events_aup TO axs_corp_sandbox_event;
GRANT SELECT ON public.corporate_sandbox_attestation TO axs_corp_sandbox_event;
DO $$ DECLARE seq text; BEGIN
 seq:=pg_get_serial_sequence('public.events_aup','id');
 IF seq IS NULL THEN RAISE EXCEPTION 'Missing expected sequence'; END IF;
 EXECUTE format('GRANT USAGE ON SEQUENCE %s TO axs_corp_sandbox_event',seq);
END $$;
CREATE POLICY sandbox_attestation_read ON public.corporate_sandbox_attestation FOR SELECT TO axs_corp_sandbox_event USING(true);
CREATE POLICY sandbox_event_tenant ON public.events_aup TO axs_corp_sandbox_event
 USING(tenant_id=current_setting('app.tenant_id',true))
 WITH CHECK(tenant_id=current_setting('app.tenant_id',true) AND (tenant_id<>'PLATFORM_SECURITY' OR (accion='denegar' AND resultado='denegado' AND entidad IN ('session','scope'))));
COMMIT;
