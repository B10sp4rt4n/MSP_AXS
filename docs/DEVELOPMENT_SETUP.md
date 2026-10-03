# Desarrollo aislado — 2 de octubre de 2026

## Recursos preparados

| Recurso | Desarrollo |
| --- | --- |
| Neon proyecto | `patient-tree-68362559` |
| Neon rama | `axs-development-20261002` / `br-blue-frog-b5o2ccsk` |
| Neon endpoint | `ep-withered-resonance-b59tusv3` |
| Railway proyecto | `AXS Development` / `c04faff4-37ba-4df4-a6ce-a4d5d5ff881b` |
| Railway servicio | `axs-development-backend` / `7a3d869b-a007-4cbd-b5e7-57fe5278f475` |
| Railway environment | `5f5b4e0c-c4ce-457c-96a4-b65ebf723354` |

Railway creó el environment con el nombre predeterminado `production` dentro del proyecto nuevo. Es un proyecto independiente: no es el servicio de producción `web` del proyecto `pleasant-encouragement`. Identificar siempre por proyecto y UUID, no sólo por el nombre del environment.

La rama Neon es una copia de producción creada el 2 de octubre a las 15:58 UTC: contiene identidades demo y auditoría heredadas. No se vaciaron tablas ni se cambiaron datos de producción. No confundir registros heredados con resultados de nuevas pruebas.

## Variables guardadas sólo en el servicio nuevo

| Variable | Valor o destino |
| --- | --- |
| `APP_ENV`, `ENV` | `development` |
| `ENVIRONMENT` | `production` para deshabilitar `/debug/db`, que expone la URL de conexión en otros modos |
| `NEON_DEV_ENDPOINT` | `ep-withered-resonance-b59tusv3` |
| `DATABASE_CORE_URL`, `DATABASE_URL` | endpoint nuevo, base `neondb`, rol `axs_core_app` |
| `DATABASE_EVENT_URL` | endpoint nuevo, base `aup_event`, rol `neondb_owner` |
| `DATABASE_GOV_URL` | endpoint nuevo, base `aup_gov`, rol `neondb_owner` |
| `SECRET_KEY` | clave independiente generada para este servicio |
| `USE_CLOUDINARY`, `ECHO_SQL` | `false` |
| `ALLOWED_ORIGINS` | `http://localhost:3000` |

No almacenar URLs con contraseñas en el repositorio. No se copiaron credenciales de Clerk, webhooks ni Cloudinary de producción.

## Activación inicial y estado actualizado

El backend ya tiene conectado el repositorio a `fix/audit-route-development-20261002` y fue desplegado. URL: `https://axs-development-backend-production.up.railway.app`. El predeploy verificó endpoints de desarrollo y CORE RLS (PASS). HTTP: `/health` 200, `/debug/db` 404, consulta de visita sin sesión 401. El predeploy es `python scripts/check_development_config.py && python scripts/check_core_rls.py`. Procedimiento para despliegues:

1. Conectar `B10sp4rt4n/MSP_AXS` a una rama que contenga estos archivos; verificar que el predeploy del servicio conserve ambas comprobaciones. La configuración de producción `railway.json` no se modificó.
2. Configurar autenticación de desarrollo y el frontend con la URL del backend nuevo; añadir su origen exacto a `ALLOWED_ORIGINS`.
3. Desplegar únicamente en el proyecto `AXS Development`. El predeploy valida endpoint/base de las cuatro URLs y después valida RLS del rol CORE. Los errores detienen el despliegue.
4. Repetir los ensayos A/B contra la URL nueva, incluyendo consultas propias 200, cruces 403, cancelaciones cruzadas sin cambios y entrega outbox → EVENT.

Los ensayos previos contra la API original pertenecen a producción. Los ensayos nuevos de development del 3-oct-2026 se documentan abajo por separado.

## Frontend de desarrollo

