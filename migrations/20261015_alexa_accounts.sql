-- Additive control-plane table. Signed lifecycle events precede tenant linkage.
-- No RLS: it resolves an external identity, like usuarios/provider_contracts.
-- Never contains visitor names or access/refresh tokens. Reads of tenant data
-- still require live Usuario + AUP_SCOPE + provider-contract + tenant RLS.
CREATE TABLE IF NOT EXISTS public.alexa_accounts (
 account_key varchar(64) PRIMARY KEY,
 amazon_user_id varchar(1024) NOT NULL UNIQUE,
 usuario_id varchar REFERENCES public.usuarios(usuario_id),
 condominio_id varchar REFERENCES public.condominios_exo(condominio_id),
 casa_id varchar REFERENCES public.casas(casa_id),
 linked_at timestamp, disabled_at timestamp,
 permission_at timestamp, permission_granted boolean NOT NULL DEFAULT false,
 subscription_at timestamp, subscribed boolean NOT NULL DEFAULT false,
 CONSTRAINT alexa_complete_binding CHECK ((usuario_id IS NULL AND condominio_id IS NULL AND casa_id IS NULL AND linked_at IS NULL)
     OR (usuario_id IS NOT NULL AND condominio_id IS NOT NULL AND casa_id IS NOT NULL AND linked_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_alexa_accounts_usuario_id ON public.alexa_accounts(usuario_id);
CREATE INDEX IF NOT EXISTS ix_alexa_accounts_condominio_id ON public.alexa_accounts(condominio_id);
GRANT SELECT, INSERT, UPDATE ON public.alexa_accounts TO axs_core_app;
