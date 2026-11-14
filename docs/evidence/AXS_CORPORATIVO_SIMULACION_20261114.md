# AXS Corporativo — simulación reproducible, 14 noviembre 2026

Se ensaya el candidato del PR #104 (`a68d1149242dd0b16cd0e363df3ccda917199423`), añadiendo una prueba integrada de recorrido. Esta evidencia es de laboratorio: JWT de prueba y SQLite en memoria con dependencias sustituidas. No acredita login Clerk, RLS PostgreSQL, conexiones segregadas reales ni regresión de producción.

## Resultado local

| Comprobación | Resultado |
| --- | --- |
| Backend: nuevo recorrido + Superadmin + directorio + conciliación + ARCO | 60 aprobadas, 0 omitidas |
| Frontend: gates de Superadmin/directorio y conciliación DOM | 13 aprobadas, 0 omitidas |
| Navegador Superadmin/directorio | Bloqueado antes de iniciar: Chromium no puede crear socket local (`Operation not permitted`) |

El nuevo recorrido crea empresas sintéticas A/B con owners distintos, configura cuotas, habilita sus directorios y crea dos sedes y un destino de A. Comprueba reintento idempotente del alta empresarial, rechazo antes de habilitar, cuotas sin filas adicionales, destinos separados por sede, GET/POST cruzados A↔B denegados, GLOBAL sin membresía denegado en directorio, host limitado a su sede y revocación con el mismo JWT. No se crean casas y B conserva cero destinos.

Las suites existentes inyectan fallos antes/después de commits CORE/GOV, comprueban recuperación por request_id, revisión obsoleta, deriva de políticas y designación/revocación ARCO. Los 13 casos frontend usan backend simulado y DOM: no equivalen a navegador conectado a API real. Las pruebas browser se remiten a CI y su resultado debe consultarse en el SHA exacto de este PR; no se presupone aprobado.

## Repetición

Con Python 3.12 y dependencias del proyecto instaladas, desde la raíz:

```sh
TESTING=1 DATABASE_URL=sqlite:///./axs_dev.db DATABASE_CORE_URL=sqlite:///./axs_core.db DATABASE_GOV_URL=sqlite:///./axs_gov.db DATABASE_EVENT_URL=sqlite:///./axs_event.db python -m pytest tests/test_corporate_simulated_journey.py tests/test_corporate_superadmin.py tests/test_corporativo_directorio.py tests/test_corporate_reconciliation.py tests/test_corporate_arco.py -o addopts='' -q
```

Desde `frontend-next`, ejecutar `npm ci`, instalar sin guardar `jsdom@26.1.0` y `playwright@1.58.2`, y ejecutar:

```sh
node --test tests/corporate-superadmin-gate.test.cjs tests/corporate-directory-gate.test.cjs tests/corporate-reconciliation-dom.test.cjs
node tests/corporate-superadmin.browser.cjs
node tests/corporate-directory.browser.cjs
```

La ejecución local usó un entorno virtual nuevo con dependencias de aplicación seleccionadas, no el requirements completo. El lock frontend se instaló con npm ci; las herramientas de ensayo se añadieron sin modificarlo. CI debe verificar el conjunto con el entorno canónico del repositorio.

## Alcance pendiente

- Completar navegador en un entorno que permita Chromium.
- Regresión HTTP autenticada del despliegue real, aislamiento PostgreSQL/RLS y login Clerk.
- Revisar y autorizar por separado la entrega frontend y la activación de una empresa piloto.

Esta entrega sólo añade pruebas y evidencia; no fusiona #104 ni cambia flags, grants, migraciones o despliegues de producción. La operación offline del PR #107 conserva su propio alcance pendiente.
