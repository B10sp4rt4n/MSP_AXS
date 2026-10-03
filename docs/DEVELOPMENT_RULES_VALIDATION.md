# Validación de reglas en development — 3-oct-2026

## Actualización completada

Salvador autorizó explícitamente conectar ambos servicios de AXS Development al commit `2bc5cef4e44331c82b898e36a910caaee6dad9b7`.

| Servicio | Deployment | Estado |
| --- | --- | --- |
| Backend | `6a2a9004-1c29-4f27-b820-06eec2496c0f` | SUCCESS |
| Frontend | `594a1343-bd28-4542-b8b6-9d0f5539f577` | SUCCESS |

Fuente `B10sp4rt4n/MSP_AXS@main`, fijada al commit; futuros pushes no despliegan automáticamente estos servicios. Variables y conexiones de desarrollo preservadas. Predeploy de backend verificó endpoint independiente; worker de auditoría inició. Producción no se modificó durante esta actualización.

## Preparación inicial (histórica; ejecución completada abajo)

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

## Ejecución autorizada y cierre — 3-oct-2026, 22:43 UTC

Salvador autorizó explícitamente crear la función y los cambios temporales del ensayo después del rechazo inicial. Servicio `axs-development-rules-smoke` / `2ba158cd-83c2-4c05-8d49-c93f2c243061`, deployment `ac0b5298-49d1-4954-bf14-f2418236dda5`, Bun 1.4.0. Sin dominio/cron; restart NEVER. La creación inicial sin secreto sólo registró WAITING. La ejecución con referencia interna del secreto terminó PASS con 21 comprobaciones entre 22:43:44 y 22:43:58 UTC.

- GUARDIA no cambió reglas ni autorizó la visita: 403. Admin B no consultó reglas de A: 403.
- Creación con entrada inmediata sin propósito: 403 y cero visitas creadas por ese intento. Fixture con propósito pero sin autorización: entrada 403 y estado pendiente intacto.
- Admin A autorizó la fixture: 200, identidad y fecha persistidas. GUARDIA registró entrada 200; repetición 400; salida 200. Fixture final `salida_registrada`, con autorización, entrada y salida persistidas.
- Configuración efectiva anterior de A restaurada: propósito/autorización false y catálogo de tipos original. El JSON explícito reemplaza el NULL inicial con comportamiento equivalente. B conserva NULL. Las visitas originales A/B siguen pendientes sin autorización ni entrada/salida.
- Scope sintético REVOCADO al terminar; AXS_TEST_SECRET vaciado sin redesplegar. No hay reinicios automáticos. El script exige fixture nueva/pendiente antes de cualquier nueva ejecución.
- Producción verificada en sólo lectura: cero filas de esta identidad/visita sintética y cero reglas activas.

Auditoría directa CORE/EVENT: 8 hechos en event_outbox (5 éxitos: activar/restaurar configuración, autorizar, entrada, salida; 3 rechazos: propósito ausente, autorización ausente, doble entrada) y 3 hechos en security_outbox (2 ROLE_DENIED, 1 SCOPE_DENIED). Los 11 entregados en un intento, last_error NULL. Consulta en `aup_event.events_aup` por los 11 UID devolvió exactamente una copia de cada uno.

Este resultado valida API desplegada, persistencia y auditoría con JWT local breve. No acredita navegación ni autorización mediante sesión Clerk/UI, lectores físicos o biometría.
