# AXS Corporativo — trazabilidad del contrato y la auditoría

Fecha de incorporación: 27 de octubre de 2026, hora de Ciudad de México.
Alcance de esta matriz: documentos de referencia y aceptación del paquete estructural C0–C5. No modifica el contrato ni aprueba un piloto integral.

## Documentos incorporados y procedencia

| Documento | Origen | Commit fuente | Blob conservado |
|---|---|---|---|
| [Contrato de desarrollo v1.1](AXS_CORPORATIVO_CONTRATO_V1.md) | [PR #87](https://github.com/B10sp4rt4n/MSP_AXS/pull/87) | 7844ce74367d35796fd7abbcbff70bdc1334f28b | 99655ad564d8f90798be97d03fd1f6346f4a3bc1 |
| [Auditoría base](AXS_CORPORATIVO_AUDITORIA_BASE_20261023.md) | [PR #95](https://github.com/B10sp4rt4n/MSP_AXS/pull/95) | 3129f0f0df46752ef0b34bdb3c02af00e1ea15eb | 2ade9b81e596db9fd2bac80fe1553f4f396ffd10 |

Los dos archivos se incorporan íntegros mediante sus blobs de Git y sus commits se conservan como padres de la integración. Sus fechas, propuestas y estados históricos corresponden a la fecha de cada documento. Esta matriz y el [cierre del ensayo](evidence/AXS_CORPORATIVO_CIERRE_ENSAYO_Y_REVISION_20261027.md) identifican el estado posterior.

Los PR originales continúan abiertos mientras no se integren a su destino main. Incorporarlos al head de #103 resuelve la ausencia documental en el paquete revisado; no constituye una fusión de esos PR a main.

## Correspondencia entre etapas propuestas e implementación

La auditoría fue una propuesta anterior al desarrollo. Los nombres C2/C3 se usaron después para entregas distintas; conservar el nombre de una rama no prueba cumplir la etapa homónima original.

| Etapa propuesta en la auditoría | Entrega que realmente existe | Estado |
|---|---|---|
| C0 — frontera de modalidad/tenant | PR #96: discriminador en raíz técnica compartida, denegaciones residenciales, pruebas de FK/RLS/regresión | Validada por CI del alcance C0; ensayo corporativo solo en sandbox |
| C1 — entidades y asignaciones corporativas | PR #97: sedes, destinos, memberships y asignaciones; cuotas; API separada | Directorio owner ensayado; administración completa de miembros y operación anfitrión/recepción no aceptadas por este ensayo |
| C2 — recorrido de visitas corporativas | El PR #98 llamado C2 implementa aprovisionamiento GLOBAL y cuotas, no visitas | Recorrido propuesto de invitación/entrada/salida pendiente |
| C3 — privacidad y piloto sintético | PR #100: Superadmin, expediente privado asistido, conciliación y controles de recuperación/sandbox; #102 portal; #103 corrección SQL/CI | Ensayo estructural y un expediente de acceso ficticio completados; piloto integral y ejecución material de cuatro derechos pendientes |

## Trazabilidad de criterios del contrato

"Parcial" significa que existe evidencia para una parte identificada, sin aceptar el criterio completo. "Pendiente" no queda dispensado por excluir esa función del ensayo estructural.

| Criterio de aceptación del contrato | Evidencia existente | Estado y falta por cubrir |
|---|---|---|
| Cliente corporativo sin vivienda ni residente ficticios | Esquema corporativo y guards independientes de Casa/scopes residenciales; creación de empresas/owners por Superadmin | Parcial: directorio sin viviendas; falta recorrido de anfitrión y visitante. Los roles corporativos se obtienen de membership, no del rol global de la identidad de prueba |
| Tenant no consulta/modifica datos, QR o evidencias de otro | Directorio GET y creación de sedes POST A↔B denegados con Clerk real; ARCO GET/POST B→A denegados; RLS cuatro escrituras 42501 | Parcial: consultas/altas de directorio y ARCO delimitados; QR/fotos corporativos no operados; no todas las rutas ni direcciones ARCO fueron ensayadas |
| Roles respetan sedes/facultades; owner no habilita plan | Guards, asignaciones y denegación sin GLOBAL en CI; Superadmin separado de membership; owner existente y rechazo de autoasignación | Parcial: owner y GLOBAL ensayados; host/recepción/multi-sede cubiertos sintéticamente donde están implementados, sin recorrido real completo |
| Invitación/QR válido y rechazo de QR ajeno/vencido/cancelado | Frontera que impide usar rutas residenciales con empresa | Pendiente de recorrido corporativo específico; la denegación residencial no implementa QR empresarial |
| Visita inesperada requiere autorización válida | Separación de modalidad y directorio | Pendiente |
| Reintentos y concurrencia no duplican entradas/salidas | Cuotas y recuperación de altas de directorio; pruebas técnicas de concurrencia separadas | Pendiente para movimientos corporativos; no extrapolar idempotencia del aprovisionamiento al ciclo de visitas |
| Visita expirada y abierta permanece visible y puede cerrarse | No hay estancias corporativas habilitadas en el ensayo | Pendiente |
| Evidencias respetan configuración y permisos | Fotos/retención y otras capacidades excluidas del sandbox corporativo | Pendiente para operación corporativa |
| Horas y correcciones con trazabilidad | Zona horaria de sede capturada; expediente ARCO con fechas y cuatro avances | Parcial: no valida movimientos ni rectificación de datos del titular |
| Casos ARCO de los cuatro derechos con identidad, decisión y constancia | Un caso de acceso ficticio: recibida→verificada→resuelta→ejecutando→cerrada, versión 5; cierre con pendientes rechazado | Parcial: registro asistido de acceso; referencias ficticias no demuestran identidad, entrega o ejecución material; rectificación/cancelación/oposición integrales pendientes |
| Datos bloqueados fuera de búsquedas/reportes/fotos de operación | Pruebas técnicas de retención/bloqueo y fronteras según matriz ARCO de C3 | Pendiente de aceptación empresarial por categoría y tratamiento; el expediente cerrado no prueba bloqueo o borrado |
| Restauración reaplica decisiones ARCO y conserva reintentos | CI de cuarentena/recuperación de memberships y revisión asistida de privacidad | Parcial: no demuestra reaplicación empresarial general de cancelaciones/oposiciones/supresiones en objetos y copias |
| Canal ARCO sin cuenta y durante suspensión/baja | Guía pública /privacidad/arco; guard ARCO separado de habilitación comercial; designación y membership comprobadas; revocación real ARCO sin perder directorio | Parcial: guía y registro privado no son recepción pública automática; falta aceptar canal/procedimiento operativo por responsable, también bajo suspensión/baja |
| Regresión residencial de QR/atención/evidencias/movimientos/recuperación | Suite general, navegador y PostgreSQL de integración 498c737 aprobados; matriz de modalidad y regresiones incluidas en los workflows | Evidencia CI sintética/descartable del paquete; no representa repetir un piloto productivo residencial ni aceptar todas las rutas del sistema |

## Evidencia técnica de referencia

Paquete de código previo a esta incorporación documental: 498c737eafa43442ca70b6e0dedf046173d0ba21.
- [Tests del PR, SUCCESS](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40622545801): 1196 Python aprobadas, 57 omitidas, cobertura 82 %; frontend, tipos y navegador aprobados.
- [PostgreSQL RLS del PR, SUCCESS](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40622545755): 122 aprobadas.
- Las ejecuciones por push 40622541473 y 40622541532 también finalizaron SUCCESS.
- El nuevo commit de incorporación cambia solo documentación y conserva idénticos los blobs de aplicación, tests, workflows y migraciones. El resultado CI del nuevo head se registra en #103, para no generar un commit adicional únicamente para documentar un SHA ya validado.

La captura final de Salvador confirmó que la restauración de designación devolvió Empresa A y el expediente ficticio cerrado con cero pendientes. El ensayo no envió respuestas a titulares ni ejecutó borrados empresariales reales.

## Resultado de la incorporación

Se resuelve la falta de contrato y auditoría dentro de la rama integrada. Se conserva su exigencia y se vincula cada criterio a evidencia concreta o a un pendiente. La aceptación lograda corresponde al directorio y registro asistido del ensayo; el piloto corporativo integral continúa sujeto a los criterios restantes.

El próximo punto de revisión es la integración de la cadena por dependencias, con sus migraciones y condiciones de despliegue revisadas. La sola incorporación de documentos no habilita datos reales, funciones de visitantes ni despliegues productivos.
