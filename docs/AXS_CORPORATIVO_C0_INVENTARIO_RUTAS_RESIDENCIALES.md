# C0 — Inventario de frontera residencial/corporativa

**Fecha:** 2026-10-23. **Estado:** revisión estática del código de la rama C0 y pruebas sintéticas ampliadas. NO equivale a certificación de aislamiento integral ni habilita despliegues.

## Contrato de autorización

- Todo flujo **residencial** que acepte `condominio_id` debe denegar `modalidad=corporativo`, incluso para operador GLOBAL, antes de mutaciones y de fijar contexto RLS. `require_condominio` y `authorized_tenant_context` aplican `expected_mode="residencial"` por defecto; `require_visita` valida vía `require_condominio`.
- Excepción explícita: expediente ARCO utiliza `expected_mode=None` **sin** conceder acceso por modalidad; sigue exigiendo permisos, designación privada y feature flag. No cerrar ni bloquear privacidad porque se deshabilite la empresa.
- Flujos de empresa C1–C3 usan su propio guard corporativo, RLS, membresías y habilitación; no pueden reutilizar los permisos residenciales.
- Identidad personal, autenticación y webhooks Clerk operan sobre la persona/autenticación, no representan permiso implícito para actuar en una sede o condominio.

## Rutas activas inspeccionadas en `backend/main.py`

| Superficie | Control observado en código | Límite / estado |
| --- | --- | --- |
| `/condominios` (casas, personal, reglas) | `require_condominio` en operaciones por ID; GET lista y conteos excluyen empresa; alta asigna modalidad residencial por defecto | Mantener pruebas de rutas y compatibilidad residencial |
| `/visitas` (incluso POST legacy `/`) | `authorized_tenant_context` por tenant y `require_visita` por ID; POST legacy llama a `require_condominio` | Sin permisos de visitas corporativas |
| `/qr` | `require_visita` y `require_condominio` | No extender QR a corporativo |
| `/preregistro` | `require_condominio` o `require_visita` | No extender reservas residenciales |
| `/identificaciones` | `authorized` delega en `require_visita` | Conservación/captura sujetas a reglas de datos |
| `/evidencias` (router montado) | `require_visita` | Subida residencial únicamente |
| `/evidencias-salida` | Helper `authorized` de identificaciones (usa `require_visita`) | Lectura y fotos privadas sujetas a ARCO/retención |
| `/bitacora`, `/reportes` | `require_condominio` | Lectura y reportes residenciales |
| `/residentes/importar` | `require_condominio` | Solo residentes |
| `/solicitudes-acceso` | `authorized_tenant_context` | Solo gestión residencial |
| `/alexa` / consulta voz | `authorized_resident` / `require_condominio` y vivienda, de forma específica | Desvinculación debe seguir posible tras revocar permisos |
| `/msps` | GLOBAL para administración de plataforma, membresía MSP para lectura; conteo residencial filtrado por modalidad | MSP no equivale a GLOBAL y no crea membresía corporativa |
| `/condominios/{id}/proveedor/*` y `/permisos/*` | `require_platform_operator` + `lock_condo`; se incorporó bloqueo de modalidad residencial en `lock_condo` | **Cierre C0 efectuado**: antes no se verificaba modalidad |
| `/arco/{id}` | Excepción transversal `expected_mode=None` + rol, scope y designación ARCO | Preservar derechos; cumplimiento ARCO corporativo completo pendiente |
| `/auth`, `/auth/me/identity`, `/webhooks/clerk` | Identidad/autenticación individual y validación webhook, sin grant de tenant | No interpretarlos como permiso de operación corporativa |
| `/canario`, `/meta` | Salud/metadatos, sin recursos privados por tenant | Revisar al añadir nuevos datos |

## Módulo inactivo de especial atención

`backend/routers/evidencias_router_cloudinary.py` contiene rutas fotográficas con verificación por rol legacy, **sin** el guard completo de visita/tenant. La aplicación no registra este router en `backend/main.py`. Se agregó prueba contra `app.routes` que falla si se publica accidentalmente. **No habilitar ni importar** este router como alternativa sin refactorizar autorizaciones, RLS y borrado conforme ARCO.

