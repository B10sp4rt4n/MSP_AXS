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
