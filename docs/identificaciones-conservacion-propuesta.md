# Conservación de fotografías de identificación — propuesta operativa v2

Estado: especificación preparada el 12 de octubre de 2026. Purga general desactivada. El responsable del condominio debe confirmar el plazo y las excepciones antes de habilitar borrado de documentos reales. Esta especificación permite preparar y probar la implementación con datos ficticios.

## Regla de conservación propuesta

| Situación | Fecha base | Vencimiento |
| --- | --- | --- |
| Salida registrada y consistente con la captura | Fecha de salida | Fecha base + 30 días |
| Cancelada, vencida o sin salida | Fecha de captura del par | Fecha base + 30 días |
| Par incompleto o fechas/estado inconsistentes | Sin cálculo automático | Revisión manual |
| Incidencia con excepción vigente | Vencimiento ordinario conservado | Se difiere la eliminación hasta el fin explícito de la excepción |

“30 días” significa 30 periodos de 24 horas. Guardar instantes en UTC y mostrarlos en America/Mexico_City. La captura del par usa el instante más reciente de los dos lados. La consulta por fecha del simulador incluye el día completo seleccionado; el bloqueo de lectura utiliza el instante exacto de vencimiento.

La regla comprende frente, reverso, nombre transcrito y cualquier copia o miniatura persistida de la identificación. La política del registro de visita y la retención de bitácora se definen por separado; no borrar el registro de visita ni modificar entrada, salida o autorización.

La salida registrada antes del vencimiento puede actualizar la fecha base de forma auditada. Una salida o corrección posterior al vencimiento no debe restaurar el acceso ni extender silenciosamente la conservación. Esos casos requieren revisión explícita.

## Excepciones por incidencias

- Sólo un administrador autorizado del condominio puede registrar o liberar una excepción dentro de su alcance.
- Exigir referencia de incidencia, responsable, motivo y fecha/hora límite; prohibir excepciones sin caducidad.
- Registrar creación, cambio y liberación en bitácora. Una ampliación requiere un acto nuevo con motivo y límite explícitos.
- El plazo máximo de una excepción queda pendiente de decisión del responsable; no inventar un límite en el producto.
- Al concluir la excepción, si ya pasó el vencimiento ordinario, bloquear la lectura y poner el par en cola.
- No admitir excepciones cuando el borrado ya esté en curso o haya terminado. Nunca prometer recuperar una foto eliminada.
- Revalidar la excepción bajo bloqueo de la misma fila de conservación usada por el trabajador, antes de reclamar el borrado. La creación de una excepción y el reclamo deben serializarse.

## Modelo y flujo por par

Implementar un registro durable de conservación por captura, asociado a condominio, visita y dos evidencias, con versión de política, fecha base, vencimiento, estado, excepción, operación de borrado, intentos, próximo intento y fechas de finalización. Las referencias privadas sólo son accesibles al backend autorizado.

1. Captura: persistir el par y su conservación en la misma transacción. La versión de política debe ser explícita.
2. Lectura: validar usuario, alcance, estado, vencimiento y excepción antes de acceder al proveedor, y volver a validar antes de entregar bytes. Devolver 410 para un par vencido sin excepción, en borrado o eliminado; mantener errores de autenticación y alcance.
3. Reclamo: seleccionar lotes paginados por condominio, bloquear el registro, revalidar vencimiento/excepción y guardar intención de borrado junto al evento de outbox. Si no se conserva esa intención, no borrar objetos.
4. Eliminación: ejecutar I/O del proveedor fuera de la transacción larga. Reclamo exclusivo con token y plazo de recuperación; otro trabajador sólo puede retomar un reclamo vencido. Usar la misma operación en todos los reintentos.
5. Confirmación: eliminar cada lado y comprobar que su lectura devuelve ausencia. Un objeto ya ausente cuenta como completado; una respuesta incierta mantiene el par pendiente.
6. Finalización: tras confirmar ambos lados ausentes, quitar referencias, nombre transcrito, hash y metadatos de captura innecesarios. Conservar identificadores mínimos de la operación y evento. Guardar finalización y outbox en una transacción.
7. Recuperación: si falla la confirmación o el evento final, conservar el estado pendiente y las referencias internas necesarias; la lectura sigue bloqueada. Reintentar sin duplicar operaciones ni eventos finales.
8. Bitácora: registrar intención, fallos y finalización, con condominio, visita, operación, cantidad de fotos, motivo y fechas; nunca incluir bytes, miniaturas, nombres transcritos, tokens ni rutas del proveedor.

