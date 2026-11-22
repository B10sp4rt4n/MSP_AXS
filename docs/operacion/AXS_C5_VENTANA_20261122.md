# Siguiente ventana C5 — 22 de noviembre de 2026

Autorización explícita para continuar el ensayo sintético existente: `103619f5-27ef-469e-91d0-58b9af1c3395`.
Aprobación registrada: `2026-11-22T23:54:01.338367+00:00`; inicio: `2026-11-22T23:54:01.338367+00:00`; fin: `2026-11-29T23:54:01.338367+00:00`. Duración máxima: siete días desde la aprobación registrada.

La aprobación del operador está vinculada a la conversación del 22 de noviembre, donde se acepta completar la validación pendiente, preparar la siguiente ventana y continuar el ensayo. Se conserva el mismo run e instancia Clerk Development. El manifiesto anterior y las tres constancias iniciales se preservan sin modificar sus fechas o hashes.

Antes de preparar esta autorización, la lectura de CORE/GOV/EVENT conservó los microsegundos PostgreSQL y el cálculo actual de las nueve consultas de catálogo coincidió con las tres huellas originales. La autorización no modifica catálogo, permisos SQL, RLS, datos o certificados.

Para activarla, seleccionar únicamente este UUID mediante `AXS_CORPORATE_SANDBOX_AUTHORIZATION_ID` en el API dedicado del sandbox y desplegar el commit que contiene el archivo. Las cuatro conexiones CORE/GOV/EVENT/PROVISIONER siguen sujetas al control de arranque existente. Se debe comprobar el estado terminal y el mensaje de vigencia del proceso; el healthcheck por sí solo no acredita la ventana.

La selección anterior es `4436d9a7-bb98-49a4-8dc8-fc38a9b59165`. No se modifica automáticamente ni se renueva por tráfico. Cada petición debe seguir bloqueándose después del vencimiento verificado por el middleware existente.

Alcance: pruebas sintéticas en el ambiente corporativo C5. No autoriza producción, datos de clientes, nuevas credenciales, ampliación de roles ni cambios de retención. El estado de despliegue se documenta por separado en la evidencia de operación.
