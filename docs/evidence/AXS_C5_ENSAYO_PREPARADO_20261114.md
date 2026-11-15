# AXS C5 — preparación del ensayo, 14 de noviembre de 2026 (CDMX)

## Código y validación
PR: https://github.com/B10sp4rt4n/MSP_AXS/pull/116
SHA: 08e8e5e15d2421bd2cfe11078f334778ad51bfd2. Base: PR #115.

- Tests CI https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43678173885: todos los jobs aprobados; Python 1243 aprobadas, 108 omitidas, cobertura 82%; navegador y frontend aprobados.
- PostgreSQL CI https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43678173873: todos los jobs aprobados; PostgreSQL 16: 158 aprobadas y 12 de migraciones; PostgreSQL 18: catálogo y C5 aprobados.
- Local: suite 1243 aprobadas, 108 omitidas. La nueva prueba PostgreSQL verifica rechazo de constancia vencida/emisor distinto, conservación de datos y fechas, permisos y rechazo de repetición.

## Migración efectivamente aplicada
Proyecto Neon patient-tree-68362559, rama br-soft-leaf-b59xcclw, base axs_corp_core_sbx_20261114, endpoint exclusivo de ensayo. No se modificó producción.
Se aplicó la migración 20261115_corporate_visits_c5.sql con el rol fijo axs_corp_sandbox_core_20261114 en lugar de axs_core_app.
Se conservaron la certificación inicial, run_id, emisor, datos y vencimiento. Sólo se actualizó el hash del catálogo:
- Antes: a5e70427b827762d98cc56f987ca715367f21ea4df0a05739a1d8c5c0172ff3b
- Después: c5c786302873655b34705c7b1aac5ea062c6fdabce9898b5fd8b24c84f76b350
- Certificación inicial: 2026-11-14T12:06:34.916Z
- Vencimiento: 2026-11-15T12:06:34.916Z (15 de noviembre, 06:06 CDMX).

El acceso TCP desde el ejecutor no resolvió DNS. Se usó la conexión administrada de Neon. La fórmula SQL de serialización/hash se cotejó contra la fórmula Python y la constancia existente antes de migrar. La transacción guardó base, propietario, run_id, emisor, vigencia y hash previo; todo el DDL y la actualización del hash quedaron en una transacción.
El primer intento de gateway rechazó múltiples comandos preparados y revirtió todo. Se verificó tabla ausente/hash anterior antes del segundo intento, que separó las sentencias sin romper el bloque DO y confirmó exitosamente.
El archivo JSON adjunto conserva las sentencias exactas; no contiene credenciales.

Verificación posterior mediante conexión del rol runtime real: hash coincide con la constancia, cero filas sin contexto tenant, SELECT/INSERT permitidos, DELETE/TRUNCATE denegados y sólo seis columnas mutables (estado, autorizador y horarios).

## Railway: preparado, NO desplegado
Proyecto AXS Corporativo Sandbox cf44e5f4-1a41-4d25-a13e-a39211cda7b6.
Entorno sandbox cd1b2ff7-509e-4c6b-9ea0-c537295d4cd3.
Patch 45565227-ab2b-4f73-b50c-b8272cea53bb: 9 cambios pendientes, backend y frontend fijados al SHA indicado y AXS_CORPORATE_VISITS_ENABLED=true únicamente en sandbox.
Pantalla verificada: muestra Apply 9 changes y botón Deploy.

La llamada accept-deploy fue rechazada por la revisión automática: “Cancelled — the user did not approve this action. No changes were made.” No se intentó desplegar por otra vía. El rechazo se refiere al despliegue; la migración anterior sí quedó confirmada.
Los servicios siguen con su despliegue anterior a2b88a34f2141b36dcde8d8d5630d5ae2c254c18 hasta que el usuario aplique Deploy. Completar el despliegue es necesario antes de verificar el nuevo arranque con el catálogo actualizado. Desactivar sólo la bandera no deshace el cambio de catálogo del sandbox.

## Producción y pendientes
Producción sigue en deployment 93d1ad63-7259-40bf-beeb-f9250cd11ff9, SHA 7ccef8e897d98555c0540aa8b03e0340102bf163. Sin merge ni activación C5 productiva.
Pendiente: el usuario pulsa Deploy en el entorno sandbox; verificar salud/predeploy y después inicio de sesión Clerk real, folio sintético, autorización, entrada, salida y bitácora.
No se declara completada esa aceptación real. Sin nombres/documentos/fotos/QR, apertura física, aforo o caducidad automática. La constancia no se renovó ni se convirtió en una nueva certificación de vacío.
