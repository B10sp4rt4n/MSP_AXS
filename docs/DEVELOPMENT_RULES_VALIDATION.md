# Validación de reglas en development — 3-oct-2026

## Actualización completada

Salvador autorizó explícitamente conectar ambos servicios de AXS Development al commit `2bc5cef4e44331c82b898e36a910caaee6dad9b7`.

| Servicio | Deployment | Estado |
| --- | --- | --- |
| Backend | `6a2a9004-1c29-4f27-b820-06eec2496c0f` | SUCCESS |
| Frontend | `594a1343-bd28-4542-b8b6-9d0f5539f577` | SUCCESS |

Fuente `B10sp4rt4n/MSP_AXS@main`, fijada al commit; futuros pushes no despliegan automáticamente estos servicios. Variables y conexiones de desarrollo preservadas. Predeploy de backend verificó endpoint independiente; worker de auditoría inició. Producción no se modificó durante esta actualización.

## Ejecución propuesta, todavía NO realizada

`scripts/development_rules_smoke.ts` es un ejecutor único para Railway/Bun, sin servidor, dominio ni cron. API y endpoint de development fijos. JWT local de cinco minutos con identidades permitidas explícitas; el backend resuelve sus permisos actuales. No imprime tokens ni secretos. No valida creación ni navegación mediante Clerk.

La revisión automática rechazó crear la función `axs-development-rules-smoke`: consideró no aprobada la infraestructura nueva y sus cambios operativos temporales. No se creó ese servicio ni se ejecutó el flujo. El alcance pendiente de autorización es:

1. Crear esa función exclusivamente en Railway proyecto `c04faff4-37ba-4df4-a6ce-a4d5d5ff881b`, environment `5f5b4e0c-c4ce-457c-96a4-b65ebf723354`, sin dominio/cron y restart NEVER.
2. Activar únicamente scope GUARDIA de la identidad sintética `axs_rules_guard_20261003` para `axs_demo_condo_a`. Refrescar vigencia de `axs_rules_visit_20261003` inmediatamente antes del ensayo, sin modificar las visitas originales.
3. Inyectar `AXS_TEST_SECRET` mediante referencia interna a SECRET_KEY del backend de development. Nunca copiar credenciales al repositorio ni a logs.
4. Ejecutar: verificar identidades y reglas apagadas; activar propósito/autorización sólo en A; comprobar que guardia no cambia reglas ni autoriza; rechazo cruzado B→A; creación inmediata sin propósito rechazada; entrada de fixture con propósito pero sin autorización rechazada; autorizar como Admin A; entrada GUARDIA permitida; segunda entrada rechazada; salida permitida.
5. El bloque finally restaura la configuración efectiva anterior de A; B debe permanecer igual. La configuración original era SQL NULL; el PUT escribe su equivalente explícito con ambas reglas apagadas. El runner no modifica visitas ajenas ni crea visitas adicionales.
6. Comprobar en CORE/EVENT las identidades, estados, eventos entregados y UID sin duplicados. El runner sólo confirma respuestas y persistencia mediante API, no certifica por sí mismo la entrega outbox.
7. Revocar el scope sintético, vaciar AXS_TEST_SECRET sin redesplegar y confirmar reglas apagadas y ambas visitas originales pendientes. Conservar el registro de prueba finalizado y la identidad revocada como evidencia, sin borrar auditoría.

## Preparación y estado seguro

Fixtures preparadas únicamente en `patient-tree-68362559`, rama development `br-blue-frog-b5o2ccsk`, CORE `neondb`. Se añadió una identidad GUARDIA sin contraseña/Clerk y una visita pendiente sin autorización: `axs_rules_visit_20261003`, proveedor, casa A 101, propósito de validación. No se agregaron membresías MSP ni permisos administrativos.

Tras el rechazo, el scope GUARDIA quedó REVOCADO. La visita nueva y las originales `axs_demo_visit_a` y `axs_demo_visit_b` siguen pendientes, sin autorización ni entrada/salida. No se cambiaron reglas del condominio.

Una ejecución concluida no debe repetirse: el script exige fixture pendiente y fecha reciente. PASS/FAIL se interpreta en `AXS_RULES_RESULT`; la salida de proceso no dispara reintentos automáticos de mutaciones. Restauración fallida requiere revisión directa de la configuración antes de reintentar.
