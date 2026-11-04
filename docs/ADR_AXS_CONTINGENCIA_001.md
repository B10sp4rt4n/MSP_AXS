# AXS Contingencia 001 — Continuidad residencial por nodo local

Estado: propuesta de arquitectura + laboratorio O0 aislado. Fecha: 2026-11-03, CDMX.

## Necesidad y decisión

Salvador solicita continuidad ante pérdida de internet como capacidad transversal de
AXS para condominios y residenciales. Un mismo motor, con habilitación, responsables,
dispositivos, vigencias y reglas por inmueble. El HTML autónomo inspira la interfaz;
un Site puede distribuir materiales, pero la operación debe estar preparada en el
equipo ANTES de la caída. Google Sites no es el motor de persistencia/sincronización.

Se propone comenzar por HTML servido en localhost y SQLite en un nodo de caseta.
No requiere servicios IA ni un proveedor SaaS adicional. No acredita costo total cero:
equipo, energía, soporte, respaldos y eventual instalación se dimensionan por inmueble.
La variante PWA/tableta es posterior y debe probar persistencia, permisos del navegador
y recuperación en cada dispositivo admitido. No se presupone equivalencia con localhost.

Requisito confirmado: disponible arquitectónicamente para todos los residenciales.
Decisión de diseño propuesta: activación explícita por inmueble y dispositivo;
no habilitación global automática. Esto no extiende capacidades residenciales a empresas.

## Base observada y límites de integración

Repositorio: `B10sp4rt4n/MSP_AXS`; main observado: `76bc9d619836f0872241741570fb7974e51d2bf6`.

| Fuente de código | Qué aporta | Qué falta para offline |
| --- | --- | --- |
| `backend/services/event_outbox.py` | CORE confirma operación y evento juntos; reenvío por UID; comparación de contenido al deduplicar | Recepción autenticada desde nodos, acuses por evento y conciliación de hechos históricos |
| `backend/services/visita_service.py` | Transiciones condicionadas y validación actual de reglas y autorización | Tratamiento explícito del tiempo observado offline; no reejecutar como entrada nueva al sincronizar |
| `backend/routers/qr_router.py` | Consulta servidor, scope, token, vigencia y estado actual | Credencial verificable offline o proyección autorizada compatible |
| `backend/services/qr_service.py` | Formato `AXS\|visita_id\|token`, token aleatorio | No es una credencial firmada autónoma; no prometer compatibilidad automática |
| `scripts/check_core_rls.py` | Revisa privilegios limitados y RLS de tablas/bandejas | Catálogos de nodos, políticas y grants propios del canal de contingencia |

O0 añade exclusivamente `labs/contingency/`, este ADR y su workflow de pruebas.
No modifica imports/rutas de AXS, SQL productivo, flags, QR, Clerk, Alexa ni integraciones.
La rama parte de main y NO incorpora el candidato corporativo #104 ni AXS Agents #101.
La integración futura debe revisar el main actualizado y las reglas de modalidad
residencial del candidato corporativo, sin fusionar cadenas paralelas por esta iniciativa.

## Topologías admitidas y frontera física

| Escenario | Diseño propuesto | Restricción |
| --- | --- | --- |
| Una caseta/un dispositivo | Un nodo + SQLite local | Primer piloto candidato; O0 es solo laboratorio |
| Varias terminales con LAN | Un servicio local coordinador, con autenticación y transporte protegido | Las terminales no abren un archivo SQLite compartido; O0 no expone LAN |
| Casetas incomunicadas | Dominios de autorización asignados por caseta o contingencia restringida | No garantizar QR de un solo uso global ni antipassback sin coordinación |

Un corte de internet, un corte de LAN y un corte eléctrico son fallas distintas.
La operación local no garantiza disponibilidad sin energía o con el nodo averiado.
No hay apertura de plumas/cerraduras en O0; no bloquear físicamente egreso por una
falla de software. Los procedimientos de salida de emergencia pertenecen al inmueble.

## Contrato mínimo de la copia preparada (O1 propuesto)

El servidor deriva tenant/MSP de autoridad autenticada, nunca del cuerpo arbitrario
del guardia. Emite un paquete verificable con versión de esquema/política, identificador,
fecha de emisión, vencimiento, epoch del nodo, alcance MSP/tenant/caseta/dispositivo,
clave emisora y firma. El equipo conserva solo la clave pública emisora; claves de
firma del servidor no se distribuyen a los nodos.

Contenido mínimo: destinos necesarios, autorizaciones elegibles con su ventana,
asignación de caseta y límite de uso, entradas abiertas y reglas de contingencia.
No descargar catálogo completo de clientes, expedientes ARCO, identificaciones,
fotografías, teléfonos, JWT de usuarios ni secretos CORE/EVENT/GOV.
Los identificadores mínimos siguen siendo datos que requieren protección.

La habilitación usa identidad de dispositivo, guardia previamente verificado y
permiso temporal acotado. Clerk/GOV verifican al preparar o renovar; una caída no
crea usuarios, roles ni autoridad GLOBAL. Caducidad y revocación son controles
distintos: sin conexión no conocemos una revocación posterior a la copia.

La hora de prueba de O0 dura una hora por conveniencia sintética. NO es una vigencia
productiva aprobada. La vigencia real, tolerancia de reloj y duración máxima se
seleccionan y justifican por inmueble antes de cualquier piloto.

## Reglas durante la contingencia

