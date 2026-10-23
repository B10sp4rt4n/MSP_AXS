# Ensayo de bootstrap en las bases corporativas vacías — 23 octubre 2026

**Alcance:** exclusivamente `br-soft-leaf-b59xcclw` (proyecto Neon `MSP_AXS`). Nunca ejecutar en `production`, ni en `axs-development-20261002`, ni en `neondb/aup_gov/aup_event` copiadas.

## Tres bases limpias comprobadas
- `axs_corp_core_sbx`
- `axs_corp_gov_sbx`
- `axs_corp_event_sbx`

Las tres reportaron 0 tablas de aplicación, 0 objetos tipo tabla y usuario `neondb_owner` antes del bootstrap. La información histórica del desarrollo no se copia.

## Método trazable
El script `scripts/export_corporate_sandbox_ddl.py` genera DDL estrictamente estructural desde los modelos ORM actuales usando `create_mock_engine` de SQLAlchemy, **sin abrir conexiones**. El CI PostgreSQL lo emite únicamente después de sus pruebas reales, con hash SHA-256 y orden de las sentencias por dominio. Esto evita reconstruir a mano las 23 entidades CORE, las 4 GOV y la entidad EVENT.

Las sentencias deben contrastarse con el CI y luego aplicarse con una transacción por base, mediante el conector Neon y con **branch_id y database_name explícitos**. Antes se repite la verificación de cero tablas/objetos, y después se verifica cantidad de tablas, ausencia de filas y `FORCE ROW LEVEL SECURITY` en todas. Las cinco políticas corporativas se agregan por nombre con `app.tenant_id`.

**No contiene datos, grants, passwords, roles LOGIN ni activación de capacidades.** El rol propietario sirve exclusivamente al DDL. Los permisos de aplicación requerirán una revisión y transacción separadas, y las funciones corporativas permanecen en false.

## No hacer
- No ejecutar el bootstrap desde el arranque del backend.
- No copiar bases o filas del desarrollo.
- No conceder `neon_superuser` a cuentas de runtime.
- No usar roles `NOLOGIN` como conexión efectiva de API.
- No realizar `accept-deploy` de Railway con configuración incompleta.

El siguiente hito, posterior a la verificación del esquema, es revisar por columna los GRANT, RLS y el control-plane de alta con datos completamente sintéticos.
