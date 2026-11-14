# Aplicación parcial autorizada: permisos y deploy pendiente

14 de noviembre de 2026, 08:52 CDMX aproximadamente. Esta acta complementa, sin sustituir, el ensayo previo y la propuesta del PR #113.

El usuario autorizó aplicar el cambio preparado. Se confirmó el servicio Railway `web` en production, sin cambios ajenos pendientes, y el commit activo `a68d1149242dd0b16cd0e363df3ccda917199423`. Los gates CORE y esquema corporativo aprobaron antes del ajuste; las tres banderas corporativas permanecieron false.

## Ejecutado en Neon producción

- Proyecto patient-tree-68362559; rama br-empty-firefly-b5ob1gsg; endpoint ep-rough-voice-b5vx4odv.
- Snapshot inmediato snap-lingering-mode-b5o3j0mc, creado 2026-11-14T14:48:48Z; expira 2026-11-21T15:00:00Z. El snapshot anterior restaurado y ensayado sigue vigente.
- Se aplicaron las dos migraciones revisadas `20261114_event_runtime_permissions.sql` y `20261114_gov_runtime_permissions.sql` sin alteraciones.
- Se habilitó LOGIN con credenciales independientes para axs_event_app y axs_gov_app. Ambos quedaron NOINHERIT, NOBYPASSRLS, NOCREATEDB y NOCREATEROLE; las contraseñas no se registran en esta acta.
- FORCE RLS verificado: una tabla EVENT y cuatro tablas GOV.
- Conteos finales: 267 eventos, 1 autoridad, 6 políticas, iguales a los previos. No se crearon eventos ni cuotas sintéticas en producción.
- Inventario de conexiones observado: cliente EVENT como neondb_owner vía pgbouncer. Otros roles con LOGIN: axs_core_app y roles administrados de Neon; no se identificó otro cliente activo EVENT/GOV. axs_core_app pierde el acceso PUBLIC a estas dos bases por diseño; conserva su base CORE.

## Preparado en Railway, todavía sin aplicar

Servicio 55c12ef5-ba69-449c-ad84-b77ee280eb5b; entorno 72f597ee-89d2-4dd4-9295-6618d3694d22; patch 8edccdb7-28a3-4f3c-b249-a398814e9c7a, estado STAGED, 9 cambios de un único servicio, destructive=false.

- Cuatro variables: DATABASE_EVENT_URL y DATABASE_GOV_URL para los roles nuevos; CLERK_PUBLISHABLE_KEY de Production y CLERK_JWKS_URL de clerk.auth.axs-mx.com.
- Fuente fijada al commit probado 02667290d6a9e762818372459c7184c915988e87, en la rama fix/axs-corporativo-runtime-least-privilege-20261114. La revisión de Railway cuenta Branch, Commit Sha, Image y Repo como cuatro ajustes de fuente.
- Predeploy preparado: `python scripts/check_core_rls.py && python -m scripts.check_corporate_schema && python scripts/check_runtime_permissions.py`.
- CLERK_JWT_PUBLIC_KEY, CORE y banderas corporativas no se modificaron.

La llamada a accept_deploy fue rechazada por la revisión automática de aprobación: `Cancelled — the user did not approve this action. No changes were made.` No se reintentó por otra vía. El rechazo corresponde al commit/deploy de Railway; no revierte las operaciones Neon ya efectuadas.

## Estado comprobado al detenerse

Deployment activo be9b87a6-8a58-4341-a181-b4fc70ebd808 continúa SUCCESS, sin un despliegue nuevo. `/health` devolvió HTTP 200 desde el contenedor activo. La comprobación directa de los engines activos mostró EVENT=neondb_owner y GOV=neondb_owner: el servicio todavía no usa los roles nuevos y la alineación Clerk sigue pendiente de aplicar.

La pantalla de revisión quedó abierta con 4 variables y 5 ajustes. No debe confundirse el cambio ya aplicado en catálogo con la adopción efectiva de roles por el backend. Faltan la aprobación y ejecución del deploy y sus verificaciones posteriores: gates con conexiones runtime reales, salud, sesión Clerk y recorridos funcionales. No se realizó merge ni despliegue frontend.

La candidata conserva CI aprobado: Python 1226 pruebas (96 omitidas), cobertura 82%; PostgreSQL 16: 146 más 12 pruebas; PostgreSQL 18: 3; frontend y 13 recorridos sintéticos aprobados. Es evidencia previa de la candidata, no una aceptación productiva posterior al deploy.
