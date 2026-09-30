-- Auditar intentos de plataforma sin elevar roles ni fijar un tenant operativo.
CREATE TABLE IF NOT EXISTS public.security_outbox (
    event_uid varchar PRIMARY KEY,
    payload json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    delivered_at timestamp without time zone,
    attempts integer NOT NULL DEFAULT 0,
    next_attempt_at timestamp without time zone NOT NULL,
    last_error varchar
);
CREATE INDEX IF NOT EXISTS ix_security_outbox_pending
    ON public.security_outbox (delivered_at, next_attempt_at);
ALTER TABLE public.security_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.security_outbox FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.security_outbox'::regclass
                   AND polname='security_outbox_backend') THEN
        CREATE POLICY security_outbox_backend ON public.security_outbox TO axs_core_app
            USING (true)
            WITH CHECK (
                payload->>'tenant_id' = 'PLATFORM_SECURITY'
                AND payload->>'event_uid' = event_uid
                AND payload->>'accion' = 'denegar'
                AND payload->>'resultado' = 'denegado'
                AND payload->>'entidad' IN ('session', 'scope')
                AND payload->>'motivo' IN ('NO_SESSION','INVALID_SESSION','UNKNOWN_IDENTITY',
                    'SCOPE_DENIED','ROLE_DENIED','MSP_DENIED','PLATFORM_DENIED','RESIDENCE_DENIED')
            );
    END IF;
END $$;
GRANT SELECT, INSERT ON public.security_outbox TO axs_core_app;
GRANT UPDATE (delivered_at, attempts, next_attempt_at, last_error)
    ON public.security_outbox TO axs_core_app;
