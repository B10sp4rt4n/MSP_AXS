# Matriz de conservación y atención ARCO de AXS

Versión 1.0. Fecha: 22 de octubre de 2026. Estado: propuesta operativa para revisión por cada responsable; no activa borrados ni modifica datos reales. Aplica como base común a Residencial y Corporativo. Corporativo conserva sus condiciones de aceptación previas al piloto.

## Responsabilidad y decisiones

El condominio o empresa que determine finalidades y medios identifica al responsable y a su persona de privacidad en el aviso y contrato. SynAppsSys actúa según el tratamiento y contrato: no se presume responsable de todos los registros ni se trasladan automáticamente decisiones entre clientes. Para Alexa rige además su aviso específico. El superadmin configura capacidades; esa facultad técnica no sustituye la decisión documentada del responsable.

La ley no establece un plazo universal para todas las visitas. Los valores propuestos siguientes son decisiones de diseño pendientes de aceptación y justificación por finalidad. El único plazo previamente autorizado es el predeterminado de fotografías de identificación para pilotos, con las condiciones de su especificación. Ninguna fila autoriza conservación indefinida mientras se decide.

## Matriz de conservación

| Categoría y finalidad | Inicio y plazo propuesto | Responsable de aprobar / ejecución | Cierre y excepciones | Estado comprobado o pendiente |
| --- | --- | --- | --- | --- |
| Frente/reverso de identificación, nombre transcrito y miniaturas; verificar visita | Pilotos: 30 periodos de 24 horas desde salida consistente; cancelada, vencida o sin salida: desde captura del par. Fechas inconsistentes: revisión manual. | Responsable del cliente acepta política; operador AXS autorizado ejecuta dentro del tenant. | Bloqueo de lectura y supresión verificada de todas las variantes; incidencia con motivo, responsable y caducidad. No extender por descarga ni por baja del cliente. | Predeterminado de piloto autorizado; purga general de fotos reales desactivada. Ver especificación vinculada. |
| Fotografía opcional de salida; evidencia del cierre | Propuesta: 30 días desde captura. No hereda automáticamente la política de identificación. | Responsable del cliente; operador autorizado. | Supresión de foto y derivados; conservar por separado el hecho de salida si corresponde. Excepción documentada con vencimiento. | Plazo y mecanismo general pendientes de validación; no declarar purga activa. |
| Preregistro, motivo y contacto de visitante; coordinar llegada | Propuesta: 30 días desde cancelación o expiración sin ingreso. Si ingresó, aplicar la fila de visita cerrada, sin duplicar datos. | Responsable del cliente; operador autorizado. | Revocar QR y permisos al expirar; depurar datos innecesarios al finalizar plazo. Una visita abierta se concilia, no se cierra inventando una salida. | Validar separación entre vigencia QR y conservación de datos. |
| Visita y movimientos; quién autorizó, entrada y salida | Propuesta: 90 días desde salida confirmada. Revisar visitas abiertas a los 30 días desde entrada; resolver su estado sin reiniciar relojes. | Responsable del cliente; administración de sede/condominio y operador autorizado. | Disociar o suprimir datos personales cuando proceda; conservar solo hechos mínimos necesarios. Incidencias requieren fundamento y término propios. | Plazo no aprobado; cancelación/disociación general pendiente. |
| Perfil residente/anfitrión, teléfono y referencias sociales; directorio y contacto | Mientras exista relación vigente y necesidad. Propuesta: depurar referencias opcionales al revocarse y revisar el resto dentro de 30 días de la baja. | Responsable del tratamiento de cada dato; operador autorizado. | Deshabilitar permisos al terminar relación; revisar obligaciones que justifiquen bloqueo. Separar cuenta de historial de visitas. | Verificar ejecución en AXS y proveedor de identidad; baja no acredita supresión. |
| Vínculo Alexa, preferencias e identificadores; función opcional | Mientras esté activo. Propuesta: revocar credenciales/permisos al desvincular y revisar datos restantes dentro de 30 días. | Responsable indicado en aviso Alexa; operador de integración. | Conservar constancia mínima de consentimiento/revocación solo por periodo justificado. Amazon administra sus propias copias. | Verificar ciclo de desvinculación y tratamiento en proveedores; consulta de 24 horas no es retención. |
| Auditoría técnica y eventos; responsabilidad y seguridad | Propuesta: 180 días desde evento para registros operativos minimizados. Datos personales de soporte requieren plazo específico. | Responsable correspondiente y seguridad de SynAppsSys según contrato. | Rectificación por evento adicional; retirar identificadores cuando proceda sin duplicarlos en la corrección. Hash reidentificable sigue siendo dato personal. | Inventario y purga por campos pendientes; ledger no exceptúa ARCO. |
| Expediente ARCO; acreditar solicitud y resolución | Propuesta: revisión anual desde cierre; antes de operar, fijar término concreto según responsabilidades aplicables. No adoptar retención perpetua ni un plazo legal inventado. | Persona de privacidad del responsable; acceso restringido. | Conservar resultado de verificación, no copia de ID por defecto. Suprimir anexos innecesarios y documentar conservación excepcional. | Procedimiento asistido documentado; gestor de expedientes no implementado. |
| Respaldos, versiones y réplicas; recuperación | Propuesta: ciclo máximo de 30 días para copias ordinarias, sujeto a verificación de cada proveedor. | Responsable acepta; infraestructura AXS verifica y ejecuta. | Registrar cancelaciones y reaplicarlas antes de reabrir una restauración; impedir que reaparezcan datos suprimidos. Excepciones separadas y restringidas. | Inventario, caducidades reales y pruebas por proveedor pendientes. No prometer eliminación instantánea de respaldos. |
| Exportaciones descargadas por cliente; uso autorizado fuera de AXS | Cada exportación identifica custodio, finalidad y vencimiento conforme a categoría original. | Responsable y custodio de copia. | Descargar no reinicia plazo; solicitar confirmación de eliminación cuando corresponda. | AXS no controla directamente dispositivos externos; registrar alcance y pendientes. |