## Evidencia agregada en C0

- `backend/services/provider_offboarding.py::lock_condo` deniega empresas corporativas con `TENANT_MODE_DENIED`, antes de `_set_postgres_tenant`; cubre inventario, procedencia, contratos, personal por contrato y baja del MSP.
- `tests/test_tenant_modalidad_c0.py` comprueba GET/POST/PUT de **las seis rutas** de gobierno residencial de proveedores, con identidad GLOBAL, respuesta 403 y conservación del MSP; también verifica ausencia del router Cloudinary legacy y bloqueo de visitas corporativas.
- `tests/smoke/test_tenant_modalidad_postgres.py` y suites existentes prueban modalidad, RLS y regresiones residenciales en PostgreSQL descartable. La nueva ampliación requiere CI del SHA correspondiente.

## Pendientes para certificar C0

1. Repetir pruebas HTTP para otras rutas activas con casos corporativo deshabilitado, corporativo habilitado, GLOBAL/MSP y scopes foráneos; la lectura estática no sustituye pruebas end-to-end por endpoint.
2. Acreditar RLS y privilegios reales en PostgreSQL para todos los caminos de lectura/escritura, incluyendo ausencia de contexto, roles sin bypass y restauración/reintentos.
3. Validar que no se filtren datos en cachés, PDFs, objetos, URLs de evidencia y notificaciones; los routers desactivados tampoco pueden publicarse por error.
4. Verificar ARCO integral, responsable, operación y retención/borrado antes de datos personales empresariales. Una empresa deshabilitada no debe perder sus derechos ARCO.
5. CI del último SHA y revisión humana de C0 antes de fusionar; C1, C2 y C3 siguen Draft, con flags corporativos apagados y sin migraciones ni despliegue productivo.

**Decisión:** no declarar C0 terminado únicamente por este inventario.

## Ampliación HTTP y corrección de avisos en cola

`tests/test_tenant_modalidad_http.py` añade una matriz de **51 combinaciones ruta/método publicadas**, con **53 escenarios** (incluye JSON, XLSX y PDF). Cada escenario prueba cuatro identidades (GLOBAL, MSP, scope local y scope ajeno), con empresa habilitada y deshabilitada: **424 denegaciones HTTP**. Se comprueba ausencia de cambios en todas las tablas CORE salvo la bandeja de seguridad, un único evento de denegación saneado y ausencia de acceso a almacenamiento o transportes. Un test adicional detecta rutas nuevas sin cobertura dentro de los doce routers residenciales inventariados. No equivale a inventariar automáticamente todo módulo futuro de la aplicación.

`tests/test_tenant_modalidad_privacy_alexa.py` usa solicitudes Alexa firmadas con una CA sintética para probar voz piloto/beta, rechazo de nuevas vinculaciones, estado no operativo y desvinculación tras revocar el scope. Comprueba también alta, consulta y avance de un expediente ARCO en ambas modalidades de habilitación, con scope y designación obligatorios. No acredita el procedimiento ARCO empresarial integral.

Se reprodujo un defecto en dos pruebas: el aviso piloto ya encolado se enviaba si el tenant cambiaba a corporativo antes del envío. `enviar_aviso_piloto` ahora consulta la modalidad en una sesión nueva antes del transporte; tenant ausente, fallo de base o bloqueo de recuperación impiden el envío. Las pruebas existentes conservan notificaciones residenciales tras movimientos confirmados; la beta también prueba la reclasificación antes del envío.

`tests/smoke/test_tenant_modalidad_http_postgres.py` replica los 424 rechazos sobre ORM real con sesiones por solicitud y RLS forzado en visitas, evidencias y outbox operativo. Comprueba ausencia de contexto, cruce entre dos empresas y conservación de datos. Acepta exclusivamente la base desechable local de CI y un rol sin SUPERUSER/BYPASSRLS. Incorporado al gate PostgreSQL; revisar resultado del último SHA antes de considerarlo aprobado.

Las pruebas locales SQLite y los firmantes/transports sintéticos no conectan con Amazon, Clerk, Neon ni Railway. Persisten los requisitos de revisión humana, políticas/grants operativos reales, recuperación entre dominios y ARCO completo antes de producción.
