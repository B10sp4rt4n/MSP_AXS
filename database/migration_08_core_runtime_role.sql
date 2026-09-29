-- Ejecutar como propietario después de migration_06, primero en rama aislada.
-- No incluye contraseña. LOGIN/PASSWORD se provisionan fuera del repositorio.
-- No habilita RLS ni cambia el rol de Railway.
BEGIN;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'axs_core_app') THEN
        CREATE ROLE axs_core_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOREPLICATION NOBYPASSRLS;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'axs_core_app'
        AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication)) THEN
        RAISE EXCEPTION 'axs_core_app tiene privilegios elevados; no continuar';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
        WHERE r.rolname='axs_core_app') THEN
        RAISE EXCEPTION 'axs_core_app tiene membresías de rol; revisar antes de continuar';
    END IF;
END $$;
GRANT CONNECT ON DATABASE neondb TO axs_core_app;
GRANT USAGE ON SCHEMA public TO axs_core_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    public.msps_exo, public.condominios_exo, public.casas, public.casetas,
    public.visitas, public.evidencias, public.usuarios,
    public.msp_memberships, public.user_tenant_scope TO axs_core_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO axs_core_app;
COMMIT;
