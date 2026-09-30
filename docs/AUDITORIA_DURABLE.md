# Auditoría durable de visitas

CORE guarda la operación y un evento inmutable en `event_outbox` en la misma
transacción. Si no puede encolar el evento, revierte la operación. EVENT puede
estar temporalmente caído sin perder los hechos ya confirmados en CORE.

## Alcance

Creación de visita manual (incluida entrada inmediata), preregistro, creación o
regeneración de QR, entrada manual/QR, salida y cancelación por HTTP. Preregistro
guarda visita, metadata, QR y sus dos eventos en un solo commit.
Las denegaciones y otros dominios conservan el registro directo anterior y
todavía no tienen esta garantía. No se resuelve aquí la repetición de creación
por una respuesta HTTP perdida, ni el funcionamiento sin conexión.

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
