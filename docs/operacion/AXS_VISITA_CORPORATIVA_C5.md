# Visita corporativa C5 — contrato de primera versión

Estado: implementación candidata; no migrada, desplegada ni habilitada en producción.

## Alcance

Registro explícito de visita en empresa/sede/destino con anfitrión corporativo vigente. No usa Casa, RESIDENTE, QR residencial ni notificaciones Alexa. La primera versión guarda una referencia opaca de hasta 80 caracteres alfanuméricos, guion o guion bajo; no incorpora nombre del visitante, documentos, biometría, fotos, apertura física ni vigencia automática. La referencia permite enlazar un folio administrado externamente y puede seguir constituyendo dato personal por vinculación: no se considera anónima.

La versión permite probar el ciclo de registro con datos sintéticos. No sustituye una aceptación productiva con política de conservación, vigencia, identificación y evidencia aprobadas. No se deben introducir nombres, correos o documentos en la referencia. No se implementan controles de aforo ni una cuota de visitas: se mantienen las cuotas existentes de sedes/destinos del directorio.

## Máquina de estados

| Operación | Estado inicial | Estado final | Quién |
| --- | --- | --- | --- |
| Preregistrar | Sin visita | preregistrada | owner/admin, anfitrión propio, recepción de la sede |
| Autorizar | preregistrada | autorizada | owner/admin o anfitrión de la visita |
| Entrada | autorizada | dentro | owner/admin o recepción de la sede |
| Salida | dentro | cerrada | owner/admin o recepción de la sede |
| Cancelar | preregistrada/autorizada | cancelada | owner/admin o anfitrión de la visita |

Membresía y asignación de sede se consultan de nuevo por solicitud. Host sólo consulta sus visitas, incluso cuando solicita bitácora. GLOBAL/MSP no reemplazan una membresía operativa. La autorización y entrada requieren destino/sede activos y anfitrión vigente con alcance de sede. Si el anfitrión se revoca después de entrar, recepción vigente puede registrar la salida. Una solicitud que ya está en curso no equivale a una revocación retroactiva; no se promete coordinación linealizable con un futuro administrador de membresías.

El UUID del preregistro es estable. Repetir UUID con payload/creador/sede distintos devuelve 409; repetirlo idéntico devuelve la visita existente. Repetir un movimiento ya reflejado en el estado actual conserva sus horarios y no crea otro evento. Si el estado ya avanzó a otro, la solicitud anterior puede devolver 409 y el cliente debe consultar el estado. Las transiciones bloquean la fila de visita en PostgreSQL. La creación se serializa por empresa. Operación y evento outbox se confirman en una transacción; una respuesta perdida tras el commit se recupera repitiendo la intención estable.

## Rutas y pantalla

`/corporativo/{tenant_id}/sedes/{site_id}/visitas`: POST preregistro, GET últimas 50 por defecto (máximo 100). GET `/capacidades` devuelve anfitriones de sede y facultades. GET `/{visit_id}` consulta la visita; PATCH `/{visit_id}/{autorizar|entrada|salida|cancelar}` ejecuta movimiento. GET `/{visit_id}/bitacora` consulta los eventos encolados, entregados o pendientes, del registro corporativo. No se denomina custodia inmutable: esa propiedad corresponde al EVENT que recibe el outbox, no a esta consulta operativa.

Pantalla: `/dashboard/corporativo/visitas?empresa=…&sede=…`, enlazada desde la sede seleccionada en el directorio. Muestra controles según capacidades verificadas por servidor y pide confirmación del movimiento. Al perder respuesta de preregistro conserva UUID/payload; no cambia silenciosamente de solicitud. Identidad, empresa o sede diferentes desmontan el contexto anterior. Una denegación oculta los datos y controles.

## Datos, permisos y privacidad

`corporate_visits` tiene metadata ORM separada para no crearse durante arranque. PK compuesta tenant/UUID y FKs compuestas a destino (empresa/sede/destino) y anfitrión (empresa/usuario) impiden mezclas aun por SQL. CHECKs restringen estados y coherencia temporal de entrada/salida. FORCE RLS exige app.tenant_id; axs_core_app sólo obtiene SELECT, INSERT y UPDATE de estado/actores de autorización/horarios. No puede editar referencias o destinos, borrar ni truncar. La autorización por rol y sede sigue siendo responsabilidad del servidor: RLS por tenant no protege contra un backend comprometido capaz de cambiar su contexto.

EVENT recibe entidad `visita_corporativa`, acción, identidad del operador, hash de sesión y sede/estado. No copia la referencia del visitante. La bitácora filtra por empresa y visita antes de devolver los eventos.

`GET /arco-corporativo/{tenant_id}/visitas?subject_ref=…` permite al operador de privacidad designado consultar por referencia exacta, máximo 100 registros. Requiere la autoridad y designación existentes de ARCO. Esta consulta no depende de las banderas de visitas/directorio ni de la suspensión comercial. No sustituye el expediente ARCO, la determinación, rectificación, anonimización o eliminación; esos actos y una política de conservación para esta nueva categoría deben definirse antes de un piloto con datos personales reales. No se declara cumplimiento legal por implementar esta ruta.

## Instalación futura

1. Ensayar el SHA exacto y la migración `migrations/20261115_corporate_visits_c5.sql` con PostgreSQL aislado. Preservar la separación A/B y las denegaciones residenciales.
2. Operador autorizado ejecuta migración manual, una sola aplicación: añade UNIQUE de destino y tabla protegida. Si existe la tabla, detener e inspeccionar. No dar DDL al runtime ni alterar permisos EVENT/GOV.
3. Mantener AXS_CORPORATE_VISITS_ENABLED=false hasta la aceptación. La API también requiere AXS_CORPORATE_API_ENABLED y empresa habilitada/membresía vigente. El frontend por sí solo no concede acceso.
4. Al habilitar la bandera en PostgreSQL, el arranque ejecuta `check_corporate_visit_schema.check_schema` en sólo lectura: PK, FKs, RLS, política y columnas mutables. Si falta la migración o hay permisos fuera de contrato, el arranque falla.
5. Publicar backend/frontend coordinados sólo en ensayo. Revisar privacidad, vigencia, conservación y necesidades de identidad/evidencia; luego obtener autorización independiente antes de cualquier activación productiva.

Reversión: deshabilitar la bandera y volver a la versión compatible conservando datos y migración. No borrar tabla, retirar RLS ni volver al propietario como conexión runtime.
