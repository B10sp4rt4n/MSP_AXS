# CLAUDE.md — MSP_AXS

Contexto persistente del proyecto para trabajar con Claude Code (o cualquier
colaborador nuevo) sin depender de la memoria de una sesión o de un Codespace
específico. Si algo relevante cambia, se actualiza este archivo **antes** de
cerrar la tarea (ver regla al final).

## Qué es esto

AX-S MSP: sistema de control de acceso para condominios/fraccionamientos,
operado por un MSP (Managed Service Provider / administrador multi-condominio).
Guardias registran visitas (entrada/salida), capturan evidencia fotográfica, y
generan/validan códigos QR de preregistro. Es **multi-tenant**: un mismo MSP
administra varios condominios (tenants), y cada usuario tiene scopes de acceso
por tenant.

**Etapa actual: beta / preparación de piloto.** Hay commits recientes de
"FASE 1/2/2.5" de un piloto y un README orientado a inversionistas — trátalo
como software en validación, no como producto maduro. Hay abundante
documentación histórica en `docs/` (70+ archivos) y en la raíz (`PLAN_30_DIAS.md`,
`BACKLOG_ISSUES.md`, `ESTADO_SISTEMA.md`, etc.) escrita en distintos momentos;
este archivo es la fuente de verdad más reciente y más corta — en caso de
conflicto, confía en el código y en este archivo antes que en esos documentos.

## Stack real (verificado en código, no asumido)

- **Backend**: FastAPI (`backend/main.py`), servido con **uvicorn**
  (`Procfile`, `Makefile`). No hay Hypercorn en este repo.
- **ORM**: SQLAlchemy 2.x. **No hay Alembic** — las migraciones son scripts
  `.sql` a mano en `database/*.sql` y `scripts/migrate_*.py`, aplicados
  manualmente. Las tablas también se auto-crean vía `Base.metadata.create_all()`
  al arrancar la app (ver `backend/main.py`).
- **Frontend servido en producción**: HTML/JS estático en `backend/static/`
  (`index.html`, `admin.html`), montado por FastAPI en `/` y `/static`.
  **No hay Streamlit en este repo.** Existe además `frontend/src/*.jsx`
  (React) pero sin `package.json` ni build config — es un scaffold
  incompleto/huérfano, no lo que se despliega hoy.
- **Auth**: JWT (HS256, `python-jose`), password hashing con `bcrypt`/`passlib`.
- **DB en producción**: Postgres en **Neon** (canónico). **DB local/offline**:
  SQLite (fallback automático cuando no hay `DATABASE_*_URL` en el entorno).
  No existe una variable `USE_SQLITE`; el modo SQLite se activa simplemente
  por *ausencia* de las variables Postgres (ver sección Arquitectura AUP).
- **Multi-tenant**: `tenant_id` / `condominio_id`, con scopes por usuario
  (`UserTenantScope`) y, en Postgres, Row-Level Security vía
  `SET app.tenant_id` (`backend/core/tenant/context.py`). En SQLite no hay RLS
  real — el aislamiento depende solo de la validación de scope en código.
- **Tests**: pytest + pytest-cov, SQLite en memoria. CI en
  `.github/workflows/tests.yml` (falla si cobertura < 40%).

## Arquitectura: AUP (SESSION → SCOPE → EVENT → GOV)

El sistema se piensa como una "memoria declarada" con 4 dominios, cada uno con
su propia base de datos/engine SQLAlchemy independiente:

| Dominio | Pregunta que responde | Engine / env var | Módulo |
|---|---|---|---|
| **AUP_CORE** | ¿Quién eres y hasta dónde llegas? (identidad, condominios, visitas, scopes) | `DATABASE_CORE_URL` | `backend/db/core/` |
| **AUP_EVENT** | ¿Qué ocurrió realmente? (log inmutable, append-only) | `DATABASE_EVENT_URL` | `backend/db/event/` |
| **AUP_GOV** | ¿Por qué se permitió o negó? (políticas, autoridades, delegaciones) | `DATABASE_GOV_URL` | `backend/db/gov/` |
| **AUP_SESSION** | JWT: quién está autenticado ahora | — (stateless, `SECRET_KEY`) | `backend/core/auth/` |

