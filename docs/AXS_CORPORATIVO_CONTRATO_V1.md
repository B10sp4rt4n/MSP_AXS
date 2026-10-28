# Contrato de desarrollo de AXS Corporativo

**Versión 1.1 · 22 de octubre de 2026**

AXS Corporativo se declara como una línea de negocio de AXS para gestionar visitas y accesos en empresas. Tendrá modelo operativo, experiencia de usuario y configuración comercial propios, apoyados en un motor común con AXS Residencial.

Este contrato fija las reglas para su diseño e implementación. Su declaración establece la dirección del desarrollo; la habilitación operativa depende de cumplir los criterios de aceptación de este documento.

# Propósito y alcance inicial

La primera entrega permitirá identificar quién llega, quién lo recibe, qué destino tiene autorizado y cuándo entra y sale. El piloto abarcará una empresa y una sede, con un modelo preparado para varias sedes.

Incluye directorio de anfitriones, destinos, invitaciones con QR, atención de visitantes sin preregistro, autorización, identificación y evidencias configurables, registro de entrada y salida y consulta de visitas abiertas.

El registro en AXS representa un movimiento confirmado por un operador autorizado. La apertura automática de puertas requiere una integración específica y queda fuera de esta entrega.

# Separación de las líneas de negocio

| Componente | Contrato |
| --- | --- |
| Motor común AXS | Comparte servicios de identidad, permisos, QR, movimientos, evidencias y auditoría. |
| AXS Residencial | Conserva sus conceptos de condominio, vivienda, residente y caseta. |
| AXS Corporativo | Utiliza empresa, sede, área o destino, anfitrión y recepción o seguridad. |
| Experiencia | Cada modalidad tiene vocabulario, menús y recorridos propios. |
| Oferta comercial | Cada línea puede tener planes, capacidades, límites y condiciones de servicio propios. |
| Repositorio | Se mantiene inicialmente una base de código compartida con módulos separados. |

Corporativo no exigirá crear viviendas ficticias ni registrar empleados como residentes. La reutilización se hará mediante servicios comunes y relaciones explícitas de cada dominio.

# Modelo de organización y aislamiento

El tenant es la cuenta cliente y constituye la frontera de aislamiento. En el alcance inicial corporativo, cada tenant representa una empresa cliente. La empresa administra una o varias sedes; cada sede contiene destinos y puntos de recepción o acceso.

Los anfitriones se vinculan a la empresa y a las sedes donde pueden recibir visitas. El destino y el anfitrión son relaciones distintas: conocer a quién visita una persona no determina por sí mismo a qué área puede acceder.

Una sede puede ocupar parte de un inmueble compartido. Compartir dirección, recepción o edificio no concede acceso a información de otra empresa. Una recepción que atienda a varias empresas requerirá asignaciones explícitas por tenant y sede; esa operación queda fuera del primer piloto.

Una persona puede participar en varias organizaciones mediante membresías independientes. Sus permisos se evalúan en el tenant activo y nunca se heredan por compartir correo, sede física o identidad.

La implementación deberá validar el alcance en servidor en consultas, cambios, búsquedas, QR, exportaciones y acceso a fotografías. Un identificador o filtro enviado por la interfaz no acredita autorización.

# Habilitación y roles

Superadmin habilita la modalidad corporativa, el plan y las capacidades contratadas de cada tenant. El owner o administrador del cliente configura su operación dentro de esas capacidades.

| Rol | Facultades iniciales |
| --- | --- |
| Superadmin | Habilitar modalidad y capacidades; realizar soporte privilegiado mediante acceso explícito y auditable. |
| Owner o administrador corporativo | Administrar sedes, destinos, membresías, asignaciones y políticas permitidas del tenant. |
| Anfitrión | Invitar y autorizar visitas dentro de sus sedes y consultar las que le corresponden. |
| Recepción o seguridad | Identificar, validar autorización y registrar movimientos en las sedes asignadas. |

Los permisos se asignan por función y alcance. El rol de recepción no permite aprobar visitas por defecto. Cualquier facultad adicional de aprobación deberá configurarse expresamente y dejar evidencia del autorizador.

Una modalidad o capacidad deshabilitada deberá bloquear también las operaciones en servidor.

# Invitaciones y autorización

La invitación identifica al tenant, la sede, el anfitrión, el destino, el motivo y la ventana de acceso. El QR acredita un preregistro y se valida contra su estado vigente en servidor; poseerlo no concede acceso ilimitado.

