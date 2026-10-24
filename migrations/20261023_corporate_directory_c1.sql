-- AXS Corporativo C1 — CORE, solo despues de migration 20261023_tenant_modalidad_c0.sql
-- NO ejecutar en produccion; prueba primero en PostgreSQL desechable.
-- Necesita propietario de esquema; nunca utilizar rol runtime con privilegios de DDL.
BEGIN;

-- Permite FK fuerte (tenant, modalidad) para prohibir un perfil empresarial
-- referido a tenant residencial aunque el llamador eluda la API.
CREATE UNIQUE INDEX IF NOT EXISTS uq_condominios_modalidad
 ON public.condominios_exo(condominio_id, modalidad);

CREATE TABLE IF NOT EXISTS public.corporate_organizations (
 tenant_id varchar PRIMARY KEY,
 modalidad varchar(16) NOT NULL DEFAULT 'corporativo',
 created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT ck_corporate_org_mode CHECK (modalidad = 'corporativo'),
 CONSTRAINT fk_corporate_org_tenant_mode
   FOREIGN KEY(tenant_id,modalidad) REFERENCES public.condominios_exo(condominio_id,modalidad)
);

CREATE TABLE IF NOT EXISTS public.corporate_sites (
 site_id varchar(40) PRIMARY KEY,
 tenant_id varchar NOT NULL REFERENCES public.corporate_organizations(tenant_id),
 nombre varchar(120) NOT NULL,
 zona_horaria varchar(80) NOT NULL DEFAULT 'America/Mexico_City',
 activa boolean NOT NULL DEFAULT true,
 created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT uq_corporate_site_tenant_id UNIQUE(tenant_id,site_id)
);

CREATE TABLE IF NOT EXISTS public.corporate_destinations (
 destination_id varchar(40) PRIMARY KEY,
 tenant_id varchar NOT NULL,
 site_id varchar(40) NOT NULL,
 nombre varchar(120) NOT NULL,
 activa boolean NOT NULL DEFAULT true,
 CONSTRAINT fk_corporate_destination_site FOREIGN KEY(tenant_id,site_id)
   REFERENCES public.corporate_sites(tenant_id,site_id),
 CONSTRAINT uq_corporate_destination_name UNIQUE(tenant_id,site_id,nombre)
);

CREATE TABLE IF NOT EXISTS public.corporate_memberships (
 membership_id varchar(40) PRIMARY KEY,
 tenant_id varchar NOT NULL REFERENCES public.corporate_organizations(tenant_id),
 user_id varchar NOT NULL REFERENCES public.usuarios(usuario_id),
 rol varchar(16) NOT NULL CHECK (rol IN ('owner','admin','host','reception')),
 estado varchar(12) NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','revocado')),
 created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT uq_corporate_member_tenant_user UNIQUE(tenant_id,user_id)
);

CREATE TABLE IF NOT EXISTS public.corporate_site_assignments (
 assignment_id varchar(40) PRIMARY KEY,
 tenant_id varchar NOT NULL,
 site_id varchar(40) NOT NULL,
 user_id varchar NOT NULL,
 estado varchar(12) NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','revocado')),
 CONSTRAINT fk_corporate_assignment_site FOREIGN KEY(tenant_id,site_id)
   REFERENCES public.corporate_sites(tenant_id,site_id),
 CONSTRAINT fk_corporate_assignment_member FOREIGN KEY(tenant_id,user_id)
   REFERENCES public.corporate_memberships(tenant_id,user_id),
 CONSTRAINT uq_corporate_assignment UNIQUE(tenant_id,site_id,user_id)
);

CREATE INDEX IF NOT EXISTS ix_corporate_sites_tenant ON public.corporate_sites(tenant_id);
CREATE INDEX IF NOT EXISTS ix_corporate_destinations_tenant_site ON public.corporate_destinations(tenant_id,site_id);
CREATE INDEX IF NOT EXISTS ix_corporate_memberships_tenant_user ON public.corporate_memberships(tenant_id,user_id);
CREATE INDEX IF NOT EXISTS ix_corporate_assignments_tenant_site ON public.corporate_site_assignments(tenant_id,site_id,user_id);

ALTER TABLE public.corporate_organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_organizations FORCE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_sites FORCE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_destinations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_destinations FORCE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_site_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.corporate_site_assignments FORCE ROW LEVEL SECURITY;

DO $$
DECLARE table_name text; policy_name text;
BEGIN
 FOREACH table_name IN ARRAY ARRAY[
  'corporate_organizations','corporate_sites','corporate_destinations',
  'corporate_memberships','corporate_site_assignments'
 ] LOOP
  policy_name := table_name || '_tenant';
  IF NOT EXISTS(
   SELECT 1 FROM pg_policy
   WHERE polrelid=format('public.%I',table_name)::regclass AND polname=policy_name
  ) THEN
   EXECUTE format(
    'CREATE POLICY %I ON public.%I USING (tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK (tenant_id=current_setting(''app.tenant_id'',true))',
    policy_name,table_name
   );
  END IF;
 END LOOP;
END $$;

-- Nunca conceder DELETE al runtime ni INSERT/UPDATE de membresias o asignaciones.
-- Solo futuras operaciones de aprovisionamiento privilegiado podran modificarlas.
GRANT SELECT ON public.corporate_organizations,public.corporate_memberships,
 public.corporate_site_assignments TO axs_core_app;
GRANT SELECT,INSERT,UPDATE ON public.corporate_sites,public.corporate_destinations
 TO axs_core_app;
COMMIT;
