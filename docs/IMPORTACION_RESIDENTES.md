# Alta de residentes por Excel

En Usuarios del condominio: descargar plantilla, completar Residentes, validar y confirmar.

- Columnas exactas: vivienda, tipo, nombre, correo. La vivienda incluye torre/sección, por ejemplo A-001.
- Hasta 500 filas y 2 MB. Vivienda en texto para conservar ceros iniciales.
- Una vivienda y un residente principal por fila. Tipos: casa, depto, local.
- Sin teléfono en esta versión porque el modelo actual no lo conserva.
- Las viviendas faltantes se crean al confirmar. Los residentes quedan preasignados, pendientes de vinculación con Clerk. No se envían invitaciones.
- El condominio se obtiene de la selección autorizada, nunca de una columna del archivo.
- Previsualización sin escrituras. Errores bloquean el lote entero. Duplicados idénticos se omiten; diferencias requieren gestión individual.
- Confirmación revalida el archivo y compara la revisión con el plan actual. Cambios concurrentes requieren nueva validación.
- Transacción única para viviendas, residentes, permisos y auditoría. Bloqueo de condominio compartido con altas individuales y edición de residentes.
- Resultado descargable en CSV con errores por fila y protección frente a fórmulas.

## Verificación

Pruebas HTTP: permisos de administrador, rechazo entre condominios, vista previa sin altas, confirmación, repetición, duplicados, fórmulas, datos inválidos, revisión obsoleta y rollback si falla auditoría. Se ejecutan en SQLite aislado; no sustituyen una prueba concurrente PostgreSQL.

Prueba Chromium con transporte sintético: `cd frontend-next && node tests/resident-import.browser.cjs` (requiere Playwright y Chromium). Usa los componentes reales incluyendo el panel padre.

TypeScript: `cd frontend-next && npx next typegen && npx tsc --noEmit`.

La plantilla está versionada en backend/static. Su generador requiere el runtime Artifact Tool y se ejecuta desde la raíz del repositorio. No requiere dependencias nuevas en producción ni migración de esquema.