Si cada `DATABASE_*_URL` no está definida, cada engine cae a su propio SQLite
local (`axs_core.db`, `axs_event.db`, `axs_gov.db`) — no a un único archivo
compartido. Axioma declarado en el código: si AUP_GOV falla, el sistema debe
denegar por defecto (deny by default).

Middleware global `AUPSessionGuard` (`backend/core/aup_runtime_blocks.py`):
bloquea cualquier request que no tenga una AUP_SESSION válida, salvo rutas
públicas explícitas (`/`, `/auth/login`, health checks).

### ⚠️ Deuda de arquitectura conocida: modelos duplicados

Existe **un modelo legacy monolítico** en `backend/db/models.py` (una sola
`Base`/engine, ligado a `DATABASE_URL` vía `backend/core/config.py`) que
convive con los modelos nuevos separados por dominio
(`backend/db/core/models.py`, `db/event/models.py`, `db/gov/models.py`).
Varios módulos "nuevos" (`core/security.py`, `core/tenant/context.py`,
`core/scope/validator.py`, `core/meta/*`, `routers/visitas_router.py`,
`routers/meta.py`) siguen importando clases (`Usuario`, `AccessLevel`, etc.)
desde el `db/models.py` legacy, no desde `db/core/models.py`, aunque las
sesiones de DB que usan (`get_db`/`get_core_db`) sí apuntan al engine
`AUP_CORE`. Funciona porque los nombres de tabla coinciden, pero son **dos
definiciones Python independientes del mismo esquema** con riesgo real de
divergencia silenciosa. También existe `backend/db/models_DEPRECATED.py`
(no usado, candidato a borrar). No lo he tocado — es un refactor no trivial,
no un fix de una línea. Cuando se aborde, documentar la decisión aquí.

## Endpoints — estado real

Prefijo `/auth` (`auth_router.py`) — **público, implementado**:
- `POST /auth/login` — crea AUP_SESSION (JWT), registra evento en AUP_EVENT.

Protegidos (requieren `Authorization: Bearer <token>`, guard global):
- `/msps` (`msp_router.py`) — GET/POST — implementado.
- `/condominios` (`condominios_router.py`) — GET/POST, `/{id}/casas` GET/POST —
  implementado, con gobierno (GOV) integrado.
- `/visitas` (`visitas_router.py`) — implementado, con deuda conocida:
  - `POST /visitas/{condominio_id}` — vigente.
  - `POST /visitas/` — **deprecated** (`deprecated=True` en el decorador),
    mantener solo por compatibilidad.
  - `GET /visitas/mis-visitas/{condominio_id}`, `GET /visitas/condominio/{condominio_id}`,
    `GET /visitas/{visita_id}` — el propio archivo los marca como
    **"PENDIENTE"/"migración desde `verificar_rol` deprecado"** en sus
    comentarios de cabecera; revisar antes de asumir que están 100% migrados
    al sistema AUP nuevo.
- `/qr` (`qr_router.py`) — `POST /qr/generar/{visita_id}`, `GET /qr/validar/{visita_id}/{token}` — implementado.
- `/qr` (`canario_router.py`, mismo prefijo, router "canario" de demostración AUP) — implementado, es un flujo de referencia/demo, no el flujo de producción de QR.
- `/evidencias` (`evidencias_router.py`) — **este es el que está montado en `main.py`**. Solo tiene `POST /evidencias/entrada/{visita_id}`, guarda archivos en filesystem local (`backend/services/evidencia_service.py`, `UPLOAD_DIR`).
- `/preregistro` (`preregistro_router.py`) — `POST /preregistro/crear`, `GET /preregistro/qr/{visita_id}` — implementado.
- `/meta` (`backend/routers/meta.py`) — API de asignaciones del "dominio meta-operativo". **Existe y está completa (340 líneas)** pero **no está montada**: el import en `backend/main.py`/`backend/routers/__init__.py` está comentado porque originalmente se buscaba un archivo `meta_router.py` que no existe (el archivo real se llama `meta.py`). Si se decide activarlo, hay que corregir el nombre del import, no solo descomentarlo.

