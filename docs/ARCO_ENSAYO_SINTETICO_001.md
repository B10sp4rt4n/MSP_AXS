# ARCO-SIM-001: resultado del ensayo local

Fecha local: 22 de octubre de 2026. Resultado: validación parcial, 82 pruebas aprobadas, cero fallidas y cero omitidas. No acredita cumplimiento ARCO integral.

## Entorno y evidencia

Se ejecutaron las cuatro suites existentes de identificación, retención, conservación y borrado de prueba. Usan SQLite en memoria, autenticación de pruebas, imágenes JPEG generadas y un almacén simulado. Las pruebas invocan las rutas de la aplicación y transacciones de base de datos. No hubo solicitudes al almacenamiento real, sesiones Clerk reales, correos enviados ni modificaciones de producción. Se instaló el entorno Python aislado con requirements.txt.

Comando: `python -m pytest -o addopts='' tests/test_identificacion_conservacion.py tests/test_identificaciones.py tests/test_identificacion_retencion.py tests/test_identificacion_borrado_prueba.py -q`.

La [evidencia estructurada](evidence/arco-sim-001-local-20261022.json) conserva los nombres de las pruebas, resultados, momento de ejecución y hashes de sus fuentes. No contiene datos personales reales ni credenciales. El folio ARCO-SIM-001 identifica este ensayo documental; no fue emitido por un gestor de solicitudes del portal.

## Resultado por control

| Control | Resultado y límite |
| --- | --- |
| Lectura y alcance | Aprobado en rutas con actores sintéticos: usuarios ajenos al tenant y roles no autorizados rechazados; revocación durante descarga impide entrega. No equivale a probar RLS de PostgreSQL ni sesión Clerk real. |
| Vencimiento | Aprobado: bloqueo en instante exacto, retiro de fotos/nombre del listado y revalidación tras descarga. Apagar trabajador no restablece acceso. |
| Excepciones | Aprobado: motivo, responsable, incidencia y caducidad requeridos; vencimiento/liberación y permisos comprobados. |
| Cancelación de fotos del piloto | Aprobado dentro del almacén simulado: retiro de objetos y referencias, conservación separada de visita y evento final único. No valida borrado real en proveedor o respaldos. |
| Fallos y reintentos | Aprobado: falla parcial mantiene pendiente y bloqueado; reintento conserva operación; respuesta incierta no se interpreta como ausencia. |
| Guardas de entorno | Aprobado: piloto deshabilitado, producción o contenido ajeno al fixture no autorizan borrado. Las restricciones continúan intactas. |
| Acceso ARCO completo | NO IMPLEMENTADO/NO EJECUTADO: no se generó inventario integral ni entrega segura al titular; el visor de fotos no sustituye una respuesta ARCO. |
| Identidad y expediente | NO IMPLEMENTADO/NO EJECUTADO en sistema: sin recepción real, folio automático, verificación documental, calendario ni cierre de solicitud. Atención asistida sigue siendo el procedimiento descrito. |
| Rectificación/oposición | NO EJECUTADO como flujo ARCO integral. No se infiere de controles de retención o cambios de perfil. |
| Respaldos y restauración | NO EJECUTADO: no hubo PostgreSQL local ni herramientas de respaldo disponibles. Una prueba genérica de restauración no demostraría reaplicación de cancelaciones ARCO. |

## Cierre y siguiente paso

El protocolo integral de la matriz sigue pendiente: este ensayo ejecutó controles reutilizables de fotografías, no la solicitud completa desde recepción hasta respuesta. No hay aprobación para activar purga general ni plazos propuestos sobre documentos reales.

Siguiente hito: construir o habilitar un expediente privado asistido con inventario por tenant y lista de acciones/pendientes por categoría. Después repetir una solicitud ficticia completa, incluida entrega segura simulada y restauración aislada que no reexponga datos cancelados. Antes de datos reales, cada responsable acepta finalidades, plazos y excepciones.
