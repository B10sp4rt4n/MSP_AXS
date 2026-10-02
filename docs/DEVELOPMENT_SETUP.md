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

## Activación pendiente

El servicio tiene start command, healthcheck y predeploy guardados directamente en Railway, pero todavía no tiene repositorio conectado, despliegue ni dominio. El predeploy es `python scripts/check_development_config.py && python scripts/check_core_rls.py`. Para activarlo:

1. Conectar `B10sp4rt4n/MSP_AXS` a una rama que contenga estos archivos; verificar que el predeploy del servicio conserve ambas comprobaciones. La configuración de producción `railway.json` no se modificó.
2. Configurar autenticación de desarrollo y el frontend con la URL del backend nuevo; añadir su origen exacto a `ALLOWED_ORIGINS`.
3. Desplegar únicamente en el proyecto `AXS Development`. El predeploy valida endpoint/base de las cuatro URLs y después valida RLS del rol CORE. Los errores detienen el despliegue.
4. Repetir los ensayos A/B contra la URL nueva, incluyendo consultas propias 200, cruces 403, cancelaciones cruzadas sin cambios y entrega outbox → EVENT.

Las comprobaciones realizadas sobre la API original pertenecen a producción. No certifican este servicio todavía sin desplegar.

## Corrección de ruta de auditoría

`ruta_segura` busca todas las coincidencias `FULL` antes de usar la primera `PARTIAL`. Así GET `/visitas/{visita_id}` deja de registrarse con la plantilla POST `/visitas/{condominio_id}`. Se preserva la sanitización: no se guardan IDs concretos ni query strings. No se reescriben hechos históricos.

Validación local: 40 pruebas de `test_security_outbox.py` y `test_development_config.py` pasaron con SQLite aislado y `TESTING=1`. Incluyen métodos GET/POST/DELETE, rechazo autenticado 403, endpoint de producción rechazado en cada variable y prohibición del fallback EVENT ausente. No se ejecutaron contra producción.
