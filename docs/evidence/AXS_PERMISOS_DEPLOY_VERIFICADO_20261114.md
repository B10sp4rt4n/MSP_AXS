# Deploy de permisos EVENT/GOV y Clerk verificado

14 de noviembre de 2026. Aplicación completada por el usuario en Railway y verificada después del arranque. Esta acta sucede a `AXS_APLICACION_PARCIAL_ROLES_20261114.md`: conserva aquel bloqueo como hecho histórico, pero el deploy ya no está pendiente.

## Versión y plataforma

- Railway proyecto 532a32f5-6313-4ee3-98de-cfcfc225dbb7, entorno production 72f597ee-89d2-4dd4-9295-6618d3694d22, servicio web 55c12ef5-ba69-449c-ad84-b77ee280eb5b.
- Deployment cf190d6b-5162-4611-a786-b35f842568f6, commit fijado 02667290d6a9e762818372459c7184c915988e87, rama fix/axs-corporativo-runtime-least-privilege-20261114.
- Iniciado 09:08:50 CDMX; SUCCESS a las 09:12:14 CDMX. Una réplica ejecutándose, cero caídas, cero fallos recientes y cero advertencias/críticos de plataforma en la consulta posterior. No quedó trabajo pendiente ni cambios staged.
- El usuario pulsó Deploy Changes después de tomar el control de la pantalla. No se sorteó el rechazo de aprobación del conector.

## Comprobaciones efectivas

El predeploy ejecutó y aprobó `scripts/check_core_rls.py`, `scripts.check_corporate_schema` y `scripts/check_runtime_permissions.py`.

Además se repitió el gate EVENT/GOV/Clerk desde la consola del contenedor del deployment nuevo. Las consultas usaron conexiones reales con sus credenciales runtime y transacciones de sólo lectura, sin SET ROLE ni credenciales administrativas.

| Dominio | Base efectiva | Usuario efectivo | Resultado |
| --- | --- | --- | --- |
| CORE | neondb | axs_core_app | Gate CORE aprobado |
| EVENT | aup_event | axs_event_app | Contrato de permisos y FORCE RLS aprobado |
| GOV | aup_gov | axs_gov_app | Contrato de permisos y FORCE RLS aprobado |
| Clerk | clerk.auth.axs-mx.com | Production | Gate de alineación aprobado |

La obtención real de JWKS desde Clerk fue exitosa. La clave RSA pública fijada en el backend coincide con una de las claves de la respuesta JWKS (comparación de n/e, sin registrar el material de la clave). La clave fijada se conservó. Esto acredita alineación y disponibilidad del material de verificación, no una sesión JWT real de un usuario.

`/health` devolvió HTTP 200 tanto por loopback del contenedor como por el dominio público Railway. Las banderas AXS_CORPORATE_API_ENABLED, AXS_CORPORATE_PROVISIONING_ENABLED y AXS_CORPORATE_SANDBOX_ONLY siguen false. No se activó el negocio corporativo ni se desplegó el frontend.

Lectura administrativa posterior en Neon: 267 eventos, 1 autoridad y 6 políticas. Coinciden con los conteos previos al cambio. Las verificaciones no insertaron visitas, eventos ni cuotas sintéticas en producción.

## Aviso heredado de arranque

El arranque registró `permission denied for schema public` al intentar CREATE TABLE identity_retention desde Base_CORE.metadata.create_all. El código de ese intento y su captura no cambiaron frente al commit anterior a68d1149242dd0b16cd0e363df3ccda917199423. La comparación de las tablas de Base_CORE contra el catálogo efectivo señaló únicamente identity_retention como ausente.

Se confirmó por las funciones efectivas del servicio que schema_enabled=false y pilot_enabled=false para retención de identidades. Este módulo está limitado al entorno de desarrollo identificado por su configuración. El servidor terminó de arrancar y la auditoría durable inició. No se concedió CREATE al runtime, no se creó la tabla ni se activó el módulo como respuesta al aviso. Queda como deuda de inicialización heredada, separada de este ajuste de permisos.

## Límites y siguiente aceptación

Pendiente: inicio de sesión Clerk real y recorridos de administrador/guardia/residente, bitácora, reporte y una operación de acceso con evidencia. Las pruebas previas CI/simulación y el gate productivo no sustituyen esta aceptación funcional. No se afirmó validación de cámara, Blob ni recuperación de sus binarios.

Respaldo previo a las migraciones: snapshot Neon snap-lingering-mode-b5o3j0mc, vigente hasta 21/11/2026 09:00 CDMX. Se conserva también el snapshot previo restaurado y ensayado. No se modificaron secretos, permisos ni configuración adicionales durante esta verificación posterior.
