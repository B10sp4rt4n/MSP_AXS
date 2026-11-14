# Propuesta de separación EVENT/GOV y alineación Clerk

Fecha: 14 de noviembre de 2026. PR #113 sobre la candidata integrada de PR #112.
Estado: preparado y ensayado en copia aislada; pendiente de autorización y aplicación productiva.
No se cambiaron variables, roles, migraciones, claves ni despliegues de producción durante este ensayo.

## Resultado y alcance

EVENT y GOV siguen usando `neondb_owner` en el backend productivo observado. Las migraciones propuestas crean `axs_event_app` y `axs_gov_app` sin LOGIN, sin contraseña, sin propiedad de tablas, sin membresías y sin BYPASSRLS/CREATEDB/CREATEROLE. Activan y fuerzan RLS sin modificar datos existentes.

| Dominio | Lectura del servicio | Escritura permitida |
| --- | --- | --- |
| EVENT | Eventos del `app.tenant_id` de la transacción | INSERT del mismo tenant; PLATFORM_SECURITY sólo admite denegaciones de sesión/scope |
| GOV | Autoridades, delegaciones, políticas y checkpoints del plano de control | INSERT de cuotas TENANT propias para crear sede/destino; UPDATE sólo límites, metadata, estado y vigencia de esas cuotas |

GOV conserva lectura global del plano de control por diseño. No representa aislamiento de lectura entre tenants. El backend conserva la autorización HTTP y el alcance del usuario. El contexto de tenant lo establece el servidor; estas reglas no sustituyen esa autorización ni protegen frente a un servidor comprometido capaz de cambiar su propio contexto.

EVENT no obtiene UPDATE, DELETE o TRUNCATE. GOV no puede crear autoridades, alterar delegaciones, escribir checkpoints ni cambiar políticas globales. El mantenimiento y la recuperación administrativa requieren una conexión privilegiada separada, fuera del runtime web.

## Configuración pública propuesta

La comprobación directa del 14 de noviembre confirmó un desajuste adicional: el backend tiene una publishable key `pk_live` que decodifica al dominio anterior `clerk.frontend-next-psi-ashen.vercel.app`. El frontend Production de Vercel sí tiene la clave de `clerk.auth.axs-mx.com`. Cambiar únicamente JWKS no basta.

| Variable del backend Railway | Observado | Propuesta |
| --- | --- | --- |
| CLERK_JWT_ISSUER | https://clerk.auth.axs-mx.com | Conservar |
| CLERK_PUBLISHABLE_KEY | pk_live, dominio anterior | `pk_live_Y2xlcmsuYXV0aC5heHMtbXguY29tJA` (misma clave pública del frontend Production) |
| CLERK_JWKS_URL | https://vocal-bee-4163.clerk.accounts.dev/.well-known/jwks.json | https://clerk.auth.axs-mx.com/.well-known/jwks.json |
| CLERK_JWT_PUBLIC_KEY | Presente | Conservar exactamente; no se obtuvo ni registró su contenido |
| DATABASE_EVENT_URL | Rol propietario / aup_event | Credencial nueva de axs_event_app en la misma base/host productivos |
| DATABASE_GOV_URL | Rol propietario / aup_gov | Credencial nueva de axs_gov_app en la misma base/host productivos |
| DATABASE_CORE_URL | axs_core_app | Conservar |

Las contraseñas y los DSN completos no forman parte de este documento. La publishable key es configuración pública. No se necesita cambiar CLERK_SECRET_KEY, comprar servicios ni activar capacidades corporativas para aplicar este ajuste.

La propuesta Clerk pasó el gate usando una copia en memoria del entorno, conservando la clave JWT fijada. El entorno activo falló el gate por desalineación. Esto no demuestra que el inicio de sesión actual esté roto: el verificador intenta primero la clave JWT fijada. La prueba de firma/issuer/caducidad de JWKS usa RSA sintético; queda pendiente una sesión real y la recuperación JWKS después del cambio autorizado.

## Secuencia de aplicación futura

