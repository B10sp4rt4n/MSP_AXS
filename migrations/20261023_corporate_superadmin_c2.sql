-- AXS Corporativo C2: PRIVILEGIO SEGREGADO + contacto de privacidad.
-- Requiere C0 y C1. EJECUTAR SOLO COMO PROPIETARIO EN ENTORNO DESCARTABLE.
-- No crea contraseña, no activa LOGIN ni altera roles usados por Railway.
BEGIN;
ALTER TABLE public.corporate_organizations
 ADD COLUMN IF NOT EXISTS privacy_contact varchar(254),
 ADD COLUMN IF NOT EXISTS privacy_notice_url varchar(500),
 ADD COLUMN IF NOT EXISTS privacy_notice_version varchar(80);

DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='axs_corporate_provisioner') THEN
  CREATE ROLE axs_corporate_provisioner NOLOGIN NOINHERIT NOSUPERUSER
   NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
 IF EXISTS (
  SELECT 1 FROM pg_roles WHERE rolname='axs_corporate_provisioner'
  AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit)
 ) THEN
  RAISE EXCEPTION 'Provisioner requiere rol no privilegiado, NOINHERIT y sin BYPASSRLS';
 END IF;
 IF EXISTS (
  SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
  WHERE r.rolname='axs_corporate_provisioner'
 ) THEN
  RAISE EXCEPTION 'Provisioner no puede heredar otros roles';
 END IF;
END $$;
DO $$
BEGIN
 EXECUTE format('GRANT CONNECT ON DATABASE %I TO axs_corporate_provisioner',current_database());
END $$;
GRANT USAGE ON SCHEMA public TO axs_corporate_provisioner;

-- No adquiere DDL, superuser, bypass de RLS, DELETE ni manejo de visitas.
GRANT SELECT ON public.condominios_exo TO axs_corporate_provisioner;
GRANT INSERT (condominio_id,msp_id,nombre,modalidad,corporativo_habilitado)
 ON public.condominios_exo TO axs_corporate_provisioner;
GRANT UPDATE (corporativo_habilitado)
 ON public.condominios_exo TO axs_corporate_provisioner;
GRANT SELECT, INSERT ON public.corporate_organizations TO axs_corporate_provisioner;
GRANT SELECT, INSERT ON public.corporate_memberships TO axs_corporate_provisioner;
GRANT INSERT ON public.event_outbox TO axs_corporate_provisioner;

-- IMPORTANTE: no modificar GRANT del rol de aplicación axs_core_app.
-- Los privilegios del provisioner solo son efectivos con app.tenant_id
-- en tablas RLS y con credenciales separadas guardadas en backend.
COMMIT;

-- Operación manual posterior, FUERA del repositorio y solo tras aceptar CI:
-- crear contraseña robusta y permitir LOGIN al rol de aprovisionamiento.
-- DATABASE_CORPORATE_PROVISIONING_URL debe ser SECRET backend, no frontend.
-- El valor predeterminado de AXS_CORPORATE_PROVISIONING_ENABLED debe seguir false.