Trabajador propuesto: cada 15 minutos, lotes de hasta 100 pares. Reintentos a 1, 5, 15 y 60 minutos, después cada 6 horas. Tras cinco fallos consecutivos, generar aviso operativo en el panel y conservar el trabajo pendiente; no declarar éxito ni descartar referencias. Intervalos configurables. El bloqueo de lectura no depende de que el trabajador esté disponible.

El piloto verificó el patrón de intención durable, ausencia en proveedor y finalización idempotente. Su servicio está restringido por allowlist y hash a fotos ficticias y no se debe convertir en trabajador general quitando esas restricciones. La implementación general requiere su propio modelo, reclamo y controles de concurrencia.

## Reporte y panel administrativo

Ampliar el simulador con versión de política, vencimiento exacto, excepción vigente, revisión, pendiente y eliminado. Paginar sin truncar ni perder candidatos. Mostrar cantidades por estado y próximo reintento; mantener no-store y aislamiento por condominio. No descargar fotografías para calcular el reporte.

El simulador actual usa 30 días y fechas consistentes, pero no consulta excepciones; no equivale todavía a la selección definitiva de la cola. Los pares incompletos requieren conciliación controlada, sin conservación indefinida ni eliminación ciega.

En el detalle de visita mostrar fecha de vencimiento y estado. Después del vencimiento o borrado, retirar fotos y nombre transcrito del estado de la pantalla, cancelar descargas pendientes y revocar URLs temporales de memoria. Las copias que una persona haya descargado fuera de la aplicación no quedan bajo control de este proceso.

## Activación por etapas

1. Implementar en Development con la purga general desactivada por defecto y fixtures aislados.
2. Probar vencimiento, excepción, revocación de acceso, concurrencia y recuperación con imágenes ficticias.
3. Ejecutar simulación por condominio y conciliar registros incompletos e incidencias.
4. Registrar aceptación de versión de política, plazo, excepciones y tratamiento de fotos existentes por el responsable del condominio.
5. Habilitar sólo los condominios aceptados, con lote inicial acotado y seguimiento de pendientes. Evitar una bandera global que active todos los condominios.
6. Desactivar el trabajador debe detener nuevos reclamos; no debe volver a habilitar la lectura de documentos vencidos ni olvidar borrados pendientes.

Para fotos anteriores a la activación, usar las fechas originales, sin reiniciar el plazo. El reporte de esos candidatos debe revisarse antes del primer lote. No aplicar una nueva política retrospectivamente sin esa aceptación registrada.

## Criterios de aceptación

- Antes del vencimiento el administrador/guardia autorizado puede leer; al llegar al instante exacto, recibe 410 sin entregar bytes.
- Una excepción vigente conserva acceso dentro del alcance; al caducar se bloquea y entra a la cola.
- Rechazar usuarios sin sesión y de otro condominio, tanto en consulta como en excepciones y operación.
- Dos trabajadores concurrentes producen una sola operación y un solo evento final.
- Probar fallo antes de intención, fallo en cada lado, ausencia previa, caída tras borrar un lado, caída tras ambos lados y fallo de outbox.
- Reintentar completa los dos lados sin duplicar el evento; nunca informa finalización con un objeto aún disponible.
- Quitar nombre transcrito y referencias después de completar; conservar el estado de visita y la evidencia mínima de auditoría.
- Verificar PostgreSQL real y RLS, no sólo dobles de prueba.
- Confirmar ausencia en almacenamiento activo y describir por separado recuperación, versiones y respaldos del proveedor.

## Evidencia y límites actuales

Captura, visor y simulador funcionan en Development. El piloto autorizado eliminó cuatro fotos ficticias de dos visitas canceladas: objetos ausentes, lectura 410, dos eventos de finalización entregados y repetición idempotente. Después se desactivó el endpoint de prueba y se verificó su rechazo 404. Evidencia: [identificaciones-borrado-prueba-20261012.json](evidence/identificaciones-borrado-prueba-20261012.json).

Se implementó y probó un piloto en Development con excepciones, bloqueo por plazo y trabajador durable restringidos a imágenes ficticias. La purga general de documentos reales continúa desactivada; la activación por condominio y la migración de fotos existentes siguen pendientes. Detalle: [piloto Development](identificaciones-conservacion-development.md). El piloto no prueba la eliminación de respaldos o versiones del proveedor. Esta propuesta operativa no establece por sí sola obligaciones legales ni equivale a un aviso de privacidad.