La validación comprende coincidencia de tenant, sede y destino, vigencia, cancelación, autorización y reglas de uso. Se rechaza un QR perteneciente a otro contexto.

Una visita sin preregistro podrá identificarse y ponerse en espera. El ingreso requerirá la decisión de un anfitrión o autorizador con facultades vigentes. Debe quedar registrado quién autorizó, para qué destino y bajo qué condiciones.

La primera entrega contempla una entrada y una salida por autorización. Una nueva visita o reingreso requerirá otra autorización, salvo que posteriormente se implemente una política explícita de acceso recurrente.

# Ciclo de visita y movimientos

La autorización y la presencia se registran por separado. Una invitación vigente no significa que el visitante esté dentro.

1. Se crea el preregistro o se recibe una solicitud en recepción.
2. Se identifica al visitante y se valida u obtiene la autorización.
3. El operador confirma la entrada y se abre la estancia.
4. El operador confirma la salida y se cierra la estancia.

Solo se permite una estancia abierta por visita autorizada. Reintentos, doble clic o solicitudes concurrentes no deben duplicar movimientos. Una salida exige una estancia abierta y referencia la entrada que cierra.

La expiración de una autorización no genera una salida automática. Si la persona tiene una entrada abierta, seguirá apareciendo como visita sin salida registrada hasta su cierre confirmado.

El tablero distinguirá visitas pendientes, autorizadas, dentro según el registro y cerradas. No presentará la lista de registros abiertos como un censo físico garantizado.

# Evidencia y trazabilidad

Las políticas de identificación, fotografía y evidencia de salida serán configurables por cliente y sede dentro de las capacidades habilitadas. La interfaz indicará cuándo una evidencia es opcional o requerida.

Cada movimiento conservará tenant, sede, visita, autorización, operador, tipo de movimiento y fecha y hora. Se registrará el momento del evento y el de su registro cuando sean distintos. Las fechas se almacenarán en UTC y se mostrarán en la zona horaria configurada para la sede, sin ajustes manuales por suma o resta de horas.

Las correcciones conservarán la secuencia del hecho, motivo, autor y fecha, aplicando las reglas de rectificación y conservación de datos personales de la sección ARCO. Las fotografías tendrán acceso restringido y una política de conservación definida antes del piloto. La auditoría registrará autorizaciones, rechazos, cancelaciones, movimientos, correcciones y cambios relevantes de permisos o políticas; no duplicará identificaciones ni fotografías en registros inmutables.

# Derechos ARCO y privacidad desde el diseño

## Carácter obligatorio y responsables

Acceso, rectificación, cancelación y oposición son requisitos del producto desde su diseño y antes del primer piloto con datos reales. Se aplicarán a visitantes, anfitriones y operadores, a identificaciones, fotografías, movimientos y cualquier otro dato personal tratado por AXS. Su atención básica no dependerá de un plan de pago, de una capacidad comercial ni de tener una cuenta de usuario.

El modelo previsto es que la empresa cliente decida las finalidades y actúe como responsable del tratamiento de sus accesos, y que SynAppsSys trate esos datos como encargado bajo instrucciones documentadas. Los roles se confirmarán por tratamiento y se reflejarán en el contrato de servicio y el aviso; SynAppsSys identificará separadamente las finalidades propias en las que le corresponda actuar como responsable.

Cada tenant designará un contacto de privacidad y publicará un canal ARCO accesible. El responsable decide la procedencia y emite la respuesta; un operador con facultades específicas ejecuta las acciones. Ser owner o superadmin no concede por sí solo acceso irrestricto al expediente ni autoriza resolver solicitudes de otro responsable.

## Atención de los cuatro derechos

| Derecho | Capacidad mínima exigida |
| --- | --- |
| Acceso | Localizar los datos del titular en el alcance correspondiente y preparar una entrega comprensible, segura y revisada para proteger datos de terceros. |
| Rectificación | Corregir datos acreditados y evitar que el valor incorrecto siga circulando en consultas, búsquedas o exportaciones. Conservar solo la trazabilidad necesaria de la corrección. |
| Cancelación | Resolver su procedencia; bloquear y después suprimir conforme a la obligación aplicable, o documentar el fundamento concreto de una excepción. |
| Oposición | Registrar y aplicar el cese del tratamiento que resulte procedente para la finalidad solicitada, sin interpretarlo automáticamente como borrado de todo el historial. |

