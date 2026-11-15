-- Manual migration only. Feature remains OFF until isolated acceptance.
BEGIN;
DO $$ BEGIN
 IF to_regclass('public.corporate_visits') IS NOT NULL THEN
  RAISE EXCEPTION 'Visit table exists: inspect before retry';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid='public.corporate_destinations'::regclass AND conname='uq_corporate_destination_scope') THEN
  ALTER TABLE public.corporate_destinations ADD CONSTRAINT uq_corporate_destination_scope UNIQUE(tenant_id,site_id,destination_id);
 END IF;
END $$;

CREATE TABLE public.corporate_visits (
	tenant_id VARCHAR NOT NULL, 
	visit_id VARCHAR(36) NOT NULL, 
	site_id VARCHAR(40) NOT NULL, 
	destination_id VARCHAR(40) NOT NULL, 
	host_user_id VARCHAR NOT NULL, 
	visitor_ref VARCHAR(80) NOT NULL, 
	state VARCHAR(16) NOT NULL, 
	created_by VARCHAR NOT NULL, 
	authorized_by VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	authorized_at TIMESTAMP WITHOUT TIME ZONE, 
	entered_at TIMESTAMP WITHOUT TIME ZONE, 
	exited_at TIMESTAMP WITHOUT TIME ZONE, 
	cancelled_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (tenant_id, visit_id), 
	FOREIGN KEY(tenant_id, site_id, destination_id) REFERENCES public.corporate_destinations (tenant_id, site_id, destination_id), 
	FOREIGN KEY(tenant_id, host_user_id) REFERENCES public.corporate_memberships (tenant_id, user_id), 
	CONSTRAINT ck_corporate_visit_state CHECK (state IN ('preregistrada','autorizada','dentro','cerrada','cancelada')), 
	CONSTRAINT ck_corporate_visit_times CHECK ((state='preregistrada' AND authorized_at IS NULL AND authorized_by IS NULL AND entered_at IS NULL AND exited_at IS NULL AND cancelled_at IS NULL) OR (state='autorizada' AND authorized_at IS NOT NULL AND authorized_by IS NOT NULL AND entered_at IS NULL AND exited_at IS NULL AND cancelled_at IS NULL) OR (state='dentro' AND authorized_at IS NOT NULL AND authorized_by IS NOT NULL AND entered_at>=authorized_at AND entered_at IS NOT NULL AND exited_at IS NULL AND cancelled_at IS NULL) OR (state='cerrada' AND authorized_at IS NOT NULL AND authorized_by IS NOT NULL AND entered_at>=authorized_at AND entered_at IS NOT NULL AND exited_at>=entered_at AND exited_at IS NOT NULL AND cancelled_at IS NULL) OR (state='cancelada' AND entered_at IS NULL AND exited_at IS NULL AND cancelled_at IS NOT NULL))
)

;
CREATE INDEX ix_corporate_visits_site_created ON public.corporate_visits(tenant_id,site_id,created_at);
ALTER TABLE public.corporate_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_visits FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.corporate_visits FROM PUBLIC;
GRANT SELECT,INSERT ON public.corporate_visits TO axs_core_app;
GRANT UPDATE(state,authorized_by,authorized_at,entered_at,exited_at,cancelled_at) ON public.corporate_visits TO axs_core_app;
CREATE POLICY corporate_visit_tenant ON public.corporate_visits TO axs_core_app
 USING(tenant_id=current_setting('app.tenant_id',true))
 WITH CHECK(tenant_id=current_setting('app.tenant_id',true));
COMMIT;
