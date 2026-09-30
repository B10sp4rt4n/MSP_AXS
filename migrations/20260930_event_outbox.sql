-- Aplicar con propietario de CORE antes del despliegue. Reejecutable y aditiva.
CREATE TABLE IF NOT EXISTS public.event_outbox (
    event_uid varchar PRIMARY KEY,
    condominio_id varchar NOT NULL REFERENCES public.condominios_exo(condominio_id),
    payload json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    delivered_at timestamp without time zone,
    attempts integer NOT NULL DEFAULT 0,
    next_attempt_at timestamp without time zone NOT NULL,
    last_error varchar
);
CREATE INDEX IF NOT EXISTS ix_event_outbox_pending
    ON public.event_outbox (condominio_id, delivered_at, next_attempt_at);
ALTER TABLE public.event_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_outbox FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.event_outbox'::regclass
                   AND polname='event_outbox_tenant') THEN
        CREATE POLICY event_outbox_tenant ON public.event_outbox
            USING (condominio_id = current_setting('app.tenant_id', true))
            WITH CHECK (condominio_id = current_setting('app.tenant_id', true));
    END IF;
END $$;
GRANT SELECT, INSERT ON public.event_outbox TO axs_core_app;
GRANT UPDATE (delivered_at, attempts, next_attempt_at, last_error)
    ON public.event_outbox TO axs_core_app;
