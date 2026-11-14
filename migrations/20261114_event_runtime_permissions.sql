-- Reviewed proposal: manual owner operation, NOT a startup migration.
-- Rehearse on an isolated restored branch first. No LOGIN or passwords.
-- Existing data/owner are preserved; role activation is a separate operation.
BEGIN;
DO $$ BEGIN
 IF current_database() <> 'aup_event' THEN RAISE EXCEPTION 'Wrong EVENT database'; END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_event_app') THEN
  RAISE EXCEPTION 'Runtime role exists: inspect before applying';
 END IF;
END $$;
CREATE ROLE axs_event_app NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
REVOKE ALL ON DATABASE aup_event FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON public.events_aup FROM PUBLIC;
GRANT CONNECT ON DATABASE aup_event TO axs_event_app;
GRANT USAGE ON SCHEMA public TO axs_event_app;
GRANT SELECT, INSERT ON public.events_aup TO axs_event_app;
DO $$ DECLARE seq text; BEGIN
 seq:=pg_get_serial_sequence('public.events_aup','id');
 IF seq IS NULL THEN RAISE EXCEPTION 'Missing EVENT sequence'; END IF;
 EXECUTE format('GRANT USAGE ON SEQUENCE %s TO axs_event_app',seq);
END $$;
ALTER TABLE public.events_aup ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events_aup FORCE ROW LEVEL SECURITY;
CREATE POLICY event_runtime_read ON public.events_aup FOR SELECT TO axs_event_app
 USING (tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY event_runtime_insert ON public.events_aup FOR INSERT TO axs_event_app
 WITH CHECK (tenant_id::text=current_setting('app.tenant_id',true) AND
 (tenant_id::text<>'PLATFORM_SECURITY' OR
 (accion::text='denegar' AND resultado::text='denegado' AND
 entidad::text=ANY(ARRAY['session','scope']::text[]))));
COMMIT;
