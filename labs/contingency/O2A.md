# O2a — Receptor autenticado, acuses y conciliación aislada

Estado: laboratorio funcional; depende de #106, que depende de #105. Rama propia.
Es la primera frontera de O2. **La integración con el backend AXS y PostgreSQL/RLS
no está implementada ni se da por verificada con estas pruebas.**

## Flujo implementado

`VerifiedJournal` conserva el paquete firmado histórico de cada movimiento, incluso
al instalar una versión nueva. `sync_authenticated` envía los pendientes en orden.
El nodo firma la entrega completa (paquete + hecho + alcance), incluyendo los tiempos
y secuencia. Es adicional a la prueba de intención de captura O1.

El receptor consulta su catálogo local de nodos habilitados, autentica la entrega con
la clave pública fijada para ese alcance y verifica paquete, emisor y prueba O1.
No acepta un tenant arbitrario del cuerpo como autorización. El alta del catálogo
es un fixture de prueba, sin endpoint público de enrolamiento ni conexión Clerk/GOV.

En una sola transacción SQLite conserva:

1. Hecho recibido y paquete original, sin reescribirlo.
2. Acuse firmado, con UID, digest, alcance, fecha de recepción y resultado.
3. Registro de una outbox de auditoría de laboratorio.
4. Cambio de proyección **solo** si procede; en otro caso, conserva el conflicto.

Esta outbox NO es todavía `backend/services/event_outbox.py`, no tiene worker y no
envía avisos. No se hacen llamadas a endpoints de entrada/salida de producción para
reproducir un movimiento antiguo.

El nodo verifica la firma del acuse con una clave pública del receptor previamente
fijada, comprueba UID/digest/alcance y conserva el acuse junto con la marca de recepción
en una transacción. Si se pierde una respuesta, reenvía el mismo UID; el receptor
devuelve el acuse original sin duplicar hecho, proyección ni outbox.

## Conciliación

| Situación | Resultado |
| --- | --- |
| Entrada válida sobre pendiente | Hecho recibido y proyección sintética a entrada registrada |
| Salida válida sobre entrada registrada | Hecho recibido y proyección sintética a salida registrada |
| Cancelación central, permiso revocado conocido, reloj incoherente o estado incompatible | Hecho recibido, conflicto y estado central conservado |
| Conflicto anterior del mismo escenario | Siguientes hechos conservados para revisión; no resolver por última escritura |
| Copia vencida al recibir, válida al observar | Evaluar tiempo de observación; la fecha de recepción es separada |
| Nodo deshabilitado/desconocido o firma inválida | Rechazar entrega y conservar pendiente en origen |
| Hueco de secuencia, UID colisionado o acuse no verificable | No confirmar como recibido; conservar pendiente |

Para nodo deshabilitado, la recuperación por un custodio autorizado es un flujo
pendiente: el receptor no deja que un nodo revocado invoque ese privilegio.
La firma autentica lo declarado por el dispositivo; no prueba presencia física ni
veracidad de su reloj. Un nodo comprometido con su clave podría firmar declaraciones
falsas. O2a no aporta custodia hardware ni antirrestauración del equipo.

## HTTP real en loopback

`make_receiver_server` publica exclusivamente `POST /lab/o2/events` en 127.0.0.1.
`loopback_sender` admite solo esa dirección/ruta, no redirecciones ni hosts remotos.
Hay límite de tamaño, validación de Host/Origin, errores sin cuerpos ni claves en logs.
El transporte HTTP local autentica mensajes con firmas; **no aporta cifrado TLS**.
No exponer este servicio en LAN ni internet. TLS y autenticación de transporte real
son gates posteriores, no una variable para activar en este laboratorio.

## Evidencia reproducible

```sh
python -m pip install -r labs/contingency/requirements-o1.txt
python -m unittest discover -s labs/contingency -p 'test_*.py' -v
```

63 pruebas: las 42 de O0/O1 y 21 nuevas. Usan HTTP loopback y archivos SQLite separados,
con claves efímeras nuevas en cada ensayo. Se prueban manipulación de mensajes/acuses,
firma de emisor/nodo, cruces, revocación, orden, UID repetido, cancelación, copias
históricas, reinicio del receptor, pérdida de acuse, outbox que falla y conservación
append-only. Los triggers no impiden alterar el archivo con privilegios del sistema.

CI debe confirmar el SHA publicado; localmente se usa cryptography 50.0.2 y CI instala
el pin AXS 46.0.3. La regresión Chromium sigue siendo de UI O0, no una pantalla O2a.
No hay evidencia de corte eléctrico, equipo de Salvador, PostgreSQL ni piloto real.

## Frontera O2b para AXS

- Catálogo de dispositivos, permisos, confianza y revocaciones obtenido de autoridad
  real, con habilitación residencial y separación MSP/tenant; no altas por el nodo.
- Persistencia PostgreSQL con RLS y rol limitado para hechos/acuse/outbox. Ensayos
  desechables con rol runtime real antes de cualquier cambio productivo.
- Mapear estados y reglas completas AXS, deduplicación transaccional y auditoría AUP.
  La proyección actual tiene una visita por escenario y no sustituye dichas reglas.
- Canal TLS, protección de claves, límites de ingestión y bitácora de rechazos sin PII.
- Pantalla de revisión responsable: conservar decisión como acto adicional, no editar
  el hecho offline. Avisos históricos diferenciados de avisos de llegada actuales.
- Secuencia por nodo/epoch independiente del guardia, multivisita, relevo y particiones
  de casetas. No prometer antipassback global cuando las casetas no se comunican.

Sin migraciones, flags, conexiones reales, movimientos de clientes ni despliegues.
