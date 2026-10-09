# Simulación de visitas sin esperas

La suite `tests/test_simulacion_reloj.py` ejecuta las rutas reales de FastAPI con CORE, EVENT y GOV aislados en SQLite en memoria. El reloj se sustituye solamente dentro de cada prueba y se restaura al terminar. No añade parámetros, endpoints ni controles de reloj a producción. Las sesiones JWT conservan su reloj real: se simula el tiempo de negocio, no la expiración de autenticación.

Ejecutar desde la raíz, con las dependencias del proyecto instaladas:

```bash
TESTING=1 python -m pytest --no-cov -q tests/test_simulacion_reloj.py tests/test_acceso_atomico.py tests/test_reglas_acceso.py
```

## Escenarios nuevos

- Visita personal, entrega y proveedor: preregistro del residente, autorización, rechazo temprano, entrada, bloqueo de reutilización, salida cuatro horas después, rechazo de salida duplicada y bloqueo posterior del QR.
- Comprobación de las horas persistidas y evento de salida único con identidad del guardia.
- Una visita programada una hora después acepta acceso desde 30 minutos antes (inclusive) hasta 60 minutos después (exclusive).
- Límites: un segundo antes del inicio, inicio exacto, un segundo antes del final, final exacto y un segundo después.
- Guardia B no puede acceder a una visita A, tampoco indicando explícitamente el condominio A.
- Cancelación del residente impide el ingreso y conserva la visita sin entrada.

## Resultado local, 9 octubre 2026 UTC

27 pruebas aprobadas, 1 omitida, 2.17 segundos; 9 son escenarios nuevos con reloj controlado. La omitida requiere PostgreSQL para comprobar bloqueos concurrentes. No se verificó cámara, interfaz móvil, Clerk externo ni producción en esta ejecución.

La caducidad comprobada es el rechazo del acceso al vencer el horario; no demuestra una tarea automática que cambie el estado persistido a «expirada». La evidencia de auditoría se comprueba en EventOutbox; no se afirma entrega al almacén EVENT en estos escenarios.