1. Antes de la ventana, capturar configuración y SHA activos en un medio seguro, confirmar respaldo restaurable vigente y enumerar clientes/roles conectados a EVENT/GOV. Las migraciones revocan CONNECT/TEMP de PUBLIC y CREATE del esquema público: cualquier otro cliente debe tener concesiones explícitas justificadas. No aplicar sin revisar ese inventario.
2. Confirmar que la versión candidata contiene los tres ajustes de contexto EVENT: registro legado, bitácora y reportes. Conectar una versión anterior con el nuevo rol puede bloquear esas operaciones por RLS. Mantener desactivadas las banderas corporativas observadas.
3. Con operador privilegiado, ejecutar manualmente `migrations/20261114_event_runtime_permissions.sql` en aup_event y `migrations/20261114_gov_runtime_permissions.sql` en aup_gov. Son transacciones separadas y deliberadamente fallan si el rol ya existe: inspeccionar antes de reintentar. No son migraciones automáticas de arranque. El propietario actual conserva sus facultades durante esta preparación.
4. Mediante el canal seguro del operador, habilitar LOGIN y una credencial independiente para cada rol nuevo. No guardar contraseñas en Git, logs, capturas o este documento. No conceder membresías ni transferir propiedad. No reutilizar la contraseña del propietario. El ensayo dejó los roles NOLOGIN y no ejecutó este paso productivo.
5. Publicar de forma coordinada el backend con contexto EVENT, los dos DSN restringidos y las dos correcciones públicas de Clerk. Conservar la clave JWT fijada y las variables CORE. Añadir al predeploy existente: `python scripts/check_core_rls.py && python -m scripts.check_corporate_schema && python scripts/check_runtime_permissions.py`. El nuevo gate sólo lee catálogo/configuración y falla si se conecta como propietario o detecta permisos/políticas fuera del contrato.
6. Verificar los tres gates, /health, sesión real de administrador/guardia/residente, evento y reintento, bitácora, reporte y denegación entre tenants. Confirmar que autoridad/delegación no pueden alterarse desde runtime. Registrar versión y resultados antes de ampliar el piloto.

## Contención y reversión

Si falla el predeploy, no promover la instancia y conservar la versión activa. Si falla el servicio después del cambio, detener la promoción y usar el respaldo de configuración/versiones para una decisión explícita. Una versión anterior puede necesitar las conexiones anteriores: no restaurar automáticamente credenciales de propietario ni desactivar RLS. No borrar tablas, políticas o roles como remedio. Las migraciones no cambian datos y el ajuste Clerk conserva la clave JWT fijada, pero el plan debe comprobar compatibilidad de versión y credenciales en conjunto.

## Evidencia del ensayo

Ver `docs/evidence/AXS_ENSAYO_PERMISOS_20261114.json`. Copia Neon 18 `br-nameless-boat-b5g5l0fl`, restaurada del snapshot previo; 19 operaciones prohibidas rechazadas, gates EVENT/GOV aprobados, replay e aislamiento EVENT y cuota propia GOV aprobados. Las escrituras sintéticas usaron ROLLBACK. Conteos finales: 267 eventos, 1 autoridad y 6 políticas, iguales a los iniciales.

El owner necesitó concesiones SET ROLE exclusivamente para el arnés de prueba en esa copia. Se retiraron al finalizar. Neon conserva sus concesiones administrativas automáticas de cloud_admin con SET e INHERIT desactivados; no son membresías del runtime. Los roles nuevos quedaron NOLOGIN. El endpoint del ensayo quedó disabled/idle, limitado a 0.25 CU y con suspensión de 300 segundos. La copia expira el 15 de noviembre a las 13:56:19 UTC. También se deshabilitó el endpoint RW automático de la restauración anterior.

CI ejecuta pruebas con conexiones autenticadas como runtime en PostgreSQL 16; no usa una sesión administrativa con SET ROLE para verificar la imposibilidad de escalar. El ensayo Neon 18 sí usó SET LOCAL ROLE por no generar credenciales. El enlace y resultado CI del commit final se registran en el PR. No confundir ninguna de estas evidencias con una activación productiva.
