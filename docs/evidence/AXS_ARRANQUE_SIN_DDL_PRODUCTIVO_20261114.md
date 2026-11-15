# Verificación productiva: arranque sin DDL

Fecha local: 14/11/2026, 21:27 CDMX. El usuario aplicó manualmente los dos cambios de fuente preparados para PR #114.

- Railway deployment: 93d1ad63-7259-40bf-beeb-f9250cd11ff9.
- Commit: 7ccef8e897d98555c0540aa8b03e0340102bf163.
- Proyecto: 532a32f5-6313-4ee3-98de-cfcfc225dbb7; production: 72f597ee-89d2-4dd4-9295-6618d3694d22; servicio web: 55c12ef5-ba69-449c-ad84-b77ee280eb5b.
- SUCCESS confirmado por API y deployment ACTIVE/Deployment successful confirmado en la interfaz.
- Una réplica ejecutándose, cero caídas/fallos recientes, sin trabajo pendiente ni advertencias/críticos de plataforma en la consulta posterior.

## Evidencia de arranque

Los registros del deployment muestran los gates CORE y esquema corporativo en PASS. El gate de permisos/configuración muestra Clerk PASS con issuer https://clerk.auth.axs-mx.com y clave fijada presente; EVENT PASS como axs_event_app y GOV PASS como axs_gov_app.

A las 03:27:25 UTC del 15/11 (21:27:25 CDMX del 14/11), el proceso registró para CORE, EVENT y GOV: «esquema administrado mediante migraciones; sin DDL de arranque». Posteriormente inició el worker de auditoría durable y completó el arranque de Uvicorn. La comprobación /health devolvió HTTP 200. No aparece el intento de CREATE TABLE identity_retention ni su error de permisos en los registros de este arranque (80 entradas solicitadas; respuesta contiene el predeploy y el arranque completo observado).

Permanece un UserWarning de configuración Pydantic V2 (`schema_extra`/`json_schema_extra`), distinto del aviso de DDL corregido. No impidió el arranque. No se afirma ausencia de cualquier advertencia futura.

## Alcance

La corrección sólo reserva el bootstrap automático para SQLite. PostgreSQL conserva migraciones explícitas y los gates previos, sin ampliar permisos. Durante esta publicación se cambiaron exclusivamente rama y commit de Railway; no se cambiaron variables, roles, tablas o datos. No se activó retención ni corporativo, ni se publicó frontend o se fusionaron PRs.

La aceptación residencial reportada por Salvador (sesión, consultas, reportes y ciclo de visita cerrado) corresponde al recorrido previo y está documentada en el commit 7ccef8e. No se repitieron operaciones de entrada/salida ni pruebas con datos personales durante esta comprobación del arranque.

CI del commit: cuatro corridas push/PR aprobadas; Python 1228 pruebas aprobadas y 96 omitidas, cobertura 82%; PostgreSQL y frontend aprobados. Las omisiones de Python incluyen pruebas que requieren entornos opcionales; las corridas PostgreSQL aportan su verificación específica. No se afirma cobertura de todos los servicios externos.

## Siguiente paso

Ejecutar la matriz corporativa con datos sintéticos y entorno aislado definida en docs/evidence/AXS_ACEPTACION_RESIDENCIAL_20261114.md del commit publicado. No se ejecutó ese ensayo como parte de esta publicación. Mantener separación entre aceptación residencial, arranque verificado y futura aceptación corporativa.
