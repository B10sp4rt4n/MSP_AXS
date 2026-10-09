# Cierre operativo sin pruebas visuales

Rama independiente de PR #30; parte de main con la simulación de reloj (#29).

## Consulta nueva

GET /visitas/resumen-turno/{condominio_id}?inicio=<ISO con zona>&fin=<ISO con zona>

Requiere scope GUARDIA o superior; tenant explícito y RLS. Intervalo [inicio, fin), máximo 31 días y sin fin futuro. Las respuestas usan UTC explícito. No requiere migración ni modifica datos.

- Turno: dentro al inicio, entradas, salidas, dentro al cierre, reconciliación, cancelaciones/rechazos registrados y eventos pendientes de entrega.
- Actual: personas con entrada sin salida y permisos pendientes clasificados por vigencia temporal.
- Alertas: IDs con salida sin entrada o salida anterior a la entrada.

El resumen actual y el turno son medidas diferentes; una entrada exactamente en fin pertenece al siguiente turno. Personas que entraron antes de inicio forman el saldo inicial.

## Vencimientos

Proyección de lectura: por_iniciar, vigente, vencido, sin_vigencia y sin_permiso_temporal. Conserva el estado original y el historial. Vigencia temporal no equivale a autorización: las reglas de entrada y el scope siguen siendo obligatorios. Un visitante que ya entró aparece como utilizado, no vencido; la salida permanece disponible.

## Recuperación

La prueba de turno deja EVENT indisponible, comprueba que la operación y cifras CORE permanecen, avanza cinco minutos virtuales y entrega todos los eventos pendientes una sola vez. Comprueba IDs concretos del outbox para separarlos de eventos de evaluación GOV. Las pruebas existentes de PostgreSQL también cubren caída TCP y muerte de proceso antes del ACK.

## Accesos simultáneos

Nueva prueba en test_reglas_acceso.py (incluida en el gate PostgreSQL existente): dos sesiones y una barrera de inicio compiten por el mismo QR. Esperado: un 200, un 400, una entrada persistida, un evento de éxito y un rechazo con identidades distintas. Se usa servicio de entrada y conservación de rechazo reales; no simula dos cámaras ni dos sesiones Clerk.

## Límites

Rechazos y cancelaciones se cuentan desde CORE EventOutbox retenido, sin depender de EVENT. Son intentos registrados, no personas únicas. Los intentos fuera de scope se auditan en seguridad global y se excluyen del resumen del condominio. No inferir rechazos históricos anteriores a la adopción del outbox. La consulta recorre el historial del tenant para contemplar personas que permanecen dentro desde turnos anteriores; no se ha medido carga de gran volumen. No incorpora pantalla nueva.
