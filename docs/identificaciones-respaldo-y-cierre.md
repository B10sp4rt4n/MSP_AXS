# Respaldo previo al vencimiento y soporte de cierre

Decisión funcional autorizada por Salvador el 12 de octubre de 2026.
Estado: especificación para implementación; no hay exportador, avisos ni descarga temporal habilitados por este documento.

## Acuerdo

Ofrecer exportación opcional antes del borrado periódico de identificaciones y un paquete de soporte al cerrar el condominio. Mantener 30 días como plazo predeterminado para pilotos. Descargar no prorroga la conservación, no crea una excepción ni detiene la eliminación. No generar copias permanentes automáticamente.

Conservar constancia mínima de solicitud, preparación, entrega por el servidor y eliminación. El servidor no puede certificar que el destinatario guardó o abrió el archivo. El plazo de esta constancia y de los registros operativos es independiente del de las fotos y sigue pendiente de definición; no establecer conservación indefinida por omisión.

## Borrado periódico

1. Mostrar al administrador un aviso dentro de AXS y una lista paginada de pares próximos a vencer. Como parámetro inicial de implementación, proponer siete días de anticipación, configurable; no es un plazo ya aprobado. No enviar correos ni mensajes externos automáticamente en esta etapa.
2. Permitir seleccionar pares y solicitar una exportación. Mostrar fecha exacta de vencimiento, cantidad de pares y aviso de custodia de la copia descargada. Sin nombres ni miniaturas en el aviso general.
3. Requerir sesión, permiso administrativo vigente y alcance sobre el condominio. La visibilidad individual del guardia no concede permiso de exportación masiva. MSP_ADMIN tampoco autoriza acceso fuera de su alcance vigente.
4. Volver a validar alcance, estado y vencimiento al preparar y al entregar. Un trabajo en cola o un archivo preparado no otorga derechos adquiridos de acceso.
5. Entregar ZIP con frente y reverso en JPEG normalizado y manifiesto JSON. Usar identificadores internos como nombres de archivo; omitir nombres personales, rutas del proveedor, credenciales y metadatos EXIF. El nombre transcrito no forma parte del respaldo fotográfico inicial.
6. Continuar el vencimiento ordinario si no se solicita o completa la descarga. La exportación nunca cambia `expires_at` ni `hold_until`.

El manifiesto identifica versión, condominio, solicitud, fecha UTC, pares incluidos, fecha de vencimiento de cada par y hash SHA-256 de cada archivo. Una selección incompleta o inconsistente se rechaza antes de preparar el paquete, con un resultado de revisión que no exponga datos de otro condominio.

## Descarga temporal y concurrencia

- Enlace de AXS autenticado, ligado al solicitante y al condominio; nunca una URL pública de Blob ni un token suficiente por sí solo. Revalidar permisos en cada intento.
- Propuesta inicial de vigencia del enlace: 15 minutos, limitada siempre por el vencimiento más próximo de los pares seleccionados. Este valor es configuración propuesta, no una función existente.
- Rechazar la entrega si cualquier par venció, entró en borrado o perdió elegibilidad. Solicitar una nueva selección; no entregar un ZIP parcial silenciosamente.
- Los paquetes temporales son copias de las identificaciones: deben inventariarse, tener limpieza por caducidad y quedar sujetos al mismo límite de acceso. El borrado de originales debe abarcar estas copias o confirmar su ausencia antes de declarar completada la eliminación de todas las copias activas administradas por AXS.
- Preparar fuera de transacciones largas y verificar nuevamente antes de responder. No mantener bloqueos de base de datos durante I/O remoto. Aplicar límites explícitos de tamaño, lotes y cuota; no permitir exportaciones sin límite.
- Usar `Cache-Control: private, no-store` y `Content-Disposition: attachment`. No guardar ZIP en ubicaciones públicas ni registrar contenido o enlaces de descarga en logs.
- Un error al exportar no suspende el borrado. Si hay una incidencia real, utilizar el mecanismo separado de excepción con motivo, responsable y caducidad.

