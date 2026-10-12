# Conservación de fotografías de identificación — propuesta operativa

Estado: propuesta preparada el 12 de octubre de 2026. No hay borrado automático activo. El plazo requiere una decisión del responsable del condominio antes de habilitar la purga.

## Plazo propuesto

- Visita con salida registrada: eliminar frente y reverso 30 días después de la salida.
- Visita cancelada, vencida o sin salida registrada: eliminar las fotos a los 30 días de su captura. Esto evita que una visita incompleta conserve documentos indefinidamente.
- Una incidencia que requiera conservar evidencia debe registrar responsable, motivo y fecha límite explícita. No habilitar excepciones sin caducidad.
- La bitácora operativa conserva el identificador de visita, el registro de captura/consulta/eliminación y sus fechas. No incorporar copias, miniaturas, URLs de almacenamiento ni el nombre transcrito de la identificación en el evento de eliminación. La conservación del nombre original del visitante pertenece a la política de visitas y se decide por separado.

## Implementación necesaria antes de activar la política

1. Añadir fecha de vencimiento y estado de eliminación al par de evidencias, con aislamiento por condominio.
2. Crear un reporte en modo simulación: mostrar candidatos y motivo, sin descargar documentos ni borrar objetos.
3. Al vencer, denegar consultas y ejecutar un trabajo idempotente que borre ambos objetos privados y retire sus referencias y el nombre transcrito de la evidencia.
4. Registrar éxito o fallo de cada eliminación. Reintentar fallos y conservar una referencia interna restringida solo mientras sea necesaria para completar el borrado.
5. Verificar por separado los mecanismos de recuperación y retención del proveedor. No afirmar que la purga de objetos elimina automáticamente respaldos o versiones ajenas a este flujo.
6. Probar con imágenes ficticias: antes y después del vencimiento, fallos de proveedor, reintento, excepción con fecha límite y rechazo entre condominios.

## Límites actuales

La captura y lectura ya funcionan en Development. El código de esta rama todavía no implementa el proceso de vencimiento ni la purga. Esta propuesta no establece por sí sola obligaciones legales ni equivale a un aviso de privacidad.
