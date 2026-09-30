-- Extender el motivo del login local sin cambiar permisos ni aislamiento.
ALTER POLICY security_outbox_backend ON public.security_outbox
    WITH CHECK (
        payload->>'tenant_id' = 'PLATFORM_SECURITY'
        AND payload->>'event_uid' = event_uid
        AND payload->>'accion' = 'denegar'
        AND payload->>'resultado' = 'denegado'
        AND payload->>'entidad' IN ('session', 'scope')
        AND payload->>'motivo' IN ('NO_SESSION','INVALID_SESSION','UNKNOWN_IDENTITY',
            'SCOPE_DENIED','ROLE_DENIED','MSP_DENIED','PLATFORM_DENIED',
            'RESIDENCE_DENIED','INVALID_CREDENTIALS')
    );