## Baja del condominio

Antes de retirar los permisos del responsable receptor, ofrecer un paquete de cierre con registros de visitas, incidencias y bitácora que le correspondan, más un manifiesto de entrega. El alcance y la conservación de estos registros requieren política propia; no aplicarles automáticamente el plazo de 30 días de fotografías.

Las identificaciones se excluyen por defecto y sólo se incorporan mediante selección explícita de pares todavía accesibles. No restaurar fotos vencidas o eliminadas ni extender su plazo por el cierre. Registrar por separado las ausencias y pendientes de eliminación, sin presentar un cierre parcial como eliminación completa.

La baja del proveedor implementada en `provider_offboarding.py` revoca una relación de servicio; no equivale a baja del condominio ni autoriza extracción de sus datos. Una solicitud previa no permite descargar después de perder el alcance. Si el receptor pierde permisos, la entrega debe reautorizarse mediante un actor vigente del condominio; nunca reactivar al proveedor sólo para descargar.

El cierre registra qué se ofreció, qué se preparó, qué entregó el servidor, qué falló y qué quedó pendiente. La descarga es opcional y no bloquea indefinidamente el cierre. No afirmar destrucción de respaldos o versiones del proveedor de almacenamiento sin evidencia independiente.

## Constancia mínima

Guardar identificador de operación, condominio, actor, versión de política, instantes, identificadores de pares, cantidades, estado y referencia al evento de auditoría. Para eliminación, enlazar el evento existente y distinguir pendiente, error y completada. No duplicar fotografías, nombres transcritos ni rutas privadas en la constancia.

Separar eventos de solicitud, preparación y entrega; no llamar «descargado por el usuario» a un ZIP que sólo se generó. Los reintentos deben ser idempotentes por solicitud y conservar intentos de entrega sin duplicar la constancia final de borrado.

## Integración pendiente

- Reutilizar el cálculo y las excepciones de `identificacion_conservacion.py`; el simulador `identificacion_retencion.py` es una proyección, no una autorización de descarga.
- Crear trabajos de exportación con estado durable, vencimiento, manifiesto y limpieza de copias temporales, aislados por condominio y protegidos por RLS.
- Incorporar autorización administrativa antes y después del I/O, siguiendo las revalidaciones de `identificaciones_router.py`.
- Usar el outbox existente para los eventos. La constancia actual de eliminación es el punto de partida; no modificar ni sustituir eventos históricos.
- Añadir panel de aviso, selección, preparación, descarga y errores; luego integrar el paquete de cierre con los permisos vigentes.
- Mantener las restricciones del piloto y la purga general desactivada hasta probar el flujo y completar la aceptación por condominio.

## Pruebas necesarias antes de activar

1. Administrador autorizado puede exportar un par sintético vigente; guardia, residente, usuario sin sesión y administrador de otro condominio no pueden.
2. Revocación de alcance o vencimiento durante preparación/entrega impide recibir el ZIP, aunque el enlace no haya caducado.
3. Solicitar, reintentar o descargar no modifica vencimiento, excepción, visita ni autorización de acceso.
4. Pares incompletos, referencias cambiadas y borrado concurrente no producen un paquete parcial presentado como completo.
5. La caducidad limpia el archivo temporal; un fallo de limpieza queda visible y reintentable. No declarar todas las copias eliminadas mientras exista una copia temporal pendiente.
6. Reintentos no duplican solicitudes ni eventos finales. La bitácora distingue preparación de entrega.
7. Cierre sin fotografías, cierre con selección explícita y baja de proveedor respetan sus distintos alcances; el antiguo proveedor no descarga después de su baja.
8. Validar límites de memoria/tamaño, contenido del manifiesto, ausencia de secretos y aislamiento PostgreSQL/RLS con dos condominios sintéticos.
