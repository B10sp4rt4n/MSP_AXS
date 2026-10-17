# Autorización remota desde la app del residente

Base revisada: main a50841a (#75), que incluye #74. No había solicitud remota implementada ni PR posterior visible al comenzar esta revisión.

## Experiencia

1. Caseta conserva el destino elegido en «¿A quién visita o a qué casa va?».
2. «Solicitar autorización sin QR» identifica al visitante por nombre completo, tipo y motivo. El catálogo y el servidor resuelven la vivienda; no se aceptan números de vivienda libres ni destinatarios elegidos por el guardia.
3. AXS guarda una visita pendiente y una solicitud durable en la misma transacción que su auditoría. Si existe una visita compatible sin QR, la reutiliza.
4. Los residentes elegibles ven la solicitud en su app abierta, que consulta cada cinco segundos. No hay push fuera de la app en esta entrega, ni confirmación de lectura o entrega a un teléfono.
5. El residente elige Permitir entrada o Rechazar entrada y confirma persona, vivienda y decisión. La confirmación consiente registrar ese acto en AXS; no habilita consentimiento de canales externos.
6. Caseta consulta el resultado. Permitir ofrece «Revisar para confirmar entrada», que recupera la ficha existente. El guardia conserva el botón de confirmación del movimiento físico y la captura de identificación existente.

Los botones existentes no cambian sus dimensiones. Las acciones nuevas reutilizan min-h-12, px-4 y py-3 de caseta. El guardia no calcula tiempos: ve espera, permiso, rechazo o vencimiento.

## Contrato y estados

- POST /solicitudes-acceso/{condominio_id}: UUID de idempotencia, destino_id, nombre_visitante, tipo_visita, proposito y visita_id opcional.
- GET de la colección: bandeja autenticada y recuperación después de recargar; hasta 100 solicitudes recientes, filtradas por residencia en servidor. La interfaz muestra las 15 más recientes del contexto.
- GET /{solicitud_id}: recuperación de un intento de envío incierto.
- POST /{solicitud_id}/respuesta: decision estrictamente permitida/rechazada, consentimiento booleano verdadero.
- Las respuestas no exponen la lista de destinatarios, claves o contactos externos. Cache-Control: private, no-store.

Estados: pendiente → permitida/rechazada/expirada. permitida → consumida/expirada. Consumida significa que caseta confirmó la entrada. La visita conserva los estados físicos existentes.

La solicitud vence cinco minutos después de crearse; el permiso debe consumirse antes de esa misma fecha. Es un valor inicial de implementación, no una preferencia histórica atribuida al usuario. No se extiende por consultar, reintentar o responder. El reloj del servidor gobierna las decisiones y entradas; el reloj del navegador sólo oculta botones vencidos.

El vencimiento impide actuar aun si no se ejecutó ninguna tarea de fondo. Su cambio auditable a expirada se materializa al consultar/responder/reintentar. Una renovación explícita tras vencimiento crea otro ID conservando la visita y limpia la autorización anterior. Un rechazo no se puede sustituir desde esta ruta.

## Autorización y aislamiento

- Sesión AUP obligatoria, autorización del condominio y contexto RLS antes de leer negocio. El middleware de recuperación existente sigue aplicándose.
- Creación limitada a caseta/administración con scope suficiente y gobierno crear_visita.
- Destinos exclusivamente del catálogo de viviendas de ese condominio. Áreas comunes y OTRO no tienen respuesta por un residente.
- Destinatarios fijados al crear: usuarios RESIDENTE en casa_id y condominio exactos, etiqueta de vivienda consistente, scope RESIDENTE activo y procedencia de contrato vigente.
- Se revalida residencia/scope/contrato al leer, responder y consumir el permiso. Un nuevo ocupante no hereda solicitudes dirigidas al ocupante anterior. Los administradores y guardias no pueden responder en nombre de un residente por esta ruta.
- La primera decisión válida gana; una repetición de la misma decisión por su mismo autor es idempotente. Otra decisión o autor obtiene conflicto.
- Las filas del condominio serializan creación/respuesta/entrada. Los cambios de solicitud y de movimiento usan actualizaciones condicionadas, no sólo validación en memoria.
- Se rechaza sustituir una visita con QR obligatorio, incluso vencido. También se rechazan entradas abiertas y coincidencias ambiguas o de otra vivienda. Comparación de nombres normaliza espacios, mayúsculas y acentos.
- La comparación de nombres es un control de duplicados, no una prueba de identidad. No detecta alias o nombres deliberadamente distintos. El guardia debe seguir verificando a la persona y recuperando su registro; esta entrega no introduce una identidad biométrica del visitante.
- Las autorizaciones remotas no pueden utilizar el endpoint genérico de autorización ni convertirse a QR. Su entrada requiere permiso vigente incluso cuando las reglas opcionales del condominio no exijan autorización.
- No se configura ni modifica Alexa, WhatsApp, consentimientos de vinculación o cuentas reales.

## Recuperación y auditoría

El cliente conserva el mismo UUID y cuerpo mientras un envío es incierto. Consulta ese ID antes de dar el envío por confirmado; un reintento exacto recupera el registro sin crear otra visita. Si se recarga la app, la bandeja durable permite recuperar solicitudes guardadas; el cotejo servidor evita duplicar una solicitud activa del mismo visitante/destino aunque se genere otro UUID.

Una respuesta perdida se resuelve consultando el estado; no se interpreta como rechazo ni como permiso. Sin comunicación no aparece una autorización nueva. El permiso requiere revalidación servidor en el movimiento. La recuperación de entrada y el compare-and-set de #74 permanecen.

Solicitud, decisión, vencimiento observado y consumo se registran en EventOutbox con identidad, sesión hasheada, destino, visita, estado, expiración y canal app. El consumidor EVENT existente reintenta su publicación. Los datos de negocio y auditoría confirman juntos. La tabla de solicitudes conserva destinatarios y autor/hora/consentimiento de la respuesta.

## Migración y revisión antes de producción

Este PR no despliega ni ejecuta migraciones reales. Aplicar migrations/20261017_solicitudes_acceso.sql en CORE antes de desplegar el backend: incorpora dos columnas de visitas y tabla de solicitudes con RLS forzado, validación de tenant/visita/destino, restricciones de estados y permisos SELECT/INSERT/UPDATE para axs_core_app. No concede DELETE/TRUNCATE.

Orden de entrega: probar migración en una base desechable → revisar CI PostgreSQL/navegador → aplicar migración aprobada → backend → frontend → aceptación con dos viviendas y dos residentes. Si se revierte código, conservar tabla y columnas para no perder evidencia.

Pruebas sintéticas: tests/test_solicitudes_acceso.py; tests/smoke/test_solicitudes_acceso_postgres.py; frontend-next/tests/solicitudes-acceso.browser.cjs; ampliación de guardia-flow.test.cjs. La prueba PostgreSQL ejecuta la migración dos veces en un esquema desechable y comprueba aislamiento; otra prueba usa dos sesiones concurrentes para respuestas opuestas. CI incorpora ambas.

## Extensión posterior de canales

| Canal | Primer incremento propuesto | Respuesta posterior | Requisito previo |
| --- | --- | --- | --- |
| App | Bandeja durable implementada | Sesión AUP y confirmación explícita implementadas | App abierta; aceptación operativa |
| WhatsApp | Aviso mínimo con enlace autenticado a la solicitud en AXS | Adaptador verificado que traduzca una decisión al mismo servicio, sin autorizar por texto libre | Cuenta/proveedor configurados, vinculación verificada, consentimiento específico, revisión de políticas y firma de webhooks |
| Alexa | Aviso genérico opcional para abrir AXS | Diseñar por separado autenticación suficiente de quien responde; un Echo compartido no acredita al residente que habla | Vinculación/consentimiento vigente, capacidades permitidas verificadas y pruebas físicas; no asumir certificación o activación |

Para cualquier canal futuro: outbox de entrega separado con intentos, vencimiento y claves idempotentes; revalidación de residencia y consentimiento antes de enviar; detener reintentos al vencer o decidir; no incluir tokens de acceso en enlaces o mensajes. Un acuse del proveedor no es lectura ni autorización. Toda respuesta mantiene la misma transición atómica y nunca registra entrada automáticamente.
