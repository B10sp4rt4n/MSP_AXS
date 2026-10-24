# AXS Corporativo — cierre de conexiones del sandbox (NO productivo)

**Estado actual:** ver [preparación comprobada el 24 de octubre de 2026](AXS_CORPORATIVO_SANDBOX_PREPARACION_20261024.md).
Las secciones siguientes conservan la secuencia histórica; los estados previos
de bases sin tablas o incompletas fueron superados. El entorno sigue sin API
operativa y sin permisos de aplicación; no aplicar instrucciones antiguas como
si fueran el estado vigente.

**Fecha:** 2026-10-23. **Estado:** servicio Railway *staged*, SIN despliegue, sin dominios públicos, sin URL con contraseña.

## Topología aprobada para ensayo futuro

- Railway proyecto separado `AXS Corporativo Sandbox`, servicio `axs-corporativo-api-sandbox`, entorno `sandbox`; no reutilizar el entorno compartido `AXS Development` ni el servicio público residencial.
- Neon proyecto `MSP_AXS`, rama única `axs-corporativo-c0-c2-ensayo-20261023` (ID `br-soft-leaf-b59xcclw`), endpoint `ep-bitter-snow-b5sgxc4h`. Es copia del desarrollo, **con datos heredados que aún no fueron anonimizados**.
- CORE: base `neondb`; solo rol de runtime limitado `axs_core_app` y nunca `neondb_owner`.
- GOV: base `aup_gov`; rol propio `axs_corp_sandbox_gov`, permisos para leer autoridades y leer/escribir políticas, NO administrar autoridades o delegaciones.
- EVENT: base `aup_event`; rol propio `axs_corp_sandbox_event`, permisos de lectura/inserción y USAGE sobre secuencia, sin UPDATE/DELETE ni DDL.
- Aprovisionamiento: cuenta `axs_corporate_provisioner` de C2 sigue `NOLOGIN`; no poner en Railway credenciales de provisioner ni activar flags hasta autorizar ensayo de accesos.

## Incidente de privilegios detectado y resuelto

El mecanismo API de Neon de alta de roles concedió **membresía `neon_superuser`** de forma inesperada a dos roles nuevos. El propietario disponible no pudo ejecutar `REVOKE`; ambos roles se eliminaron inmediatamente y se verificó su desaparición. Los reemplazos se crearon mediante `CREATE ROLE NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`, sin membresías.

Verificación: los roles GOV y EVENT carecen de SELECT sobre CORE (`usuarios`, `visitas` y `corporate_memberships`). Son incapaces de ingresar porque **NOLOGIN**. Los grants sí están listos en su rama de prueba. No se generaron ni transportaron contraseñas.

## Bloqueo previo al despliegue

El script `scripts/check_corporate_sandbox_config.py` comprueba SIN abrir conexión ni imprimir secretos:
- `APP_ENV=development`, `ENV=development`, `ENVIRONMENT=production` (inhabilita la ruta legacy `/debug/db`) y `AXS_CORPORATE_SANDBOX_ONLY=true`;
- hostname exclusivo de `ep-bitter-snow-b5sgxc4h`, bases correctas y nombres exactos de roles CORE/GOV/EVENT; SSL exigido y `DATABASE_URL = DATABASE_CORE_URL`;
- secreto independiente de sesión (mínimo 32 caracteres) y claves de **Clerk de prueba** (`sk_test_` y `pk_test_`);
- `AXS_CORPORATE_API_ENABLED=false`, `AXS_CORPORATE_PROVISIONING_ENABLED=false`; Alexa, fotos, Cloudinary, casos ARCO e SQL echo deshabilitados;
- ausencia de `DATABASE_CORPORATE_PROVISIONING_URL` hasta contar con procedimiento separado.

El predeploy staged de Railway ejecuta primero ese script y luego `scripts/check_core_rls.py`. **Como las variables de conexión, Clerk y sesión aún no se han inyectado, un deploy accidental debe fallar cerrado.** Esto es deliberado. El script no sustituye una prueba HTTP ni garantiza que una clave pertenezca a la instancia Clerk esperada.

## Criterio de habilitación y cierre

1. Revisar costo/conformidad antes de activar computación Railway: el servicio todavía no está desplegado.
2. Preparar datos de ensayo sin PII heredada, cuentas de base LOGIN con privilegios mínimos y secretos nuevos mediante mecanismo seguro; nunca reutilizar credenciales de producción ni conceder `neon_superuser`.
3. Configurar URLs exclusivamente de la rama de ensayo, verificar login real contra cada base y `check_core_rls.py`; GOV/EVENT no deben ser dueños de tablas.
4. Usar solo Clerk de desarrollo, comprobar el emisor y los usuarios sintéticos antes de habilitar endpoints.
5. Activar exclusivamente en servicio sandbox bajo aceptación expresa y evidencia; no en AXS Residencial. Probar alta, idempotencia, owner, cuotas, RLS, auditoría y ARCO antes de datos personales reales.
6. Mantener los PR #96 → #97 → #98 → #100 como dependencias de revisión, sin merge automático.

No se ha ejecutado `accept-deploy`, no se ha cambiado ningún servicio residencial y no se ha configurado `DATABASE_CORPORATE_PROVISIONING_URL`.


## Auditoría de datos heredados y bases nuevas — 23 de octubre de 2026

