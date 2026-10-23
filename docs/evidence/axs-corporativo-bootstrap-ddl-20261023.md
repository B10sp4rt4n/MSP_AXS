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


## Resultado Neon — esquema instalado

Se completó la instalación de las **165 sentencias** exportadas del código ORM (CI GitHub Actions job `120607313380`; 91 pruebas PostgreSQL aprobadas).

Hashes del DDL emitido:
- CORE, 113 sentencias: `d4857128f362f7db9e057ebc6bee3aebd318e0573c26a85319dd62fdec24fca2`
- GOV, 35 sentencias: `b5c44b6257bcd1b7030015545d9ba05de3d438719f0e5f708cc7f5442988254b`
- EVENT, 17 sentencias: `69b05982098854bd71e2fc091c411161fcbd5f4d6348c794af462d84b69ad47a`

Aplicación mediante `run_sql_transaction` en la **rama `br-soft-leaf-b59xcclw`** y únicamente a estas bases:
- `axs_corp_core_sbx`: 23 tablas, 23 con `relrowsecurity=true` y `relforcerowsecurity=true`; 5 políticas corporativas; 2 tipos enum.
- `axs_corp_gov_sbx`: 4 tablas, 4 con RLS habilitado y forzado, 3 tipos enum. **0 políticas operativas**, denegación predeterminada.
- `axs_corp_event_sbx`: 1 tabla, RLS habilitado y forzado; **0 políticas operativas**, denegación predeterminada.

Se consultó `EXISTS(SELECT 1 ... LIMIT 1)` sobre cada una de las 28 tablas; **ninguna contenía filas**. Verificación read-only de permisos del runtime: `axs_core_app` (CORE), `axs_corp_sandbox_gov` (GOV) y `axs_corp_sandbox_event` (EVENT) tienen **0 privilegios SELECT/INSERT/UPDATE/DELETE** en las respectivas tablas nuevas y no son dueños de ellas.

La instalación NO cargó datos, NO entregó permisos de aplicación, NO creó cuentas LOGIN, NO introdujo secretos y NO activó AXS Corporativo. Las bases históricas `neondb`, `aup_gov`, `aup_event`, la rama Neon production y San Luis no se modificaron.

**Bloqueo deliberado:** no habilitar backend ni dar de alta una empresa hasta diseñar/verificar los grants y políticas RLS mínimos por dominio, crear identidades completamente sintéticas, y resolver las credenciales limitadas de prueba. En particular, GOV/EVENT no tienen aún políticas RLS que autoricen operaciones; configurar una URL no solucionaría este control y sería una regresión de seguridad.

Railway `AXS Corporativo Sandbox` continúa staged sin despliegue; se exige nueva revisión de permisos, costos y privacidad antes de activar un runtime.
