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

La integración no cambia backend ni introduce migraciones. El backend coincide
con #40. Desde `a0ecdf58a26cd5e7291708fb82786a8d0598eb03`, el frontend añade
foco y desplazamiento a la confirmación, y ajustes de ancho para móvil. Ese ajuste
está en el PR y todavía no se ha desplegado. Agrega pruebas y documentación
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

## Estado verificable al 9 de octubre de 2026

| Control | Resultado y alcance |
| --- | --- |
| Dos ciclos con mismo MSP | Ejecutados por el usuario desde Clerk/UI en desarrollo sobre b349cb9; contrastados con CORE/EVENT |
| Permisos independientes | #31 de C1 y #32 de C2 revocados; #30 local activo; #31 seguía revocado antes de otorgar #32 |
| Historial | Ambos contratos cerrados; seis eventos entregados; visita y evidencia históricas sin cambios |
| Autoridad temporal | lab261009_ui_v1_authority revocada a las 20:51:30.934 UTC |
| Ensayo de reversión | Frontend anterior y restauración exitosos en desarrollo; backend y datos conservados |
| CI de a0ecdf5 | Tests y evidencia offline aprobados; PostgreSQL bloqueado antes del checkout por cuota Docker Hub |
| Pantalla estrecha | Chromium con CSS real aprobado en 320/360/1280 px; inspección de PNG pendiente por descarga HTTP 403 |
| Revisión independiente | Pendiente; la revisión del autor no equivale a aprobación de mantenedor |
| Producción | Retenida; sin fusión ni despliegue autorizado |

Evidencia de CI del cambio de aplicación a0ecdf5:
- [Tests #237](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/37990872582).
- [Evidencia offline #3](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/37990872543).
- [PostgreSQL #67](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/37990872540):
  dos intentos, ambos bloqueados por `toomanyrequests` al descargar postgres:16.
- Artifact `provider-console-responsive`, ID 11645401387: seis PNG del ensayo
  sintético. No acredita sesión real de Clerk ni inspección visual humana.

Los cambios documentales posteriores no alteran la aplicación; aun así, revisar
el CI del HEAD final antes de fusionar. No trasladar un resultado verde de otro
SHA sin identificar su alcance.

### Contratos del recorrido guiado

| Versión | UUID | Apertura UTC | Baja UTC | Scope |
| --- | --- | --- | --- | --- |
| 1 | 549f64fe-f38f-49d6-b9fd-5bd7b0040af9 | 20:13:34 | 20:25:49 | 31 |
| 2 | 2a2a88c2-dcaa-4cfc-bc91-ba8416608a39 | 20:46:38 | 20:50:33 | 32 |

Tenant `lab_ui_261009_condo`, MSP `lab_ui_261009_msp`. No repetir el ensayo
sobre estos contratos cerrados: se conservan como evidencia. El ensayo guiado
no incluyó sesión Clerk del guardia; JWT reutilizado, concurrencia e idempotencia
se acreditan mediante las pruebas automatizadas y el ensayo HTTP separado.
La referencia histórica del scope 31 es `ensayo-ui-contrato-1`; no se corrigió
retroactivamente. La del scope 32 es `ensayo-ui-permiso-2`.

## Lista de cierre para el revisor

- [ ] Confirmar HEAD y base finales del PR #42 y leer sus cambios.
- [ ] Aprobar PostgreSQL/RLS del candidato: autenticación de registro o reintento
  cuando exista cuota. No omitir el gate ni tratar el fallo de infraestructura
  como prueba aprobada. Si se configura autenticación, el contenedor de servicio
  necesita credenciales antes de iniciar los pasos del job.
- [ ] Inspeccionar capturas: texto legible, confirmación y botones visibles,
  historial identificable y ausencia de desbordamientos. Las aserciones
  automáticas no sustituyen esta inspección.
- [ ] Confirmar que cancelar no escribe y que cada baja contiene el UUID vigente.
- [ ] Revisar preservación de #30, revocación de #31/#32 y auditoría correlacionada.
- [ ] Registrar aprobación independiente en GitHub. Revisor aún no asignado;
  no se enviaron solicitudes ni se presume aprobación.
- [ ] Elegir PR agregado #42 o ruta de PR individuales; no fusionar ambas a ciegas.
- [ ] Obtener autorización expresa de publicación; main activa producción.

## Guion reutilizable de aceptación Clerk + UI + API

El resultado ejecutado y sus límites se describen arriba. Esta lista es un guion
para futuras repeticiones, no una afirmación de que cada punto se ejecutó.

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

## Reversión ensayada en desarrollo

Proyecto AXS Development `c04faff4-37ba-4df4-a6ce-a4d5d5ff881b`;
entorno `5f5b4e0c-c4ce-457c-96a4-b65ebf723354`. Aunque el entorno se llama
production en Railway, pertenece exclusivamente al proyecto de desarrollo.

| Paso | Commit frontend | Deployment | Resultado |
| --- | --- | --- | --- |
| Regreso a frontend anterior | cef637b5571567a7727720d613dd2b5b3d553269 | b29d2b39-c779-46d0-b16a-940626bd35f4 | SUCCESS 20:55:27 UTC |
| Restauración del panel | b349cb9bdd88707615314bb6c79b27aa0e95a8ff | 5b3e8c2f-6b22-4412-9551-985b45be5746 | SUCCESS 20:57:10 UTC |

Backend conservado en deployment `d44e11a5-ec37-4cca-80a1-43675f1be9e5`.
Salud frontend/backend 200 durante el regreso. Tras restaurar: /health y /ready
backend 200, contratos sin sesión 401, panel sin sesión redirige a /sign-in.

Digest de filas de contratos sintéticos: `01ec281d52632d5db5433c0b47164a57`;
scopes: `3beda5744e6d02002b0b463d67753606`. Idénticos antes, durante y después;
seis eventos entregados y autoridad temporal revocada. No se restauró base de
datos ni se bajó esquema. No se ejecutó un recorrido autenticado completo en la
interfaz anterior. Estos deployments de desarrollo NO son destinos productivos.

## Publicación futura (no ejecutada)

Responsables pendientes de designar: mantenedor revisor y operador de publicación.
Salvador conserva la decisión de autorizar producción. No se ha fijado ventana.

Secuencia una vez aprobados los controles y autorizada la salida:

1. Registrar HEAD/base aprobados, deployments productivos de partida y versión
   compatible de retorno; comprobar que no hay cambios ajenos por publicar.
2. Confirmar configuración productiva, salud y outbox pendiente mediante lectura.
   No copiar IDs, URLs de desarrollo, claves Clerk de prueba ni autoridades del lab.
3. Fusionar únicamente la ruta elegida. Observar el despliegue automático hasta
   SUCCESS; una build en cola no es publicación completada.
4. Verificar salud, rechazo sin sesión y observabilidad. Cualquier ensayo con
   escritura requiere tenant sintético y autorización específicos de producción.
5. Si falla la interfaz, aplicar la reversión frontend compatible acordada;
   conservar backend versionado, contratos, scopes y auditoría. Registrar resultado.



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
