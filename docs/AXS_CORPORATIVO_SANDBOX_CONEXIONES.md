# AXS Corporativo — cierre de conexiones del sandbox (NO productivo)

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
