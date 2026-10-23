# Ensayo aislado AXS Corporativo — Neon 23 octubre 2026

**Estado:** Migraciones C0/C1/C2 aplicadas únicamente en rama temporal de Neon, sin fusionar PR ni activar flags.

## Identidad y delimitación
- Proyecto: `MSP_AXS` (Neon project `patient-tree-68362559`)
- Rama fuente de desarrollo: `axs-development-20261002` (ID `br-blue-frog-b5o2ccsk`)
- Rama de ensayo: `axs-corporativo-c0-c2-ensayo-20261023` (ID `br-soft-leaf-b59xcclw`)
- Sin modificaciones a rama `production` ni a `main` GitHub. No se crearon datos reales de empresa, propietario o visitantes.

## Ejecución
Las instrucciones versionadas de:
1. `migrations/20261023_tenant_modalidad_c0.sql`
2. `migrations/20261023_corporate_directory_c1.sql`
3. `migrations/20261023_corporate_superadmin_c2.sql`

Se aplicaron en ese orden mediante sentencias dentro de transacciones. La API Neon no acepta múltiples sentencias en un solo comando preparado, por lo que se extrajeron los componentes del SQL y se enviaron al mecanismo de transacción de Neon. **No se cambió la semántica de las sentencias**.

## Verificaciones observadas
- Antes de migrar: `condominios_exo` existe; la columna `modalidad` no existía; 12 registros en la rama fuente copiada.
- Después de migrar: 12 filas `modalidad=residencial`, `corporativo_habilitado=false`. Ninguna reclasificación ni alta real.
- Tablas corporativas `corporate_organizations`, `corporate_sites`, `corporate_destinations`, `corporate_memberships`, `corporate_site_assignments`: cada una con `relrowsecurity=true`, `relforcerowsecurity=true` y una policy.
- `axs_corporate_provisioner` tiene `rolcanlogin=false`, `rolinherit=false`, `rolbypassrls=false`, `rolsuper=false`.
- `corporate_organizations` incorpora `privacy_contact`, `privacy_notice_url` y `privacy_notice_version`.

