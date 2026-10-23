# Expediente ARCO asistido: primera implementación

Estado: backend preparado y probado localmente; no desplegado ni activado. Complementa la matriz del PR #89. No reemplaza el procedimiento público ni acredita cumplimiento ARCO integral.

## Alcance

Registro privado por tenant con UUID de folio suministrado por el operador, recepción original, derecho, referencia opaca al titular, responsable de seguimiento, vencimiento de determinación, decisión, ejecución, pendientes e historial. No recibe documentos ni direcciones de correo; las referencias apuntan al expediente privado custodiado por el responsable. No colocar nombres, tokens o URLs de documentos en referencias. `owner_id` identifica al responsable asignado en ese expediente externo; no otorga acceso al sistema.

El acceso requiere autenticación, rol administrativo, alcance actual sobre el tenant y designación explícita de privacidad `usuario_id:condominio_id` en `AXS_ARCO_OPERATORS` (lista separada por comas). Ser superadmin o administrador MSP no sustituye esa designación. Revocar cualquiera de estas condiciones bloquea nuevas consultas. Respuestas con `private, no-store`; consultas paginadas hasta 100 filas.

`AXS_ARCO_CASES_ENABLED` está apagado por defecto. Mantenerlo apagado en producción. La migración `20261022_arco_cases.sql` crea tabla, permisos y RLS obligatorio; antes de activarla se debe probar en PostgreSQL aislado con rol sin bypass. Este cambio no ejecuta la migración.

## Rutas y estados

- `POST /arco/{condominio_id}`: recepción idempotente por UUID y contenido idéntico; cambios con igual UUID devuelven 409.
- `GET /arco/{condominio_id}?offset=0&limit=50`: consulta privada; no es un canal público de solicitud.
- `POST /arco/{condominio_id}/{case_id}/estado`: requiere versión vigente, referencia de evidencia y siguiente estado permitido.

Secuencia: recibida → verificada → resuelta → ejecutando → cerrada. La verificación es una declaración del operador con referencia al soporte privado; no hay verificación automática de identidad. Al resolver se exige resultado y constancia de comunicación; decisiones procedentes/parciales exigen vencimiento de ejecución. No permite cerrar con pendientes o sin constancia de respuesta. Un expediente cerrado no se reabre en esta primera versión.

Recepción y vencimientos deben incluir zona horaria; se guardan en UTC. Los vencimientos son introducidos por el operador conforme al calendario legal y suspensiones aplicables; el sistema no calcula días hábiles, feriados ni ampliaciones. La recepción original no cambia. No interpretar estas fechas como validación automática del plazo legal.

Cada cambio se guarda con versión e historial privado. En PostgreSQL la transacción bloquea el tenant y el expediente para serializar operadores; una versión obsoleta devuelve 409. La operación y su evento de outbox se confirman juntos. La bitácora general recibe solo folio, tenant, estado y versión; no recibe referencia al titular ni evidencia de decisión. El folio sigue siendo metadato protegido, no información pública.

## Validación y pendientes

Pruebas locales: ciclo completo sintético, idempotencia, rechazo por roles/tenant/designación, bandera apagada, fechas sin zona, campos extra, versiones antiguas, cierre con pendientes y reversión si falla auditoría. SQLite y autenticación de pruebas; no equivalen a PostgreSQL real o sesión Clerk.

Antes de habilitar para datos reales: validar migración/RLS/concurrencia en PostgreSQL, incorporar pantalla administrativa y probarla con actores designados, acordar custodia de referencias/expedientes externos, verificar identidad por canal seguro, calendario de plazos y notificaciones operativas, ampliar acciones por categoría y verificar conservación del propio expediente. `pending_actions` es una declaración asistida del operador, no una comprobación automática del proveedor. Registrar cero no demuestra por sí mismo eliminación de datos.

No envía correos, no adjunta IDs, no borra datos, no conecta proveedores, no modifica respaldos ni ofrece una bandeja pública. Las capacidades previas del portal permanecen disponibles con esta función deshabilitada.
