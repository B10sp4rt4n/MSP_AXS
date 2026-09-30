# Auditoría durable de visitas

CORE guarda la operación y un evento inmutable en `event_outbox` en la misma
transacción. Si no puede encolar el evento, revierte la operación. EVENT puede
estar temporalmente caído sin perder los hechos ya confirmados en CORE.

## Alcance

Creación de visita manual (incluida entrada inmediata), preregistro, creación o
regeneración de QR, entrada manual/QR, salida y cancelación por HTTP. Preregistro
guarda visita, metadata, QR y sus dos eventos en un solo commit.
También se conservan rechazos de validación QR: cancelado/finalizado, inválido,
expirado, usado, aún no vigente, conflicto al consumir y visita inexistente
(dentro de un condominio previamente autorizado). Entrada manual, salida,
cancelación y generación QR conservan sus rechazos por estado; creación de
visita y generación QR conservan la denegación de gobierno.
Sin sesión, sin autorización de condominio, preregistro y otros dominios aún
conservan el comportamiento anterior de rechazos. No se usa un tenant ficticio
ni se eleva el rol RLS para registrar intentos en una entidad ajena. No se resuelve aquí la repetición de creación
por una respuesta HTTP perdida, ni el funcionamiento sin conexión.

## Confirmación de rechazos

`rechazar_operacion` recibe sólo un condominio previamente autorizado. Copia la
identidad y hash de sesión, revierte la transacción de negocio pendiente, fija
el tenant RLS y confirma únicamente el evento. Así el rechazo permanece aunque
EVENT esté caído y no confirma accidentalmente una entrada o salida.
Si CORE falla al conservarlo, se responde 503 y el acceso continúa rechazado.
El motivo del rechazo de gobierno es fijo; no se guardan errores de conexión.
No se almacena el QR recibido, incluso para una visita desconocida.

Cada solicitud rechazada es un intento separado, con su propio UID. Los
reintentos del worker comparten UID; no se fusionan intentos reales distintos.
La auditoría de accesos sin sesión o sin alcance requiere un dominio de seguridad
separado: no debe perforar el aislamiento por condominio de esta bandeja.

## Envío y recuperación

Cada proceso del backend inicia un worker que revisa pendientes cada 15 segundos,
25 por condominio en cada ciclo. RLS fuerza el tenant en cada transacción;
`FOR UPDATE SKIP LOCKED` reparte filas entre workers. El evento usa siempre el
mismo `event_uid`, hora UTC e identidad; no conserva JWT ni secretos de QR.

EVENT hace INSERT con conflicto por UID y verifica el contenido existente. CORE
reconoce el envío sólo después del commit de EVENT. Un reinicio o pérdida del
ACK provoca reenvío sin duplicar el hecho. Los errores se reintentan con demora
exponencial hasta 256 segundos; no se descartan tras un número de intentos.
La bandeja almacena únicamente la clase del error para evitar revelar secretos.

## Despliegue y operación

Aplicar `migrations/20260930_event_outbox.sql` con propietario de CORE, primero
en la rama de pruebas y luego en producción, antes de desplegar el código.
`scripts/check_core_rls.py` exige RLS forzado, acceso de lectura/inserción y
actualización exclusiva de campos de entrega. El rol operativo no puede cambiar
payload, tenant, UID u hora del hecho, ni borrar o truncar filas.

Verificar pendientes con una sesión autorizada y `app.tenant_id` establecido:

```sql
SELECT count(*) AS pendientes, min(created_at) AS pendiente_desde,
       max(attempts) AS intentos_maximos
FROM event_outbox WHERE delivered_at IS NULL;
```

Los logs `axs.outbox` avisan errores de envío; un pendiente antiguo requiere
revisar disponibilidad de EVENT y la clase `last_error`. La bandeja conserva
también entregados; la retención debe definirse antes de crecer a gran volumen.
No hay endpoint público de inspección ni borrado automático.

## Pruebas

`tests/test_event_outbox.py` cubre rollback, caída de EVENT, demora de reintento,
pérdida de ACK, contenido conflictivo, tenant incorrecto y preregistro atómico.
El gate PostgreSQL corre con un rol sin bypass y FORCE RLS: dos workers compiten
por los mismos pendientes, otra entidad no puede leerlos y un reinicio no duplica.

`tests/test_rechazos_durables.py` cubre las causas de rechazo, independencia de
EVENT, rollback de negocio pendiente, fallo de CORE, conflicto de consumo,
condominio ajeno/inexistente y reenvíos sin duplicar intentos. El gate PostgreSQL
incluye un rechazo confirmado tras rollback, aislado por FORCE RLS, que compite
con eventos exitosos en el mismo envío concurrente.
