-- Apply to CORE before deploying the application. Additive, repeatable.
BEGIN;
ALTER TABLE public.usuarios ADD COLUMN IF NOT EXISTS celular varchar(16);
ALTER TABLE public.usuarios ADD COLUMN IF NOT EXISTS celular_verified_at timestamp;
ALTER TABLE public.usuarios ADD COLUMN IF NOT EXISTS celular_consent_at timestamp;
-- Identity control plane, like usuarios; deliberately not tenant-owned.
-- Only self-service authenticated routes expose these private references.
CREATE TABLE IF NOT EXISTS public.external_identities (
 identity_id varchar PRIMARY KEY,
 usuario_id varchar NOT NULL REFERENCES public.usuarios(usuario_id),
 provider varchar(16) NOT NULL,
 reference varchar(300),
 consent_at timestamp NOT NULL,
 consent_version varchar(40) NOT NULL,
 verified_at timestamp,
 verification_method varchar(80),
 revoked_at timestamp,
 updated_at timestamp NOT NULL,
 CONSTRAINT uq_external_identity_provider UNIQUE(usuario_id, provider),
 CONSTRAINT external_provider CHECK (provider IN ('whatsapp','facebook','instagram')),
 CONSTRAINT external_verification CHECK (
   (verified_at IS NULL AND verification_method IS NULL) OR
   (verified_at IS NOT NULL AND verification_method IS NOT NULL)),
 CONSTRAINT external_revocation CHECK (
   (revoked_at IS NULL AND reference IS NOT NULL) OR
   (revoked_at IS NOT NULL AND reference IS NULL AND verified_at IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_external_identities_usuario_id ON public.external_identities(usuario_id);
GRANT SELECT, INSERT, UPDATE ON public.external_identities TO axs_core_app;
COMMIT;
