# Activación del sandbox corporativo — 27 de octubre de 2026

Salvador autorizó «vamos a activarlo». Proyecto Railway cf44e5f4-1a41-4d25-a13e-a39211cda7b6, entorno sandbox cd1b2ff7-509e-4c6b-9ea0-c537295d4cd3.

## Servicios publicados y resultado observado
| Servicio | ID | Deployment | Estado |
| --- | --- | --- | --- |
| API | e395d483-dd09-4f50-a1e8-415787be5b30 | 805e44a7-d836-47ce-9f08-3a36c624fbfa | SUCCESS |
| Frontend | 94571cbd-cf97-4487-95ea-0c84054e6428 | 42aed218-eac5-4fd0-b937-e0d9a72e7e8a | SUCCESS |

- API: https://axs-corporativo-api-sandbox-sandbox.up.railway.app
- Acceso verificado: https://axs-corporativo-web-sandbox-sandbox.up.railway.app/sign-in
- Consola tras autenticación: /dashboard/corporativo-superadmin.

El frontend se hospedó como servicio separado en el mismo proyecto Railway. Vercel frontend-next conserva su configuración productiva; no tenía variables preview de Clerk. La clave de desarrollo se comparte mediante referencia de variable interna de Railway, sin copiar su valor al chat, Git o frontend público.

## Configuración aplicada
- API: fase runtime, flags corporativo/provisioning/casos ARCO activos solo en sandbox. Alexa/fotos/retención desactivados. Predeploy usa python -m scripts.check_corporate_sandbox_config y python -m scripts.check_corporate_sandbox_data.
- CORS restringido al único origen del frontend sandbox.
- Frontend: rootDirectory frontend-next, npm run build, arranque Next.js en puerto 3000, healthcheck /privacidad.
- API explícita NEXT_PUBLIC_API_URL apunta al dominio sandbox; publishable key de prueba; fallback de login a consola corporativa.
- Node 22 fijado mediante NIXPACKS_NODE_VERSION. El primer build falló por Node 18; el build final aprobó.
- La configuración efectiva reside en Railway. El archivo de configuración alternativo propuesto durante el diagnóstico no fue aceptado como selector de configuración por la plataforma (opción deprecada), por lo que se retira de esta rama. No se presenta como configuración aplicada.

## Pruebas reales
- Railway observó ambos deployments en estado terminal SUCCESS.
- API GET /health: 200, status healthy.
- API GET /ready: 200, ready true.
- OPTIONS de acceso corporativo desde origen permitido: 200 y Access-Control-Allow-Origin exacto.
- OPTIONS desde otro origen: 400, sin permiso CORS.
- GET /plataforma/corporativo/acceso sin sesión: 401.
- Frontend /privacidad: 200; /sign-in: 200.
- Acceso sin sesión a /dashboard/corporativo-superadmin redirige a /sign-in.
- Navegador: visible «Sign in to MSP-AXS», campos Email address/Password, botón Continue y «Development mode»; Clerk cargó vocal-bee-4163.clerk.accounts.dev. No se ingresaron credenciales, enviaron correos ni crearon cuentas.

## SHAs y límites
La metadata real de Railway reportó API sobre 3e10e1f597a7d4201c68b3dc7739205ab0c44094 y frontend sobre f671cf269e05bc854bc28c44e820fd4d230f8a8e. Se conservó ese dato aunque la configuración de source mostraba inicialmente el pin ba70873. Las diferencias de esos SHAs respecto al código previamente probado son evidencia operativa y el archivo alternativo retirado; no cambios funcionales de backend/frontend.

No se acredita todavía sesión Clerk autenticada, alta de empresa o recorrido completo de permisos desde navegador. El usuario de ensayo de plataforma es el previamente seleccionado por Salvador; la segunda identidad sigue disponible para asignarla como owner.

La constancia de arranque vence el 28 de octubre a las 11:54 CDMX; eso limita nuevos arranques y no detiene automáticamente procesos ya iniciados. No eliminar certificados ni datos para forzar renovación.

Producción, main, San Luis, las bases heredadas y el proyecto frontend productivo de Vercel no se modificaron.
