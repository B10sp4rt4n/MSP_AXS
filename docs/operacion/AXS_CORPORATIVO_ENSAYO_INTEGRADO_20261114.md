# Ensayo integrado corporativo — preparación 14 noviembre 2026

El sandbox publicado conserva una constancia inicial que venció el 28 de octubre. El candidato integrado no debe arrancar contra ese conjunto poblado ni renovar artificialmente su certificado. Se añade un perfil explícito `integrated-20261114`, exclusivamente en fase runtime del sandbox, para otro conjunto vacío en el mismo endpoint de ensayo `ep-bitter-snow-b5sgxc4h`.

| Dominio | Base nueva | Rol runtime nuevo |
| --- | --- | --- |
| CORE | axs_corp_core_sbx_20261114 | axs_corp_sandbox_core_20261114 |
| GOV | axs_corp_gov_sbx_20261114 | axs_corp_sandbox_gov_20261114 |
| EVENT | axs_corp_event_sbx_20261114 | axs_corp_sandbox_event_20261114 |
| Aprovisionamiento CORE | axs_corp_core_sbx_20261114 | axs_corporate_provisioner_20261114 |

Los nombres no son libres ni se obtienen de parámetros de usuario. Perfil omitido conserva el contrato anterior; un perfil desconocido falla. Fuera del sandbox, la credencial de aprovisionamiento sigue exigiendo el rol productivo original. Los controles de TTL, issuer Clerk Development, huella de catálogo, permisos, NOINHERIT, ausencia de propiedad/DDL y FORCE RLS se conservan.

## Procedimiento

1. Validar CI del SHA exacto, incluidos ambos perfiles y PostgreSQL real descartable.
2. Comprobar que no existen las nuevas bases/roles. Crear únicamente estas tres bases en la rama `br-soft-leaf-b59xcclw`, con propietario `neondb_owner`; no crear otro endpoint ni otro servicio.
3. Instalar el DDL del ORM y las migraciones C2/C4 y permisos del bundle `python -m scripts.prepare_integrated_sandbox_bundle`. El render sustituye únicamente identificadores fijos por los del perfil nuevo. No reutiliza el histórico de enmienda de certificados del 27 de octubre. Inicialización de una sola aplicación: ante fallo parcial, inspeccionar; no repetir a ciegas.
4. Verificar los cuatro contratos de permisos; certificar vaciedad con UUID nuevo, issuer existente de prueba y TTL de 24 horas antes de sembrar filas. La certificación usa el script original con el perfil nuevo y no modifica la constancia anterior.
5. Registrar sólo los tres subjects Clerk Development ya utilizados, con datos sintéticos, el MSP de ensayo y una autoridad GLOBAL. Las empresas y directorios se crean mediante la API del candidato, no copiando tenants anteriores.
6. Habilitar LOGIN y contraseñas independientes únicamente en los cuatro roles nuevos y transportar sus URLs al backend por variables secretas. No copiar credenciales de propietario al runtime ni rotar las del ensayo anterior.
7. Preparar backend y frontend del sandbox con el mismo SHA fijado. Conservar dominio, Clerk Development y CORS. Backend: perfil nuevo, UUID, conexiones nuevas y gates de configuración/datos. Frontend: código integrado; mismo API de sandbox. No cambiar aliases Vercel ni producción.
8. Revisar diff de infraestructura y publicar coordinadamente sólo en sandbox. Observar SUCCESS, gates y salud; repetir autenticación/permiso propio/cruzado, alta de A/B, cuotas y conciliación sobre ese SHA.

## Recuperación

Los datos y credenciales anteriores se conservan. Una reversión al backend anterior contra su certificado vencido no es una recuperación ejecutable: no prometerla ni redeplegarlo como si fuese válida. Antes de publicar debe existir una alternativa de aplicación ensayada sobre las bases nuevas con certificado vigente, o detener el avance en preparación. Un fallo del gate impide habilitar el nuevo ensayo. No borrar bases, certificados o journal para resolverlo.

La preparación de código y las pruebas no equivalen a publicación ni a recorrido autenticado del candidato. El resultado remoto y los SHA/despliegues deben registrarse en el PR antes de dar el ensayo por completado.