No montado / código muerto o alternativo (no confundir con lo anterior):
- `backend/routers/evidencias_router_cloudinary.py` (412 líneas) — versión
  alternativa de evidencias que sube a Cloudinary en vez de filesystem local
  (`POST entrada/salida`, `GET visita/{id}`, thumbnails, `DELETE`). **No está
  importada en `backend/routers/__init__.py` ni en `main.py`.** El servicio
  activo (`evidencia_service.py`) sí tiene un flag `USE_CLOUDINARY` (default
  `true`) pero el router que se ejecuta hoy es el de filesystem local. Antes
  de tocar evidencias, confirmar cuál de los dos caminos es el vigente.

## Cómo levantar el proyecto en local

```bash
pip install -r requirements.txt
pre-commit install          # opcional, o: make install

cp .env.example .env        # editar valores reales
# Sin ninguna DATABASE_*_URL definida, cada dominio AUP cae a su propio
# SQLite local (axs_core.db, axs_event.db, axs_gov.db) — no se necesita
# Postgres para desarrollar.

make dev                    # uvicorn backend.main:app --reload --port 8000
# o: uvicorn backend.main:app --reload
```

- Salud: `GET /health`. Debug de conexión DB: `GET /debug/db`.
- Login de prueba (ver `ESTADO_SISTEMA.md` / seeds en `backend/scripts/`):
  usuarios de ejemplo se crean con `backend/scripts/seed_*.py` — no hay
  usuario hardcodeado en el arranque, hay que correr un seed script primero
  en una DB nueva.

Tests:
```bash
make test        # pytest tests/ -v
make coverage     # con reporte HTML en htmlcov/
```
Los tests usan SQLite en memoria (`tests/conftest.py`), no requieren Neon.

## Variables de entorno

Ver `.env.example` (regenerado a partir de un grep real de `os.getenv(...)`
en el código — no inventado). Resumen de las que importan para arrancar:

- `DATABASE_CORE_URL`, `DATABASE_EVENT_URL`, `DATABASE_GOV_URL` — Postgres/Neon
  por dominio AUP. Sin ellas, SQLite local automático.
- `DATABASE_URL` — solo la usa el `db/models.py` legacy y el endpoint de
  debug `/debug/db`; no controla los tres engines AUP de arriba.
- `SECRET_KEY` — firma JWT. **Cambiar en producción**, nunca reusar el default.
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default 480 (8h) en código, aunque
  `.env.example` histórico decía 60; el default real está en
  `backend/core/auth/jwt.py`.
