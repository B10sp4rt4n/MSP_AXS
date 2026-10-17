# Integración Alexa: PR #63 + #64

## Revisión del 17 de octubre de 2026 (UTC)

Base: `932af04842d907af10b117529c0ec222680226ef`.
PR #63: `e8784ca9b71d8a95937d51eb3b7af7ec4da4194f`.
PR #64: `c6f002c2d4453f1015fd0e201f482eca3baa4f6e`.
Ambos abiertos al revisar. Esta rama incorpora los cambios de ambos PR y la reconciliación;
no fusiona main ni activa banderas ni modifica datos de un condominio.

## Comparación de los tres archivos compartidos

| Archivo | #63 | #64 | Resultado |
| --- | --- | --- | --- |
| backend/routers/alexa_router.py | Resuelve identidad OAuth, valida residencia vigente, eventos de vinculación y desconexión | Consulta por hora de movimiento, incluye salidas recientes con entrada antigua | Merge textual limpio. La identidad determina tenant/casa antes del filtro de visitas; se conservan ambas condiciones y auditoría previa a la respuesta |
| backend/services/alexa_notifications.py | Rama beta con destinatarios vinculados, autorización fresca; solo entradas | Entradas/salidas y referencia por movimiento en piloto | Conflictos de texto en descripción y final del módulo; además incompatibilidad funcional: la rama beta retornaba antes de procesar salidas y su emisor fijaba `entrada` |
| docs/alexa-piloto.md | Delimita piloto con linking=false y remite a beta | Documenta salidas, última actividad y hora | Merge limpio pero insuficiente: actualizar alcance inicial y también docs/alexa-beta.md, que aún prometía solo entradas |

## Correcciones

- Validar estado y hora del movimiento antes de bifurcar piloto/beta. Mantener requisito de entrada confirmada para salida.
- Copiar el movimiento como escalar a la tarea beta. Generar referencias distintas para entrada/salida de la misma visita.
- Conservar sesiones nuevas, consentimiento, suscripción, recovery gate y autorización de residencia/scope/contrato en cada envío beta.
- Revalidar también tenant/casa del registro Alexa recargado: pudo cambiar después de enumerar destinatarios.
- Mantener consulta OAuth sin fallback al piloto, ventana de 24 horas por movimiento y filtros simultáneos de condominio, vivienda y tipo de destino.
- Actualizar pruebas beta para ambos movimientos y documentación de ambos modos.
- Actualizar la llamada directa de `test_visit_routes_apply_boundary_before_mutation` por la nueva firma con BackgroundTasks; comprobar que una denegación no encola avisos. La primera suite completa descubrió este fallo de fixture (502 passed, 22 skipped, 1 failed), ya corregido.

## Orden recomendado y aceptación

1. Revisar y fusionar #64 primero: cambio funcional acotado al piloto existente; OAuth permanece apagado.
2. Integrar #63 junto con esta reconciliación, nunca #63 sin corregir su ruta de avisos. Esta rama contiene ambos PR y puede ser el PR de integración después de #64; #63 quedará contenido en ella. Alternativamente aceptar esta rama como integración conjunta y cerrar los originales como incorporados, tras revisión.
3. Mantener `AXS_ALEXA_LINKING_ENABLED=false`. Antes de habilitar una beta limitada: migración aditiva y privilegios en entorno de prueba, configuración Clerk/Amazon y aceptación física.
4. No ampliar residentes por haber pasado pytest. Conservar allowlist explícita y verificar dos viviendas controladas antes de invitar más usuarios.

## Verificación automatizada

Pruebas locales con SQLite en memoria, firmas de una CA sintética y transporte/introspección simulados. Ninguna autenticación de residente real ni llamadas proactivas a Amazon.

- Ambas modalidades conservan entrada y salida; la salida requiere hora y tiene referencia distinta.
- Ruta de salida confirma CORE antes del aviso y rechaza repetir la transición sin otro aviso.
- OAuth devuelve solo movimientos de la vivienda autorizada, aunque otra casa/condominio tenga una salida más reciente.
- Salida reciente de visita que entró días antes; entradas sin salida y ventana de consulta existente.
- Denegación por scope revocado, residencia cambiada, token inválido, cuenta deshabilitada y origen contractual obsoleto.
- Revalidación de permisos y residencia al ejecutar tareas; cambio de vínculo entre enumeración y recarga.
- Pruebas existentes de firma, auditoría, recovery, revocación y eventos fuera de orden.

Las pruebas no acreditan RLS ni locks/concurrencia de PostgreSQL. Tampoco garantizan entrega: sigue siendo best effort, sin cola durable; HTTP 202 solo acredita aceptación. Una revocación concurrente posterior a la última validación no puede retirar un envío ya iniciado.

## Verificaciones pendientes fuera de pytest

- Migración/privilegios, RLS y concurrencia en PostgreSQL aislado; no ejecutar contra registros reales.
- Clerk: cliente OAuth, redirects, scopes, introspección y autenticación de cada residente.
- Amazon: Account Linking, eventos de ciclo de vida, permisos y suscripciones, certificado/endpoint y modelo de invocación «mis visitas».
- Echo real con dos cuentas/viviendas controladas: entrada, salida, hora CDMX, consulta de salida reciente con entrada antigua; confirmar ausencia de aviso/lectura cruzada.
- Desvincular, revocar permiso, cambiar residencia y repetir; comprobar bloqueo efectivo, además de continuidad de registros cuando Alexa falla.
- Mantener endpoint stages/development. Certificación y despliegue masivo fuera de esta integración.

Resultado focalizado final: **103 passed** (Alexa + prueba de aislamiento de salida), 15.82 s. Comando: `python -m pytest tests/test_msp_boundary.py::test_visit_routes_apply_boundary_before_mutation tests/test_alexa_linking.py tests/test_alexa_notifications.py tests/test_alexa_voice.py -o addopts='' -q`.

Suite completa final: **503 passed, 22 skipped**, 51.01 s. Comando: `python -m pytest tests/ -o addopts='' -q`. Las omisiones no se consideran verificaciones aprobadas. `git diff --check` sin incidencias.
