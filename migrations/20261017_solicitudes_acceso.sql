-- CORE: apply before backend/frontend deployment; no external channel activation.
BEGIN;
ALTER TABLE public.visitas ADD COLUMN IF NOT EXISTS solicitud_remota_id varchar;
ALTER TABLE public.visitas ADD COLUMN IF NOT EXISTS autorizacion_remota_hasta timestamp;
CREATE TABLE IF NOT EXISTS public.solicitudes_acceso (
 solicitud_id varchar PRIMARY KEY,
 condominio_id varchar NOT NULL REFERENCES public.condominios_exo(condominio_id),
 visita_id varchar NOT NULL REFERENCES public.visitas(visita_id),
 destino_id varchar NOT NULL REFERENCES public.casas(casa_id),
 solicitada_por varchar NOT NULL REFERENCES public.usuarios(usuario_id),
 destinatarios json NOT NULL, fingerprint varchar NOT NULL,
 estado varchar NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','permitida','rechazada','expirada','consumida')),
 creada_en timestamp NOT NULL, expira_en timestamp NOT NULL,
 respondida_por varchar REFERENCES public.usuarios(usuario_id), respondida_en timestamp,
 consentimiento_en timestamp,
 CHECK (expira_en > creada_en),
 CHECK (estado NOT IN ('permitida','rechazada','consumida') OR
   (respondida_por IS NOT NULL AND respondida_en IS NOT NULL AND consentimiento_en IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_solicitudes_acceso_condominio_id ON public.solicitudes_acceso(condominio_id);
CREATE INDEX IF NOT EXISTS ix_solicitudes_acceso_visita_id ON public.solicitudes_acceso(visita_id);
ALTER TABLE public.solicitudes_acceso ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.solicitudes_acceso FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.solicitudes_acceso'::regclass AND polname='solicitudes_acceso_tenant') THEN
  CREATE POLICY solicitudes_acceso_tenant ON public.solicitudes_acceso
   USING (condominio_id = current_setting('app.tenant_id',true)
      AND EXISTS (SELECT 1 FROM public.visitas v WHERE v.visita_id=solicitudes_acceso.visita_id AND v.condominio_id=solicitudes_acceso.condominio_id))
   WITH CHECK (condominio_id = current_setting('app.tenant_id',true)
      AND EXISTS (SELECT 1 FROM public.visitas v WHERE v.visita_id=solicitudes_acceso.visita_id AND v.condominio_id=solicitudes_acceso.condominio_id)
      AND EXISTS (SELECT 1 FROM public.casas c WHERE c.casa_id=solicitudes_acceso.destino_id AND c.condominio_id=solicitudes_acceso.condominio_id));
 END IF;
END $$;
GRANT SELECT,INSERT,UPDATE ON public.solicitudes_acceso TO axs_core_app;
COMMIT;