- `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` — evidencias en filesystem local.
- `USE_CLOUDINARY`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`,
  `CLOUDINARY_API_SECRET`, `CLOUDINARY_UPLOAD_PRESET` — solo si se activa el
  camino Cloudinary (ver nota de evidencias arriba).

## Pendientes conocidos (no exhaustivo, ver también BACKLOG_ISSUES.md)

- `backend/services/ingest.py` **no existe en este repo** — si en alguna
  conversación anterior se hizo referencia a un stub con ese nombre, no
  corresponde a este código; no crear un archivo con ese nombre sin
  confirmar primero para qué feature es.
- Modelos duplicados (`db/models.py` legacy vs `db/core|event|gov/models.py`)
  — ver sección de arquitectura arriba.
- Endpoints de `visitas_router.py` marcados como pendientes de migración
  (ver sección Endpoints).
- Router `meta.py` completo pero no montado (nombre de archivo no coincide
  con el import esperado).
- Dos implementaciones de evidencias (filesystem vs Cloudinary), solo una
  montada.
- 15 tests fallan hoy con errores **preexistentes**, no relacionados con la
  corrección de conflictos de git del 2026-09-24: `tests/test_meta_operativo.py`
  usa un fixture `db` que nunca se definió en `conftest.py`; `tests/smoke/test_tenant_isolation.py`
  falla al crear las tablas del modelo legacy porque `backend/db/models.py`
  tiene foreign keys apuntando a tablas `usuarios_exo`/`condominios_exo`/`msps_exo`
  que no existen (parecen residuos de un rename de tablas nunca completado).
- `frontend/src/*.jsx` (React) es un scaffold sin build config; no es lo que
  se sirve en producción.
- Varios archivos generados (`.coverage`, `coverage.xml`, `axs_dev.db`,
  `database/axs.db`, `uvicorn.log`) están **trackeados en git** a pesar de
  que `.gitignore` los excluye para nuevos cambios — son ruido de commits
  pasados, no secretos, pero conviene `git rm --cached` en algún momento.
- Ver `docs/SESSION_LOG.md` para el detalle de qué se hizo en cada sesión.

## Decisiones de arquitectura

Formato: `fecha — decisión — motivo`.

- **2026-09-24** — Se corrigen marcadores de conflicto de git
  (`<<<<<<< HEAD / ======= / >>>>>>> origin/main`) que habían quedado
  commiteados sin resolver en **tres archivos**, todos por la misma merge
  ("Merge main (CI/CD) into cloudinary branch", commit `413428b`):
  `backend/main.py`, `backend/routers/visitas_router.py` y
  `backend/core/scope/validator.py` (más un cuarto, `backend/core/scope/__init__.py`,
  donde el lado HEAD estaba vacío). Ninguno parseaba — el backend no podía
  arrancar en absoluto, y `tests/test_1_session.py` ya tenía tests marcados
  como `SKIPPED` a mano con el motivo literal "routers tienen imports rotos",
  es decir: el problema ya era conocido y se había trabajado *alrededor* de
  él en vez de resolverlo.
  - `main.py`: se conservó `msp_router` (ya usado en `app.include_router`) y
    se descartó la referencia a `meta_router` (apunta a un módulo que no
    existe con ese nombre).
  - `visitas_router.py` y `scope/validator.py`: ambos conflictos enfrentaban
    la misma disyuntiva — importar `Usuario`/`AccessLevel`/`UserTenantScope`
    desde el modelo legacy `backend.db.models` o desde el modelo nuevo
    `backend.db.core`. Se verificó que ambos definen las mismas tablas con
    columnas compatibles (no es una decisión "seguro vs. rompe en runtime"),
    así que se resolvió por consistencia con `backend/core/auth/dependencies.py`
    (`get_current_user`, usado por *todos* los endpoints protegidos), que ya
    usa `backend.db.core.Usuario`. Se dejó `backend.db.core` en los tres
    archivos. Esto es más consistente que quedarse con el modelo legacy, pero
    **no resuelve** la deuda de fondo (ver sección de arquitectura arriba) —
    sigue habiendo módulos (`core/security.py`, `core/tenant/context.py` para
    `AccessLevel`, `core/meta/*`, `routers/meta.py`) que importan desde
    `backend.db.models`.
  - Motivo: bloqueaba cualquier intento de correr el proyecto o la suite de
    tests completa.
  - Verificado post-fix: `python -c "from backend.main import app"` importa
    sin errores (28 rutas registradas) y `pytest tests/` corre (84 passed,
    15 skipped, 15 errors — los 15 errores son **preexistentes y no
    relacionados** con este fix: un fixture `db` nunca definido en
    `tests/test_meta_operativo.py`, y foreign keys rotas en
    `backend/db/models.py` que apuntan a tablas `*_exo` inexistentes. No se
    tocaron — quedan como pendiente separado).
- **2026-09-24** — Se removió `.env` del tracking de git
  (`git rm --cached .env`, el archivo se queda en disco/`.gitignore`) porque
  contenía una credencial real de Neon Postgres commiteada desde
  `b3d26b3` (varios commits atrás, en `main`, con remoto en GitHub). El
  archivo sigue en el filesystem local sin cambios. **Pendiente para el
  usuario: rotar la contraseña de esa base Neon cuanto antes en el panel de
  Neon** — quitar el archivo de git no revoca una credencial ya expuesta.
- **2026-09-24** — Se crea este `CLAUDE.md`, `docs/SESSION_LOG.md`,
  `.devcontainer/devcontainer.json` y se regenera `.env.example` a partir de
  un grep real del código, para que un Codespace nuevo pueda levantar el
  proyecto sin depender de contexto perdido en una VM anterior.

<!-- Regla permanente: toda decisión de arquitectura tomada en esta o futuras
     sesiones se agrega arriba (fecha, decisión, motivo) ANTES de cerrar la
     tarea. -->