## Evidencia previa CI en PostgreSQL efímero
- [PR #100](https://github.com/B10sp4rt4n/MSP_AXS/pull/100): 585 pruebas de regresión generales y 90 pruebas PostgreSQL, incluida ruta HTTP integrada con rol restringido; navegador del Superadmin con datos ficticios.

## Pendientes bloqueantes
- Verificación end-to-end usando directamente la rama *Neon* de ensayo y su rol runtime efectivo; pruebas sintéticas CI no equivalen a desplegar backend en Neon.
- Inventario final de rutas residenciales ajenas al guard central.
- ARCO corporativo: tratamiento, conservación, borrado y responsable por empresa; no basta la presencia de un aviso.
- Revisión de activación y concilicación entre CORE y GOV. Las políticas y el alta están en bases separadas; no existe transacción distribuida.
- C0→C1→C2→C3 en GitHub se mantienen en PR draft escalonados, no fusionados ni desplegados. No activar flags ni configurar un provisioner con LOGIN productivo.

La rama de ensayo se conserva para verificación posterior, **no** para uso por el piloto residencial ni por empresas reales.


## Ampliación — verificación de credencial y entorno (23-oct-2026)
- Railway `AXS Development`: el backend actual pertenece a un entorno denominado `production` y su fuente es `feat/arco-expediente-asistido`. No se cambió la rama de origen, servicio, variables ni despliegue.
- La rama Neon del ensayo sí conserva el rol `axs_corporate_provisioner`, creado `NOLOGIN`. El intento de `SET LOCAL ROLE` con el propietario disponible devolvió *permission denied to set role*: no se forzó la asignación de membresía ni se elevó la cuenta propietaria para el ensayo.
- Inspección de privilegios con `has_table_privilege`: `corporate_memberships` SELECT/INSERT=true y DELETE=false; `visitas` SELECT=false; `event_outbox` INSERT=true y SELECT=false. El rol tiene `rolsuper=false`, `rolbypassrls=false`, `rolinherit=false`, `rolcanlogin=false`.
- Por ese motivo **no se certifica ejecución HTTP desplegada sobre esa rama Neon**, únicamente migraciones estructurales/privilegios observados, además de pruebas HTTP con PostgreSQL descartable en GitHub Actions.
- Condición para ensayo HTTP integral: backend desechable apuntando exclusivamente a la rama Neon de prueba, credencial de provisioner autorizada para ensayo bajo control del administrador de DB, fuentes GOV/Event de prueba, flags solo de ensayo y sin datos personales. No activar credenciales productivas para salvar este requisito.


## Preparación del backend Railway separado (23-oct-2026)
- Proyecto Railway independiente: `AXS Corporativo Sandbox`, id `cf44e5f4-1a41-4d25-a13e-a39211cda7b6`. Entorno `sandbox` id `cd1b2ff7-509e-4c6b-9ea0-c537295d4cd3`.
- Servicio `axs-corporativo-api-sandbox`, id `e395d483-dd09-4f50-a1e8-415787be5b30`.
- Se **prepararon cambios staged sin aplicar**: source `B10sp4rt4n/MSP_AXS` fijado al commit `1c182bdd4486dce6bed8cd1710c3d22c2493ee53`; builder Railpack, comando uvicorn, `/health` y checks previos de desarrollo/RLS.
- Flags preparados `AXS_CORPORATE_API_ENABLED=false`, `AXS_CORPORATE_PROVISIONING_ENABLED=false`, `AXS_CORPORATE_SANDBOX_ONLY=true`, `ENVIRONMENT=sandbox`.
- **NO se ha ejecutado accept-deploy.** El servicio no tiene instancias productivas ni dominio público. No se copiarán las credenciales ni variables del backend compartido de Railway.
- Pendiente preparar conexión aislada a rama Neon `br-soft-leaf-b59xcclw`, orígenes GOV/EVENT de prueba, credencial de provisioner (actualmente `NOLOGIN`), autenticación Clerk de prueba y revisión de costos antes de activar un servicio. No duplicar secretos al repositorio o al frontend.
- Si no se autoriza gasto computacional adicional, conservar staged sin deploy; la validación automatizada CI PostgreSQL ya aprobada continúa siendo la evidencia funcional disponible.


## Preparación de conexiones GOV / EVENT y predeploy (23-oct-2026)

**Sin despliegue ni uso de datos reales.** La rama de ensayo conserva datos heredados del desarrollo: NO es una base anonimizada ni se debe exponer por una API pública.

- Se verificó que `neondb`, `aup_gov` y `aup_event` existen en `br-soft-leaf-b59xcclw`. Contienen, respectivamente, 23, 4 y 1 tablas públicas.
- El mecanismo `create_postgres_role` de Neon **otorgó inesperadamente membresía `neon_superuser` y privilegios amplios** a dos roles recién creados. Intento de `REVOKE neon_superuser` fue denegado al propietario disponible. **Ambos roles se eliminaron de la rama aislada inmediatamente**; no se usaron y no se conectaron a Railway.
- Reemplazo con SQL explícito `CREATE ROLE ... NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`, sin membresías: `axs_corp_sandbox_gov` y `axs_corp_sandbox_event`. Verificada la ausencia de `neon_superuser` y todas las capacidades elevadas.
- GOV: rol `axs_corp_sandbox_gov` sólo SELECT de `authorities_gov` y SELECT/INSERT/UPDATE de `policies_gov`; sin DELETE ni modificación de autoridades o delegaciones.
- EVENT: rol `axs_corp_sandbox_event` sólo SELECT/INSERT de `events_aup` y USAGE de su secuencia; sin UPDATE, DELETE ni CREATE.
- Aislamiento cruzado comprobado: ninguna de estas cuentas puede leer `usuarios`, `visitas` ni `corporate_memberships` en CORE; el rol GOV no puede acceder a EVENT y el rol EVENT no tiene permisos sobre GOV.
- Ambas cuentas están `NOLOGIN`, por lo que **no existe todavía conexión funcional o contraseña que pueda llevarse a Railway**. No se modificó la cuenta `axs_corporate_provisioner`, que sigue `NOLOGIN`.
- En Railway sandbox se prepararon, sin aplicar: `APP_ENV=development`, `ENV=development`, `ENVIRONMENT=production` (para bloquear `/debug/db`), `NEON_DEV_ENDPOINT=ep-bitter-snow-b5sgxc4h`, flags corporativos apagados, orígenes restringidos a localhost, no fotos/ARCO/Cloudinary y no SQL echo.
- Se añadió `scripts/check_corporate_sandbox_config.py` con tests sintéticos: fail-closed ante URL de otra rama, roles owner, SSL ausente, Clerk live, secretos de sesión ausentes o funcionalidades activadas. El predeploy de Railway staged usa este control antes de `scripts/check_core_rls.py`.
- Pendientes: roles LOGIN creados con un método que NO asigne privilegios extra; secretos nuevos entregados por mecanismo seguro, **sin copiar contraseñas de desarrollo/productivo**; credenciales Clerk de prueba, nueva clave de sesión, validación de datos heredados y autorización de costo antes de accept-deploy.

Esta revisión es de **estructura y grants, no prueba de acceso como roles**: `NOLOGIN` y el propietario no autorizado para `SET ROLE` impiden probar conexiones reales a esta rama. El ensayo HTTP integrado continúa acreditado únicamente en PostgreSQL desechable de CI.