- Servicio Railway `axs-development-frontend`, UUID `4467b13c-61d4-4807-8e49-8c11e384278a`, en el mismo proyecto separado. Raíz `/frontend-next`; misma rama del backend.
- Dominio activo: `https://axs-development-frontend-production.up.railway.app`. Frontend desplegado; `/health` devuelve 200. Login y navegación A/B verificados por el usuario el 3-oct-2026.
- `NEXT_PUBLIC_API_URL` apunta explícitamente al backend nuevo. `ALLOWED_ORIGINS` del backend incluye este origen y localhost:3000.
- El usuario agregó claves Clerk Development en ambos servicios. La comprobación de build valida prefijos de prueba; no acredita por sí misma que ambas claves correspondan a una misma instancia ni valida credenciales contra Clerk.
- Fijados `RAILPACK_NODE_VERSION=22` y `NIXPACKS_NODE_VERSION=22` únicamente en el servicio nuevo. Fallo inicial confirmado: Node 18.20.5 incompatible con Next 16.3.6. Segundo fallo: comillas del comando inline interpretadas incorrectamente por Railpack.
- Build corregido: `node scripts/check-development.cjs && npm run build`; start `npm run start -- --hostname 0.0.0.0 --port $PORT`. Guard valida APP_ENV, destino API exacto y claves Clerk test sin imprimir valores. Cinco escenarios locales pasaron.
- Frontend desplegado correctamente con Node 22 y healthcheck `/health`. Las sesiones Clerk de A/B se resolvieron a sus identidades existentes durante las consultas autenticadas y auditoría. No se reatribuyeron roles/scopes.

## Corrección de ruta de auditoría

`ruta_segura` busca todas las coincidencias `FULL` antes de usar la primera `PARTIAL`. Así GET `/visitas/{visita_id}` deja de registrarse con la plantilla POST `/visitas/{condominio_id}`. Se preserva la sanitización: no se guardan IDs concretos ni query strings. No se reescriben hechos históricos.

Validación local: 40 pruebas de `test_security_outbox.py` y `test_development_config.py` pasaron con SQLite aislado y `TESTING=1`. Incluyen métodos GET/POST/DELETE, rechazo autenticado 403, endpoint de producción rechazado en cada variable y prohibición del fallback EVENT ausente. No se ejecutaron contra producción.


## Evidencia development — 3-oct-2026

- Sesiones Clerk manuales: 14 consultas simétricas de casas/usuarios/listas de visitas y visitas por ID, propios 200 y cruces 403. Cancelaciones cruzadas 403; ambas visitas ficticias originales siguen pendientes. 11 rechazos entregados y encontrados en EVENT, incluyendo un intento adicional realizado todavía con A.
- Automatización local: 50 pruebas pasaron en SQLite aislado, incluidas dos parametrizaciones HTTP de creación/cancelación propias, creación cruzada 403, cuerpo con otro condominio 400, cancelación cruzada 403 sin cambio y auditoría con identidad/ruta/método. Comando: `TESTING=1 python -m pytest tests/test_msp_boundary.py tests/test_destinos_visitas.py tests/test_security_outbox.py tests/test_development_config.py -q --override-ini addopts='' --tb=short`.
- API desplegada: runner `scripts/development_visit_smoke.ts` ejecutado dentro del proyecto Railway separado. Función `axs-development-visit-smoke`, servicio `d34e653f-5bab-4c9e-96fc-b90de8d0536d`, deployment `b798674b-017f-4a65-b8fb-45cdd9a43532`, resultado PASS con 20 comprobaciones en ejecución final.
- Autenticación del runner: JWT local HS256 ya admitido por el backend, expira en 5 minutos y sujeto limitado en el código a las dos identidades demo; el backend resuelve usuario y permisos reales. No reemplaza una prueba de creación mediante Clerk/UI. Secreto inyectado exclusivamente mediante referencia al backend development, nunca impreso. API y endpoint development fijos; sin URL pública, cron ni reinicios automáticos. Tras finalizar se vació AXS_TEST_SECRET sin redesplegar: un despliegue posterior requiere volver a configurar la referencia.
- Primera ejecución completó A y se detuvo al exigir vivienda en B. B sólo tiene destinos comunes; se ajustó el runner para aceptar Administración existente. La ejecución final reutilizó la visita A cancelada, sin duplicarla. La cancelación cruzada de A pendiente quedó verificada en primera ejecución; la de B pendiente en la segunda. No se alteró el catálogo para conseguir que pasara.
- Visitas nuevas: `VIS-4ced9e365c` en A (vivienda 101), `VIS-7dad7600d5` en B (Administración). Ambas quedaron canceladas por su propio administrador. Exactamente una visita por marcador A/B en CORE.
- Auditoría de ambas ejecuciones: 4 hechos de negocio (dos creaciones y dos cancelaciones) y 6 SCOPE_DENIED; cada uno entregado en un intento, last_error NULL. Reintentos de peticiones denegadas son hechos distintos. Comprobados por UID en EVENT sin duplicados.
- PR #25 sigue en draft; no se fusionó a main ni se cambió el proyecto de producción.
