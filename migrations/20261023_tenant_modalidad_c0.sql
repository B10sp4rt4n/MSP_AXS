-- AXS CORPORATIVO C0 (CORE).
-- NO aplicar en produccion sin plan coordinado con despliegue de backend.
-- Mantiene la tabla fisica legacy condominios_exo como raiz de aislamiento.
-- Todos los tenants previos permanecen residenciales. No crea empresas ni sedes.
-- Ensayar primero en una rama PostgreSQL desechable y comprobar grants/RLS.
BEGIN;

ALTER TABLE public.condominios_exo
    ADD COLUMN IF NOT EXISTS modalidad varchar(16) NOT NULL DEFAULT 'residencial';

ALTER TABLE public.condominios_exo
    ADD COLUMN IF NOT EXISTS corporativo_habilitado boolean NOT NULL DEFAULT false;

-- Compatibilidad: no reclasificar clientes existentes ni activar un piloto.
-- Los defaults cubren escrituras de versiones previas del backend.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.condominios_exo'::regclass
          AND conname = 'ck_condominios_modalidad'
    ) THEN
        ALTER TABLE public.condominios_exo
            ADD CONSTRAINT ck_condominios_modalidad
            CHECK (modalidad IN ('residencial', 'corporativo'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.condominios_exo'::regclass
          AND conname = 'ck_condominios_corporativo_habilitado'
    ) THEN
        ALTER TABLE public.condominios_exo
            ADD CONSTRAINT ck_condominios_corporativo_habilitado
            CHECK (NOT corporativo_habilitado OR modalidad = 'corporativo');
    END IF;
END $$;

-- No se cambian politicas RLS ni privilegios de rol en esta fase.
-- A futuro, el alta empresarial debe quedar reservada a Superadmin
-- y nunca invocar /condominios/ (que genera destinos residenciales).
COMMIT;

-- REVISION POSTERIOR (lectura, en una conexion autorizada):
-- SELECT modalidad, corporativo_habilitado, count(*)
-- FROM public.condominios_exo GROUP BY 1, 2;
-- Resultado esperado sobre datos existentes: SOLO residencial / false.