- Comprobación read-only de la rama de ensayo `br-soft-leaf-b59xcclw`: CORE contiene **38 usuarios, 43 visitas, 37 viviendas y 22 evidencias** procedentes de la rama copiada de desarrollo. El recuento no accedió a los contenidos. Esto **bloquea la apertura de una API de ensayo pública**, aunque no sea producción.
- Se creó `scripts/check_corporate_sandbox_data.py` como gate de arranque: consulta únicamente existencia de filas en tablas CORE, GOV y EVENT, exige rol y base correctos, sin imprimir PII. Falla si hay datos heredados, tablas faltantes o credenciales demasiado privilegiadas. Pruebas sintéticas `tests/test_corporate_sandbox_data.py`.
- La configuración de Railway **todavía NO invoca este segundo gate**: la actualización staged fue rechazada por controles de seguridad. No hacer `accept-deploy` mientras no se verifique su aplicación.
- Alternativa no destructiva iniciada en la misma rama Neon: se crearon bases **vacías** `axs_corp_core_sbx` y `axs_corp_event_sbx`, sin datos ni credenciales. La creación de `axs_corp_gov_sbx` fue rechazada por el conector, por lo que el conjunto no está completo. No se borraron ni editaron las bases heredadas.
- El intento de actualizar los nombres de destino de la configuración GitHub también fue parcialmente rechazado. Se **revirtió** el cambio de destino para mantener coherencia con sus pruebas; el código aún apunta a las bases copiadas, que deben seguir bloqueadas. No se anunció un resultado que no se haya validado.
- No se cambiaron los roles NOLOGIN GOV/EVENT ni la cuenta de aprovisionamiento. No hay servicio Railway ejecutándose, ni entorno corporativo habilitado, ni rutas públicas nuevas. Las bases vacías recién creadas requieren estructura/RLS, grants limitados y pruebas antes de poder usarse.

**Bloqueantes siguientes:** completar GOV vacío mediante una operación autorizada, inicializar y asegurar los esquemas vacíos; después migrar el pin de bases y probar su gate; solo entonces preparar credenciales sintéticas de inicio de sesión y pedir autorización de costo para desplegar Railway. No utilizar `DELETE/TRUNCATE` en las bases clonadas ni exponer los 38 usuarios heredados.


## Cierre del catálogo de bases vacías — 23-oct-2026

- Neon rama `br-soft-leaf-b59xcclw`: tres bases limpias `axs_corp_core_sbx`, `axs_corp_gov_sbx`, `axs_corp_event_sbx`. Consultas read-only confirmaron **0 tablas de aplicación en cada base**. La creación de GOV se completó en el segundo intento.
- Las bases clonadas originales `neondb`, `aup_gov`, `aup_event` y su contenido heredado **permanecen intactas**. El catálogo corporativo de ensayo usa nombres diferentes en el validador GitHub (config y gate de datos), con pruebas actualizadas.
- Se incorporó `scripts/bootstrap_corporate_sandbox_schemas.py`: bootstrap **manual**, doble confirmación, URL PostgreSQL exclusiva del endpoint y tres nombres de base concretos; rol `neondb_owner` utilizado solo para crear el esquema, exige cero tablas antes y justo antes de cada fase. Usa los modelos ORM actuales, fuerza RLS y no asigna grants a roles de aplicación. No es invocado por el arranque de Railway.
- Se añadieron `tests/test_corporate_schema_bootstrap.py` y `tests/smoke/test_corporate_schemas_fresh_postgres.py`: validación offline de destinos/autorización y construcción de los tres esquemas con RLS en PostgreSQL efímero de CI. **No equivale a inicialización real de Neon**.
- Importante: las tres bases Neon nuevas **todavía no tienen esquema de aplicación**. Las cuentas GOV/EVENT permanecen `NOLOGIN`, sin contraseñas en Railway. No activar un deploy, aunque las comprobaciones de configuración estén listas.
- El servicio Railway sigue preparado (staged) y el intento anterior de añadir el gate de datos a su predeploy fue bloqueado. Debe verificarse el comando staged antes de ejecutar cualquier deploy. No reutilizar claves de producción.

**Secuencia pendiente:** CI verde del bootstrap → aplicar esquema *con credencial de propietario únicamente en las tres bases vacías* → políticas/grants por dominio revisados → verificación con credenciales nuevas de prueba → revisar costos y autorización explícita para desplegar. No abrir API hasta completar privacidad y datos sintéticos.


## Refuerzo previo a importación del backend

- `backend/main.py` ejecuta `check_corporate_sandbox_data.check_data(os.environ)` **antes de importar motores CORE/GOV/EVENT** cuando `AXS_CORPORATE_SANDBOX_ONLY=true`. El guard se ejecuta también si se omite el predeploy de Railway. En modo residencial la ruta de inicialización existente no cambia.
- El gate de Railway (sin aplicar) ahora contiene tres etapas: `check_corporate_sandbox_config.py` → `check_corporate_sandbox_data.py` → `check_core_rls.py`. No se autoriza despliegue hasta obtener credenciales y permisos válidos.
- Las tres bases `axs_corp_core_sbx`, `axs_corp_gov_sbx` y `axs_corp_event_sbx` fueron consultadas y tenían **cero tablas de aplicación**; su esquema no se ha instalado en Neon.
- El bootstrap **solo manual** `scripts/bootstrap_corporate_sandbox_schemas.py` crea las tablas reales con RLS forzado, tras doble confirmación y preflight de tres bases vacías. No concede privilegios de runtime, ni incluye migración automática en despliegue.
- La primera prueba del bootstrap contra PostgreSQL efímero de CI resultó en **91 pruebas PG aprobadas** (run `40007292828`). No trasladar esos resultados a una afirmación de Neon listo para servicio.
