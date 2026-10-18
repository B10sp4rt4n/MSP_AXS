-- Apply to CORE after progressive_identity and before deploying Amazon support.
-- Repeatable; existing provider rows and Alexa bindings are preserved.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
ALTER TABLE public.external_identities DROP CONSTRAINT IF EXISTS external_provider;
ALTER TABLE public.external_identities ADD CONSTRAINT external_provider
 CHECK (provider IN ('whatsapp','facebook','instagram','amazon'));
COMMIT;
