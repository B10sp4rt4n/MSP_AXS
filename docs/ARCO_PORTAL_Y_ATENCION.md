# Derechos ARCO en el portal AXS

Versión 1.0. Fecha: 22 de octubre de 2026.

## Alcance publicado

El portal dispone de una guía pública en `/privacidad/arco`, enlazada desde el pie de página general, Configuración y el aviso de Alexa en `/privacidad`. Explica acceso, rectificación, cancelación y oposición, canal de contacto, identidad, responsables, plazos y conservación. El contacto de recepción existente es `sruiz@synappssys.com`, a cargo de Salvador Ruiz Esparza.

La guía es común a las modalidades habilitadas. No requiere sesión ni plan de pago. El aviso de Alexa conserva su alcance específico y no se presenta como aviso integral de fotografías o control de visitas. Los datos del responsable de cada condominio o empresa deben corresponder a su aviso y a los contratos aplicables.

El enlace de contacto abre la aplicación de correo del interesado. La página no envía correos, no asigna folios automáticos, no acredita identidad y no ejecuta cambios o borrados. La recepción y atención se realizan de forma asistida por personal autorizado. El contrato corporativo del PR #87 declara las capacidades que deben implementarse para ese piloto; publicar esta guía no acredita que ya existan.

## Procedimiento de atención desde la recepción

1. Registrar la solicitud y su fecha original de recepción en un expediente privado con folio. Identificar el responsable del tratamiento; orientar y canalizar cuando los datos correspondan a un cliente. No publicar expedientes en GitHub, bitácoras públicas ni este documento.
2. Confirmar un medio seguro de respuesta y pedir únicamente la información necesaria para localizar los datos. Verificar identidad o representación por un canal adecuado antes de entregar información o ejecutar acciones. Conservar evidencia mínima de la verificación, evitando copias innecesarias de documentos.
3. Determinar el derecho y finalidad afectados. Distinguir oposición, revocación del consentimiento, baja de cuenta y cancelación. Revisar datos de perfil, visitas, movimientos, fotos, auditoría y proveedores pertinentes dentro del alcance del responsable.
4. Registrar los vencimientos y dar seguimiento a la resolución y ejecución. Para responsables privados en México, el artículo 31 de la LFPDPPP prevé 20 días hábiles para comunicar la determinación y, si procede, 15 días hábiles siguientes para hacerla efectiva; permite una ampliación de cada plazo, por un periodo igual, si se justifica. Registrar cualquier requerimiento y su efecto conforme a las disposiciones aplicables; no reiniciar plazos por reasignaciones internas.
5. El responsable comunica una decisión motivada, incluso si es parcial o existe una excepción. En acceso, revisar datos de terceros antes de entregar por un medio seguro. El ejercicio es gratuito, salvo los costos permitidos por la ley.
6. Un operador autorizado ejecuta lo resuelto y conserva constancia. Si procede cancelación, determinar bloqueo, supresión y cualquier obligación de conservación con fundamento, alcance y término. Notificar a los terceros que corresponda para rectificación o cancelación.
7. Registrar resultados, pendientes, reintentos y comunicación al titular. No declarar una supresión completa si faltan objetos, copias o verificaciones. Mantener el canal disponible ante suspensión de cuenta o terminación del servicio.

## Registro mínimo del expediente

| Campo | Contenido |
| --- | --- |
| Folio y recepción | Referencia y fecha original, con zona horaria. |
| Responsable y alcance | Organización, tenant y categorías involucradas; acceso restringido. |
| Solicitud | Derecho ejercido, finalidad, medio de respuesta y datos mínimos de localización. |
| Identidad | Resultado, método y fecha de verificación; representación cuando aplique. |
| Seguimiento | Persona asignada, vencimientos, requerimientos y ampliaciones motivadas. |
| Decisión | Procedencia total o parcial, fundamento y excepciones. |
| Ejecución | Acciones, proveedor, operador, fecha, resultados y pendientes. |
| Comunicación y cierre | Respuesta al titular, constancia de entrega y conclusión. |

Un cambio de estado del expediente conserva la trazabilidad y no debe duplicar los datos personales que se estén suprimiendo. Las solicitudes del mismo titular en distintos tenants no se fusionan ni divulgan automáticamente entre clientes.

## Conservación y límites de la implementación

La [matriz de conservación y atención ARCO](ARCO_MATRIZ_CONSERVACION_V1.md) distingue plazos autorizados y propuestos, responsables, brechas y ensayo sintético pendiente de ejecución. No activa borrados ni modifica datos reales.

La trazabilidad no justifica almacenar datos personales indefinidamente. Los datos de identidad y las fotografías deben poder tratarse separadamente del hecho auditable. Un hash o una referencia que permita reidentificar a alguien sigue requiriendo protección.

Una retención excepcional requiere fundamento, alcance, responsable y término o revisión. Los datos bloqueados se excluyen de la operación ordinaria. Para suprimir se deben considerar almacenamiento activo, miniaturas, cachés, índices y proveedores; los respaldos requieren caducidad definida y reaplicación de decisiones ARCO antes de restaurar el servicio. Las copias descargadas fuera de AXS requieren identificar a su custodio y el tratamiento correspondiente; la plataforma no controla su borrado directamente.

La política técnica de identificación tiene especificación y pruebas propias: [conservación de fotografías](identificaciones-conservacion-propuesta.md). Su plazo predeterminado de piloto no es un plazo legal universal ni acredita purga general habilitada. Este cambio no activa trabajadores de borrado ni modifica evidencias, permisos o datos de producción.

Quedan por implementar o verificar, según el tratamiento, la gestión de expedientes en el sistema, acciones ARCO sobre datos y proveedores, mecanismos de bloqueo y supresión general, control de respaldos y validación de plazos por categoría. Hasta su validación se utilizará el procedimiento asistido, sin prometer operaciones automáticas.

Antes del piloto corporativo con datos reales se requiere cumplir los criterios ARCO del contrato corporativo. Cada nuevo tratamiento debe identificar responsable, aviso, finalidad, fundamento o consentimiento aplicable, canal y plazos de conservación.

## Verificación de publicación

- La ruta ARCO responde sin cuenta de usuario y sin redirección a inicio de sesión.
- El pie del portal, Configuración y el aviso de Alexa permiten llegar a la guía.
- Los cuatro derechos, el contacto y la distinción entre solicitud y borrado automático son visibles en móvil y escritorio.
- El contacto abre un `mailto:` al correo publicado, sin enviar mensajes automáticamente.
- El aviso de Alexa conserva su alcance y la guía no presenta Corporativo como una modalidad ya habilitada.

## Fuentes y control de cambios

[Ley y reformas en Cámara de Diputados](https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp.htm). [Publicación original del 20 de marzo de 2025](https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp/LFPDPPP_orig_20mar25.pdf), artículos 10, 21 a 34. La reforma del 14 de noviembre de 2025 modifica el artículo 4.

Las futuras revisiones deben mantener sincronizados esta guía, la página pública, los avisos aplicables y el contrato de desarrollo. El expediente privado de solicitudes y el historial público de documentación tienen finalidades y permisos distintos.
