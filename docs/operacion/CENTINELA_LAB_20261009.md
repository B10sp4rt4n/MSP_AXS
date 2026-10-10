# Centinela Laboratorio — relevo y baja del proveedor

Ejecutado el 9-oct-2026 sobre la rama Neon de desarrollo
`axs-development-20261002` (`br-blue-frog-b5o2ccsk`), proyecto
`patient-tree-68362559`. Se modificaron exclusivamente los registros ficticios
`lab261009_*` creados para este caso. Producción no recibió estos cambios.

## Resultado

| Actor | Inicial | Relevo | Sólo baja de membresía MSP | Baja completa del laboratorio |
|---|---|---|---|---|
| Director del proveedor | 200 | 200 | 403 | 403 |
| Guardia saliente | 200 | 403 | 403 | 403 |
| Guardia de relevo | 403 | 200 | 200 | 403 |
| Administrador del condominio | 200 | 200 | 200 | 200 |
| Residente | 200 | 200 | 200 | 200 |

Para el residente se comprueba su propia visita; para el personal, el acceso al
catálogo de viviendas. El residente no tiene permiso para listar todas las casas.

Los estados se capturaron después de cada transacción real en Neon. Las respuestas
HTTP se verificaron con FastAPI local y los estados de autorización en SQLite,
reutilizando los mismos JWT sintéticos durante toda la secuencia. No representan
solicitudes contra Railway ni sesiones Clerk reales. La conexión PostgreSQL
directa desde el ejecutor falló por DNS; las operaciones reales se hicieron con
el conector Neon.

El alta sintética inicial omitió vigencia en las tres visitas. El primer replay
detectó que el contrato HTTP la exige; se corrigió en desarrollo tomando created_at
y se aplica explícitamente esa misma corrección a cada etapa del replay. Las
capturas originales conservan el valor nulo para no reescribir la evidencia.

Durante las bajas se conservaron los estados de las tres visitas, la referencia de evidencia sintética
(sin archivo real), viviendas e identidades. El administrador del condominio
sigue leyendo las tres visitas con sus estados originales. El condominio de
control conserva su acceso y rechaza al administrador de Ensayo.

## Hallazgo y límite

Revocar la membresía MSP sólo retira esa vía de autorización del director. El
guardia de relevo todavía obtiene 200 gracias a su scope local. Por tanto, no se
debe presentar esa operación como una baja completa del proveedor.

La baja completa del laboratorio fue una operación administrativa explícita:
revocar los scopes de ambos guardias, conservar los del administrador local y el
residente, y desvincular `Residencial Ensayo` del MSP (`msp_id=NULL`). No se borró
el proveedor ni el historial. No existe todavía un endpoint de producto que
orqueste automáticamente esta baja. La decisión de conservar al administrador
local es específica de este escenario; no se infiere para otros condominios.

Los archivos `tests/fixtures/centinela_lifecycle.json` y
`tests/test_centinela_lifecycle.py` conservan el caso reproducible. No contienen
credenciales, cuentas Clerk ni datos personales reales.

```sh
python -m pytest -q --no-cov tests/test_centinela_lifecycle.py
```