| Condición | Comportamiento propuesto |
| --- | --- |
| Copia y permiso vigentes; visita elegible y pase válido | Permitir confirmación local explícita; guardar movimiento y pendiente en una transacción |
| Copia vencida, firma inválida, dispositivo no habilitado o reloj no confiable | Bloquear nuevas autorizaciones/entradas automáticas; mostrar procedimiento de contingencia |
| Entrada abierta en la copia | Conservar observación de salida; distinguirla de autorización y de actuación física |
| Visita desconocida/sin autorización descargada | No inventar autorización; excepción humana solo con procedimiento previamente aprobado y registro separado |
| Imposible persistir | No mostrar éxito; conservar intención y recuperar estado antes de reintentar |
| Reintento de la misma solicitud | Mismo identificador y contenido; devolver el hecho ya guardado |
| Identificador repetido con contenido diferente | Rechazar y señalar integridad; nunca confirmar como duplicado válido |

La pantalla muestra: modo real de operación, última copia, vencimiento, guardia/caseta,
pendientes, conflictos y capacidad de almacenamiento. O0 no detecta internet: todas
sus acciones son locales y los botones simulan comunicación con otro SQLite.
No muestra un indicador de conectividad ficticio como medición de red.

## Diario, sincronización y conflictos (O2 propuesto)

Identidad de hecho: UID global + MSP/tenant/nodo/epoch + secuencia local. Conservar
guardia/caseta, visita/destino, operación, instante observado y su calidad de reloj,
copia/política aplicada, digest y autenticidad del nodo. La hora de recepción del
servidor se conserva aparte: no reemplaza el instante observado por la caseta.

1. Escribir diario y proyección local atómicamente. Nunca replicar tablas completas
   con una estrategia de «última escritura gana».
2. Enviar lotes ordenados del nodo autenticado; validar identidad, esquema, firma,
   ámbito, epoch, secuencia y contenido. La carga de un evento no autoriza una puerta.
3. Guardar hecho recibido y resultado de conciliación de forma durable. En la futura
   integración, enlazar su evento AUP mediante la outbox transaccional existente.
4. Acusar por UID + digest + resultado. El nodo marca recibido solo tras verificar
   el acuse; si se pierde, reenvía el mismo UID. Transporte al menos una vez,
   procesamiento idempotente: no prometer entrega «exactamente una vez».
5. Separar «recibido» de «aplicado a la proyección» y «en revisión». Si hubo cancelación,
   uso en otra caseta, revocación o secuencia incompatible, conservar el hecho observado
   sin sobrescribir silenciosamente el estado central. La decisión responsable será
   otro registro auditable; no editar retroactivamente el movimiento original.

No llamar al endpoint actual de entrada para reproducir hechos de horas anteriores:
su tiempo/reglas representan una operación presente y podría emitir notificaciones
engañosas. Definir un receptor específico; evitar avisos de llegada en tiempo real
para una llegada histórica sincronizada. Contratos API aún no implementados.

## Protección, conservación y operación

Antes de datos reales: cifrado local y respaldo cifrado, claves ligadas al dispositivo,
política por categoría y responsable, acceso del sistema operativo, borrado/retención
tras acuse y plazo autorizado, ARCO también sobre copias locales, capacidad/disco lleno,
revocación de nodo perdido y actualización firmada. No purgar hechos pendientes para
liberar espacio; bloquear nuevas capturas de forma visible si no pueden conservarse.
SQLite por sí solo no resuelve cifrado ni custodia. Triggers y hashes no impiden a
un administrador del archivo sustituir la base o restaurar una copia antigua.

## Entregas y condiciones de aceptación

| Fase | Resultado | Gate |
| --- | --- | --- |
| O0 — este paquete | HTML localhost, SQLite, dos escenarios ficticios, receptor simulado y pruebas | Persistencia, aislamiento lógico, atomicidad, concurrencia, reintentos, vencimiento y conflictos sintéticos |
| O1 — siguiente | Paquete verificable, registro de dispositivos, habilitación por tenant, guardia y política | Firma/alcance, clave rota, revocación, reloj, replay de copia antigua; sin datos reales inicialmente |
| O2 | Receptor AXS + bandejas, acuses verificables y revisión de conflictos | HTTP autenticado, PostgreSQL/RLS desechable, fallos intermedios y notificaciones históricas |
| O3 | Piloto controlado de una caseta | Equipo real, corte físico de conexión, reinicio, almacenamiento/recuperación, permisos/privacidad y autorización de activación |
| O4 | Varios dispositivos/casetas y habilitación progresiva | Concurrencia LAN, particiones, límites de un solo uso, soporte/monitoreo y recuperación por nodo |

Disponible para todos como diseño común no significa desplegado/habilitado en todos.
No aumentar la fase por contar pruebas de otra: SQLite sintético no acredita RLS,
autenticación productiva, corte eléctrico, firma, operación iPad ni piloto de San Luis.

## Evidencia O0

Véase `labs/contingency/README.md`: instrucciones reproducibles, pruebas y límites.
Evidencia automatizada por commit: workflow `contingency-lab.yml`.
La evidencia del navegador/servidor local debe identificarse como sintética;
no conservar capturas con personas o datos reales en este laboratorio.

## Referencias técnicas

- https://sqlite.org/wasm/doc/tip/persistence.md — alternativa navegador, no usada por O0.
- https://sqlite.org/atomiccommit.html — atomicidad y límites del almacenamiento.
- https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API — preparación offline de una futura PWA.

Decisiones aún abiertas: hardware objetivo del primer piloto, vigencia productiva,
custodia de claves, cifrado local, política de excepciones y topología de varias casetas.
