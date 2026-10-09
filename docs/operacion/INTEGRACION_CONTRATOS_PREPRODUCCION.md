# Integración de contratos previa a fusión

Estado: **producción retenida**. Este documento prepara la revisión; no autoriza
fusión, promoción, cambios de configuración productiva ni relaciones reales.

## Candidato combinado

Base `bc35bfd8576bb545ccbf51d82a0bac1dbf04cc5c` (#38, contratos versionados).
Rama aislada `integration/provider-contracts-preproduction` reúne sin conflictos:

| PR | Commit integrado | Aporte |
| --- | --- | --- |
| #39 | `eaf8d15897a30dad6e23b37397c34e6a1af077d8` | Reproducción legacy y regresión de dos ciclos |
| #40 | `b349cb9bdd88707615314bb6c79b27aa0e95a8ff` | Panel, modelo frontend y prueba Chromium sintética |
| #41 | `82a321c9727c1bcc66ae4d01dfa33c8805e5a2f8` | Ensayo HTTP conectado, fixtures y evidencia verificada |

La integración no cambia backend ni introduce migraciones. Su código de
aplicación backend/frontend coincide con #40; agrega las pruebas y documentación
de los otros PR. El ensayo HTTP documentado se ejecutó sobre #40 desplegado en
desarrollo, no sobre un nuevo despliegue de esta rama. CI del PR de integración
comprueba el árbol combinado. Los tres PR de origen permanecen abiertos.

## Revisión técnica realizada

- Lectura y mutaciones de proveedores requieren Authority GLOBAL activa en GOV.
  El rol MSP_ADMIN y la sesión Clerk por sí solos no confieren esa autoridad.
- El panel exige lectura autorizada antes de mostrar acciones; una solicitud de
  baja conserva el UUID del contrato seleccionado. Backend comprueba de nuevo
  contrato, proveedor y procedencia bajo bloqueo transaccional del condominio.
- UUID estable en reintentos de apertura; scopes nuevos para recontratación;
  comprobante persistido por contrato cerrado. Revocación y auditoría comparten
  transacción CORE; EVENT recibe el mismo UID mediante outbox.
- Cambio de identidad desmonta el estado del panel. Exclusión de doble envío.
  Si falla la lectura posterior a una mutación, conserva comprobante y retira
  controles obsoletos. La lectura de historial e inventario son dos peticiones,
  no una instantánea atómica; la validación definitiva permanece en backend.
- Permisos locales se conservan por procedencia explícita, no por rol aparente.
- El cliente API tiene un fallback productivo preexistente. Toda prueba conectada
  exige URL de desarrollo explícita y el gate de configuración del frontend.
  No usar el fallback como entorno de ensayo.

Esta revisión del autor no equivale a aprobación independiente de mantenedor.

## Puertas pendientes antes de fusión

1. CI verde del commit combinado: backend/cobertura, PostgreSQL con RLS y
   concurrencia, frontend/TypeScript, Chromium sintético y evidencia offline.
2. Sesión real de Clerk de prueba → Next → API en desarrollo. Comprobar identidad
   mapeada y autoridad temporal sintética, sin reutilizar autoridades reales.
3. Revisión visual en escritorio y pantalla estrecha: confirmación legible,
   errores visibles, historial y permisos identificables, ninguna acción oculta
   por desbordamiento o dependiente exclusivamente de color.
4. Revisión de cambios por mantenedor y elección explícita del modo de integrar:
   este PR agregado **o** los PR individuales. No fusionar ambas rutas a ciegas;
   volver a ejecutar CI si cambia base, cabeza o resolución de conflictos.
5. Autorización de publicación. `main` dispara despliegue productivo: fusionar
   allí es publicar. Mientras producción siga retenida, conservar el borrador.

## Guion de aceptación Clerk + UI + API (aún no ejecutado)

Destino exclusivo: frontend y backend del proyecto **AXS Development**. Usar
otro prefijo sintético y UUID nuevos; los fixtures del ensayo HTTP ya están
cerrados y se conservan como evidencia.

- Autenticar operador mediante Clerk de prueba. Si se necesita login/MFA, el
  usuario completa el paso personalmente; no compartir contraseñas ni códigos.
- Registrar sólo para esta prueba el vínculo Clerk con una identidad sintética
  y una autoridad temporal. Registrar IDs y hora de inicio, sin tokens.
- Con identidad sin autoridad, consultar y verificar rechazo y ausencia de
  controles de operación. Volver al operador y verificar que no queda estado
  de la sesión anterior.
- Desde el panel: abrir C1, otorgar permiso, verificar acceso del guardia; cerrar
  C1 y comprobar denegación sin renovar su sesión. El administrador local conserva
  acceso. Abrir C2 para el mismo MSP: el guardia continúa denegado hasta permiso
  nuevo; cerrar C2 y comprobar nueva denegación.
- Revisar dos contratos cerrados, scopes de cada ciclo, comprobantes y eventos.
  Correlacionar UUID/UID con las bases de desarrollo; no registrar Authorization.
- Revisar errores de entrada y consulta, cancelar una confirmación y comprobar
  ausencia de mutación. El fallo ambiguo de red ya cuenta con test sintético;
  cualquier ensayo conectado debe limitarse al tenant de prueba.
- Revocar la autoridad temporal al terminar, también si falla. Conservar historia
  sintética y evidencia. Cerrar sesión y anotar resultados observados/pedientes.

## Publicación y reversión (procedimiento, no ejecutado)

Antes de una publicación futura autorizada, registrar los SHA e IDs de deployment
realmente activos de backend/frontend, el candidato aprobado, estado de esquema,
salud y pendientes de outbox. Confirmar compatibilidad de esa versión de retorno
con contratos versionados. La revisión actual no ha certificado un deployment
productivo concreto como destino de reversión.

Este candidato no requiere bajar esquema ni restaurar datos. Si falla sólo el
panel, retirar/revertir su código a una versión frontend compatible y conservar
backend de contratos, datos y eventos. Preparar la reversión en rama aislada y
validarla en desarrollo antes de promoverla con autorización.

Si aparecen autorizaciones incorrectas, errores repetidos al cerrar contratos o
auditoría pendiente anormal, detener nuevas operaciones administrativas y revisar
el alcance. No intentar "deshacer" una baja reactivando scopes, reabriendo contratos
cerrados ni volviendo a asociar manualmente el MSP. Un vínculo nuevo usa otro
contrato y permisos nuevos. Mantener disponible la evidencia del incidente.

No volver a backend anterior a #38 sin demostrar que reconoce y exige contract_id.
No restaurar una copia antigua de CORE/GOV/EVENT como rollback de interfaz: podría
recuperar permisos revocados o perder auditoría. Conservar outbox y eventos;
resolver incidencias mediante cambio compatible y revisado. Un restore por
incidente de base de datos pertenece al procedimiento de recuperación separado.

Después de publicar o revertir, verificar salud, rechazo sin sesión, autoridad,
scopes revocados, contratos cerrados y entrega de outbox. Pruebas con escritura
en producción requieren autorización específica y un tenant sintético aprobado;
este documento no la concede.
