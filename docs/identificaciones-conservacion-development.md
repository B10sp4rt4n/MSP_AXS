# Conservación de identificaciones: piloto Development

Estado: implementación restringida a imágenes ficticias; purga general de documentos reales desactivada.

## Qué se implementó

- Registro durable por par en `identity_retention`, con versión de política, vencimiento, excepción, operación y reclamo exclusivo.
- Treinta días desde la salida consistente; si no hay salida, desde la captura. La salida actualiza el plazo en su misma transacción, sólo si la identificación aún no venció.
- Bloqueo exacto de consulta por vencimiento, incluso si el trabajador está detenido. La lectura se revalida después de descargar del proveedor. El listado vencido omite fotos y nombre transcrito.
- Excepción administrativa con responsable, incidencia, motivo y fecha límite con zona horaria. Creación, cambio y liberación auditados. Rechazo si el borrado ya comenzó.
- Intención y outbox transaccionales, reclamos con `FOR UPDATE SKIP LOCKED`, token y lease de 15 minutos. El I/O remoto se realiza fuera de las transacciones largas.
- Confirmación de ausencia de ambos objetos antes de finalizar. Errores 304/429/500/503 del proveedor no cuentan como ausencia. Reintentos a 1, 5, 15, 60 minutos y luego cada seis horas.
- Finalización atómica con referencias y nombre transcrito retirados y evento de bitácora único. Un fallo parcial mantiene el acceso bloqueado y conserva referencias restringidas para completar.
- Pantalla con vencimiento y estado, gestión de excepciones para administradores del piloto y retirada de imágenes locales al vencer o recibir 410. TypeScript y lint comprobados; no se realizó una segunda sesión Clerk para los actores sintéticos.
- Reporte de simulación considera las excepciones de pares inscritos y excluye pares eliminados. Conserva el límite explícito de 10,000 fotos; no hay paginación general todavía.

## Límites de activación

La inscripción y el trabajador requieren simultáneamente:

1. `APP_ENV=development`.
2. Endpoint `ep-withered-resonance-b59tusv3`.
3. `AXS_ID_RETENTION_SCHEMA_ENABLED=true`.
4. `AXS_ID_RETENTION_PILOT_ENABLED=true`.
5. Condominio ficticio `axs_demo_condo_a` o `axs_demo_condo_b`.
6. Visita con prefijo exacto `AXS RETENTION development 20261012 `.
7. Dos fotos con etiqueta ficticia y hash normalizado conocido.

El trabajador vuelve a comprobar visita, tenant, captura, lados, referencias canónicas, hashes y bytes antes de borrar. No existe endpoint para mover el reloj o inscribir documentos reales. La modificación de fechas del ensayo se conserva como SQL con guardas para exactamente sus dos pares/cuatro IDs de evidencia.

Al cerrar el ensayo, dejar `AXS_ID_RETENTION_PILOT_ENABLED=false`. Mantener el switch de esquema/lectura habilitado en Development: apagar el trabajador no restaura acceso. El piloto de borrado anterior sigue también desactivado (`AXS_ID_PHOTOS_TEST_PURGE_ENABLED=false`).

No quitar las restricciones para activar producción. Falta una versión general con aceptación de política por condominio, migración de registros existentes, conciliación de pares incompletos, paginación y seguimiento operativo de errores. El límite máximo de excepciones sigue pendiente del responsable.

## API del piloto

Todas las rutas requieren sesión y alcance; las de gestión requieren ADMIN_CONDOMINIO o MSP_ADMIN:

- `GET /identificaciones/{visita_id}?condominio_id=...`: conserva contrato previo y añade estado de conservación cuando el par está inscrito.
- `GET /identificaciones/{visita_id}/{evidencia_id}?condominio_id=...`: 410 si vencida, pendiente, para revisión o eliminada.
- `PUT /identificaciones/{visita_id}/conservacion/excepcion?condominio_id=...`: cuerpo `hasta` (ISO con zona), `responsable`, `incidencia`, `motivo`.
- `DELETE /identificaciones/{visita_id}/conservacion/excepcion?condominio_id=...`: libera la excepción; no restaura ni recrea fotos.
- `POST /identificaciones/{visita_id}/conservacion/ciclo-prueba?condominio_id=...`: procesa sólo ese par elegible por la misma ruta del trabajador. No cambia fechas y no permite saltar vencimiento o excepción. Deshabilitada al cerrar el piloto.

La respuesta no contiene rutas de almacenamiento ni secretos. Fechas almacenadas en UTC y mostradas en hora de Ciudad de México.

## Ensayo y repetición

`scripts/development_retention_postgres.ts` verifica RLS con un rol sin bypass y dos conexiones concurrentes en la rama hija `br-small-poetry-b5fnlc9t`. El fixture de reclamo queda persistido; para repetir se debe preparar un fixture nuevo o restablecer explícitamente sólo ese fixture en esa rama aislada. Su credencial temporal se retiró del operador tras el ensayo.

`scripts/development_retention_smoke.ts` tiene fases `setup`, `verify` y `closed`. El operador es la función de prueba existente, sin dominio público, cron ni reinicio automático. Usa las identidades locales existentes de prueba; no equivale a una segunda sesión Clerk.

El reloj ficticio se adelanta exclusivamente mediante `scripts/development_retention_fixture_clock.sql`, con guardas de visita, UUID de captura, evidencia y hash. No ejecutarlo sobre producción ni generalizarlo.

Validación local: 105 pruebas combinadas, incluidas 27 nuevas de conservación, con `python -m pytest -o addopts='' tests/test_identificacion_conservacion.py tests/test_identificaciones.py tests/test_identificacion_retencion.py tests/test_identificacion_borrado_prueba.py tests/test_reportes_operacion.py tests/test_destinos_visitas.py -q`. La opción evita el plugin de cobertura ausente en el entorno local; no omite los tests.

La evidencia del ensayo desplegado se conserva en `docs/evidence/identificaciones-conservacion-development-20261012.json`. Confirma ausencia en almacenamiento activo, no destrucción de respaldos o versiones del proveedor.