## Atención por derecho

| Derecho | Acción asistida y controles | Evidencia mínima de cumplimiento |
| --- | --- | --- |
| Acceso | Verificar identidad; localizar categorías dentro del tenant; retirar datos de terceros; entregar por canal seguro. | Inventario entregado, alcance, fecha y constancia de entrega; sin publicar contenido. |
| Rectificación | Validar corrección y sustento; actualizar dato vigente; conservar acto mínimo de corrección y notificar a terceros cuando corresponda. | Campos afectados y resultado; evitar reproducir el valor personal antiguo en logs. |
| Cancelación | Resolver procedencia, bloqueo y fundamento de excepciones; ejecutar supresión/disociación en cada almacén y proveedor pertinente; verificar resultados. | Operación, categorías, verificaciones y pendientes; cierre parcial explícito si quedan copias. |
| Oposición | Identificar tratamiento/finalidad; cesar lo procedente sin confundirlo con baja general; documentar restricciones y decisión motivada. | Finalidad afectada, controles aplicados, fecha y respuesta. |

Recepción pública: sruiz@synappssys.com. Registrar fecha original, folio privado, tenant, responsable, identidad verificada, persona asignada, derecho, vencimientos, decisión, ejecución y comunicación. La canalización no reinicia plazos. No enviar datos entre clientes por compartir titular.

Conforme a artículos 2 y 31 de la LFPDPPP, comunicar determinación hasta en 20 días hábiles desde recepción y, si procede, hacerla efectiva dentro de los 15 días hábiles siguientes a la respuesta; una ampliación por periodo igual requiere justificación. Registrar requerimientos y efectos conforme al marco aplicable. No convertir objetivos internos en ampliaciones legales.

## Ensayo con datos ficticios: preparado, no ejecutado

Usar un tenant aislado de desarrollo y una persona sintética con visita cerrada y fotos generadas para prueba. No enviar correo real ni usar fotografías de personas o documentos reales.

1. Crear solicitud sintética de acceso y cancelación con folio `ARCO-SIM-001`; registrar recepción, identidad simulada y responsable ficticio.
2. Inventariar perfil, visita, fotos, derivados, auditoría y copias; comprobar que otro tenant no pueda consultarlos.
3. Preparar entrega de acceso sin terceros. Registrar qué se incluye y por qué; no enviar comunicaciones externas.
4. Emitir decisión simulada: separar fotos y perfil del hecho de movimiento; enumerar cualquier retención y término. No simular que una excepción existe sin motivo.
5. Ejecutar solo mecanismos disponibles sobre fixtures. Si una acción no existe, registrar `NO IMPLEMENTADO`; no marcarla aprobada por haber escrito el procedimiento.
6. Verificar ausencia en proveedor, acceso bloqueado y reintento idempotente donde aplique. Ensayar restauración aislada y reaplicación de supresiones antes de acceso.
7. Cerrar el ensayo con resultados por control, evidencia técnica y fallos. El expediente real permanece privado; al repositorio solo llegan fixtures y resultados sin datos personales.

Aceptación: ningún dato de otro tenant expuesto; entrega verificable; toda supresión confirmada o pendiente explícita; copias/restauración tratadas; ninguna acción sobre producción. Este documento no constituye evidencia de haber ejecutado el ensayo.

## Brechas y orden de implementación

| Prioridad | Trabajo | Criterio de salida |
| --- | --- | --- |
| 1 | Inventario por categoría, proveedor y rol; responsable y plazos aceptados por tenant | Política versionada con finalidad, base, vencimiento y excepciones; ningún tratamiento sin decisión. |
| 2 | Expediente asistido privado y calendario de solicitudes | Folio, permisos, responsable, vencimientos y cierre verificables; sin datos personales en GitHub. |
| 3 | Ejecutar ensayo sintético anterior | Resultados reales por control; fallos y pendientes identificados. |
| 4 | Generalizar bloqueo y supresión con outbox e idempotencia | Evidencia por objeto, categoría y proveedor; acceso revocado y reintentos seguros. |
| 5 | Respaldos y restauración con decisiones ARCO | Caducidades verificadas y restauración que no reexponga datos cancelados. |

Activar por tenant solo tras aceptación de política y pruebas. Las capacidades ARCO básicas no dependen de plan comercial. Esta matriz no activa Corporativo ni reemplaza los avisos de cada responsable.

## Referencias

- [Procedimiento publicado y atención](ARCO_PORTAL_Y_ATENCION.md).
- [Política de fotografías de identificación](identificaciones-conservacion-propuesta.md).
- [Respaldo y cierre](identificaciones-respaldo-y-cierre.md).
- [LFPDPPP vigente, Cámara de Diputados](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf): artículos 2, 10 a 15 y 21 a 34. Las cifras propuestas en esta matriz no son plazos impuestos por esa ley.