El sistema distinguirá oposición, revocación del consentimiento y baja de una cuenta. Registrará el alcance y resolución de cada una; no ejecutará una como sustituto de otra.

La primera entrega puede apoyarse en un canal y un procedimiento asistidos por personal. Debe permitir recibir, registrar, atender y acreditar las solicitudes sin exigir un portal de autoservicio completo.

El expediente tendrá folio, responsable, fecha de recepción, derecho y alcance solicitados, medio de respuesta, verificación de identidad o representación, vencimientos aplicables, decisión, acciones realizadas y constancia de comunicación. Las ampliaciones o excepciones se motivarán; no se reiniciará el cómputo por cambios internos de estado. Se validarán los plazos y reglas aplicables antes del piloto.

La verificación de identidad será proporcional y protegerá sus evidencias. No se exigirá crear una cuenta de AXS ni entregar nuevamente una fotografía de identificación cuando exista un medio suficiente menos intrusivo.

## Conservación y auditoría compatibles con ARCO

La arquitectura separará el hecho auditable de las cargas de datos personales. Los registros inmutables evitarán nombres, documentos, fotos o enlaces públicos que impidan atender una rectificación o supresión. Las referencias y hashes que permitan vincular o reidentificar a una persona seguirán bajo controles de datos personales.

Cada categoría tendrá una finalidad, justificación, plazo, evento que inicia el cómputo y acción al vencer: perfiles, visitas, fotografías, identificaciones, expedientes ARCO, auditoría y respaldos. No se fijará un plazo universal ni se justificará conservar indefinidamente con la palabra auditoría.

Una retención excepcional precisará fundamento, alcance, responsable y fecha de revisión o término. Los datos bloqueados quedarán fuera de la operación ordinaria. Las fotografías y copias de identificaciones se eliminarán cuando corresponda sin conservar duplicados en logs, miniaturas o exportaciones gestionadas por la plataforma.

El proceso abarcará base de datos, archivos, miniaturas, índices, cachés y proveedores que sigan tratando la información. Mantendrá tareas, reintentos y evidencia de cumplimiento sin registrar nuevamente el dato suprimido. Se notificará a los terceros que corresponda cuando deban aplicar la rectificación o cancelación.

Los respaldos tendrán acceso restringido y caducidad definida. Cuando no sea viable borrar selectivamente de inmediato, se documentará la restricción y su ciclo de expiración; toda restauración reaplicará las decisiones ARCO antes de poner los datos a disposición operativa.

## Recopilación y avisos

Antes de recabar datos se mostrará el aviso correspondiente al responsable y su versión. Cada campo y evidencia deberá tener una finalidad justificada. El consentimiento se recabará cuando sea exigible y se distinguirá de los tratamientos amparados en una excepción aplicable.

La captura de ambos lados de una identificación no será el valor predeterminado corporativo. Requerirá justificar su necesidad y configurar alternativas menos intrusivas cuando sean suficientes.

Los datos de acceso no se reutilizarán para marketing, perfiles comerciales o nuevas finalidades sin establecer previamente las condiciones legales aplicables. La exclusión de biometría de la primera entrega permanece vigente.

## Base normativa y validación

Referencia para México y clientes privados: Ley Federal de Protección de Datos Personales en Posesión de los Particulares, artículos 10, 12, 14 a 16 y 21 a 34. La cancelación puede implicar bloqueo previo a la supresión y excepciones de conservación; una excepción requiere una decisión motivada para el caso.

Fuentes oficiales: [texto original publicado el 20 de marzo de 2025](https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp/LFPDPPP_orig_20mar25.pdf), [índice de reformas](https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp.htm) y [reforma del artículo 4 publicada el 14 de noviembre de 2025](https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp/LFPDPPP_ref01_14nov25.pdf).

Este contrato declara requisitos técnicos y operativos; su implementación deberá validarse contra el aviso y las obligaciones de cada tratamiento antes del piloto. La expansión a entidades públicas u otras jurisdicciones requerirá revisar el régimen correspondiente.

# Oferta comercial y capacidades

AXS Corporativo tendrá un catálogo comercial diferenciado del residencial. La modalidad, el plan y las capacidades se configurarán por tenant desde superadmin; el cliente administrará únicamente las opciones habilitadas.

La unidad de cobro, precios, límites incluidos y condiciones de soporte quedan pendientes de definición. La arquitectura permitirá configurarlos sin codificar precios en el flujo de acceso. El primer piloto utilizará habilitación administrada; no incluye un sistema de cobro automático.

# Desarrollo y compatibilidad

El desarrollo se preparará en una rama Git dedicada dentro de MSP_AXS. La rama sirve para revisar e integrar cambios; la separación permanente entre negocios reside en módulos, contratos y modelo de datos. El nombre de rama propuesto es `feat/axs-corporativo-v1`.

Antes de implementar se revisarán las dependencias actuales de vivienda, residente y condominio. Esa revisión determinará los cambios concretos y las migraciones necesarias.

Los clientes residenciales existentes conservarán su modalidad y comportamiento. Corporativo permanecerá deshabilitado hasta su habilitación explícita. Los cambios de datos serán incrementales y conservarán relaciones e historial existentes conforme a los plazos y derechos aplicables. Deshabilitar Corporativo no borrará automáticamente sus registros ni suspenderá la atención de derechos ARCO; la recuperación preservará movimientos y auditoría sin reactivar datos cancelados o suprimidos.

La primera revisión de código incluirá este contrato en la documentación del repositorio y trazará cada criterio de aceptación a su validación.

# Etapas y criterios de aceptación

| Etapa | Resultado exigido |
| --- | --- |
| Revisión de base | Mapa de dependencias residenciales, servicios reutilizables y cambios necesarios. |
| Separación estructural | Modalidad por tenant, módulos separados, modelo de sedes y permisos definidos. |
| Recorrido corporativo | Invitación, autorización, identificación, entrada, salida y tablero funcionando en un entorno de prueba. |
| Piloto | Empresa, sede, operadores y políticas definidos; validación completa y evidencia de resultados. |

La habilitación del piloto requiere comprobar:

- Un cliente corporativo opera sin vivienda ni residente ficticios.
- Un tenant no consulta ni modifica datos, QR o evidencias de otro.
- Los roles respetan sus sedes y facultades; owner no habilita capacidades comerciales reservadas a superadmin.
- Una invitación válida permite el recorrido completo y un QR de otra sede, vencido o cancelado se rechaza.
- Una visita inesperada espera una autorización válida antes de ingresar.
- Reintentos y concurrencia no duplican entradas ni salidas.
- Una visita expirada que sigue abierta permanece visible y puede cerrarse conforme a permisos.
- Las evidencias respetan la configuración y el acceso autorizado.
- Las horas se muestran correctamente y las correcciones conservan trazabilidad.
- Se ejecutan casos ARCO de acceso, rectificación, cancelación y oposición con identidad validada, aislamiento entre tenants, decisión motivada y constancia del resultado.
- Los datos bloqueados no aparecen en búsquedas, reportes, exportaciones ni enlaces de fotos de operación ordinaria; solo quedan accesibles para la finalidad restringida que justifica su conservación.
- Una restauración de respaldo vuelve a aplicar cancelaciones, oposiciones y supresiones antes de habilitar el servicio; los reintentos de borrado no pierden el seguimiento.
- El canal ARCO sigue disponible sin cuenta de usuario y cuando el plan o tenant se suspenden o terminan.
- Los recorridos residenciales de QR, atención sin preregistro, evidencias, entrada, salida y recuperación de visitas abiertas conservan su funcionamiento.

# Límites y decisiones pendientes

La primera entrega excluye control de asistencia o nómina, biometría, torniquetes, apertura remota de puertas, proveedores con permisos recurrentes, recepción compartida entre empresas, nuevas integraciones de mensajería y cobro automático. Alexa y otras integraciones podrán evolucionar por separado.

Los derechos ARCO y sus mecanismos mínimos son parte obligatoria de la primera entrega, incluso en el piloto, y quedan fuera de las exclusiones anteriores. Antes del piloto deben definirse la empresa y sede, los responsables operativos y de privacidad, el canal ARCO, las reglas de autorización, la zona horaria y la política de evidencias y conservación. Antes de comercializar deben definirse precios, límites y condiciones de servicio.

Los cambios de alcance, aislamiento, roles o uso de datos requerirán una nueva versión del contrato con motivo e impacto. Los ajustes de implementación que respeten estas reglas podrán resolverse durante el desarrollo.
