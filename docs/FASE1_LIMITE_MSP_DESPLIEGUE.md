# Fase 1: límite de proveedor y condominio

Estado: implementación en PR borrador; ensayos SQL en rama Neon aislada. No desplegar todavía.

## Contrato de autoridad

| Actor | Fuente efectiva | Alcance |
| --- | --- | --- |
| Operador AX-S | `authorities_gov` GLOBAL y ACTIVO | Todos los MSP y condominios; crea MSP y asigna administradores |
| Administrador MSP | `usuarios.rol = MSP_ADMIN` y `msp_memberships` activo | Solo los condominios del MSP asignado; crea condominios dentro de ese MSP |
| Administrador, guardia o residente | `user_tenant_scope` ACTIVO con nivel suficiente | Solo el condominio indicado; residente limitado a su vivienda en visitas y QR |

La pertenencia no se infiere de `usuarios.msp_id`, `usuarios.rol` ni de un JWT. Revocar la fila de membresía elimina el alcance en la siguiente consulta. `PUT /msps/{msp_id}/admins/{usuario_id}` y `DELETE` sobre esa misma ruta solo aceptan operador GLOBAL. La autoridad GLOBAL se administra en AUP_GOV, fuera de estas rutas.

## Preparación de despliegue

1. Identificar las bases reales detrás de `DATABASE_CORE_URL`, `DATABASE_GOV_URL` y `DATABASE_EVENT_URL`, sin copiar secretos. Comparar esquema y datos con ORM y `migration_06_msp_memberships.sql`. El arranque actual llama `create_all`; eso no sustituye una migración controlada.
2. Verificar qué identidad tendrá autoridad GLOBAL activa en GOV. Revisar cada par inicial usuario/MSP con el proveedor y cargar únicamente pares aprobados en CORE. No hay migración automática del campo legado `msp_id`.
3. Revisar índices, claves foráneas, respaldo y plan de reversión. Las migraciones 06 (CORE) y 07 (EVENT) se aplicaron sin errores en la rama aislada de Neon; falta probar asignación/revocación y el recorrido de la aplicación, y acordar los pares iniciales de membresía.
4. Verificar en PostgreSQL las políticas RLS y las rutas que crean o modifican visitas. `set_config(..., true)` dura la transacción: los servicios hacen `commit()` y `refresh()`. La sesión ahora restablece el tenant y las rutas por `visita_id` validan el condominio antes de buscar la fila. CI con PostgreSQL desechable y rol sin bypass ya validó el servicio tras `commit()`/`refresh()`; la prueba HTTP en SQLite cubre selección y rechazo del condominio. Falta el recorrido HTTP sobre PostgreSQL y el rol real de despliegue antes de activar RLS.
5. Validar gobierno de `crear_tenant` y límites por proveedor. La política actual es global y cuenta todos los condominios; un cupo contractual por MSP requiere un diseño separado. Comprobar también registro EVENT de las altas y revocaciones de membresía antes de habilitar operación real.
6. Solo después de estas verificaciones, desplegar de forma escalonada y repetir los casos de acceso cruzado en staging y producción controlada. Si falta la tabla o la autoridad, las nuevas rutas deniegan acceso.

## Pruebas recuperadas y EVENT

Las pruebas de sesión, planes y verificación de eventos ya se ejecutan en SQLite. El verificador de EVENT ahora conserva `event_uid` y `session_hash` para eventos nuevos. Antes de desplegar el código, aplicar `database/migration_07_event_integrity_inputs.sql` en EVENT, además de la migración de CORE; `create_all` no añade columnas a una tabla existente. Los eventos históricos carecen de esos insumos y el verificador responde `false` (no verificable); no rellenarlos con valores inventados. La prueba de `set_config` requiere una base PostgreSQL desechable mediante `AXS_TEST_POSTGRES_URL`. Esa prueba valida el contexto de transacción, pero todavía no comprueba políticas RLS ni el comportamiento después de `commit()` en el flujo real.

La prueba `tests/smoke/test_postgres_rls.py` crea un esquema aislado en PostgreSQL con el ORM actual, aplica RLS a `visitas` y ensaya lectura y escritura cruzada después de `commit()` y `refresh()`. La sesión se vincula al Engine para que `commit()` termine la transacción PostgreSQL real. `.github/workflows/postgres-rls.yml` la ejecuta en un servicio PostgreSQL 16 desechable con rol `NOSUPERUSER NOBYPASSRLS`; el run 36617404798 pasó las cuatro pruebas smoke, sin skips. El ejecutor local no tiene conectividad directa a Neon; el CI es evidencia del flujo Python con PostgreSQL, no una prueba sobre el despliegue Neon.

Inventario confirmado el 29-sep-2026 en Neon `patient-tree-68362559`: `neondb` contiene CORE, `aup_event` contiene EVENT y `aup_gov` contiene GOV. La rama principal es `br-empty-firefly-b5ob1gsg`; RLS está apagado y no hay políticas para `visitas`, `casetas` ni `evidencias`. El rol `neondb_owner` tiene `BYPASSRLS`; por eso la prueba falla de forma explícita si recibe un URL con ese rol. La rama aislada `br-rapid-dust-b5103vvw` contiene dos MSP y condominios ficticios; con un rol `NOBYPASSRLS`, una política por `visitas.condominio_id` mostró A solo en A, B solo en B, cero filas para UPDATE cruzado y cero filas sin contexto. La inserción A fue aceptada y la inserción B bajo contexto A fue rechazada; el conector no expuso el código de ese rechazo. Estas evidencias son de SQL en la rama aislada; CI agregó evidencia del servicio Python con PostgreSQL desechable. La prueba HTTP de rutas por ID pasó en SQLite; falta el recorrido HTTP contra PostgreSQL con RLS activo.

En esa misma rama, las políticas de `casetas` por `condominio_id` y `evidencias` por la visita referenciada devolvieron únicamente las filas A bajo contexto A, únicamente B bajo contexto B y ninguna sin contexto. Los UPDATE cruzados no devolvieron filas. `evidencias` no tiene columna `condominio_id`; una política que la referencie directamente es inválida. Estas pruebas no habilitan aún RLS de producción: el rol de la aplicación debe carecer de BYPASSRLS y las rutas deben ejercitarse contra PostgreSQL.

**Gate de datos previo a RLS, cerrado el 29-sep-2026:** inicialmente, 5 de 6 visitas tenían `condominio_id` nulo y las cinco tenían evidencias. Salvador confirmó que son datos de prueba. La cuenta que registró las evidencias tenía un único scope activo (`condo-piloto-01`), y la visita ya asignada del conjunto apuntaba al mismo condominio. Se ensayó en `br-rapid-dust-b5103vvw` y luego se asignaron exactamente las cinco visitas identificadas por ID en una transacción condicionada en la rama principal. Verificación posterior: 6/6 visitas en `condo-piloto-01`; cero visitas sin condominio y cero evidencias huérfanas o ligadas a visitas sin condominio. No se modificó `casa_unidad`, no se crearon membresías y no se activó RLS. Repetir este inventario antes del futuro despliegue por si se crean nuevas filas incompletas.

**Bloqueo de diseño detectado:** `database/NEON_SETUP_COMPLETE.sql` define RLS sobre `visitas.tenant_id` de otro esquema histórico, mientras el ORM vigente usa `visitas.condominio_id`. No ejecutar esa sección SQL en el esquema vigente. Las rutas por `visita_id` aceptan ahora `?condominio_id=...` para operadores de múltiples condominios; guardias y residentes usan su condominio principal. Primero se valida alcance y se fija contexto, luego se consulta la visita. Falta comprobar el recorrido HTTP contra PostgreSQL. Tampoco asumir que la política antigua `tenant_bypass_visitas` es segura para un rol de aplicación compartido entre proveedores. El ensayo aislado valida la mecánica, no da por cerrado ese contrato HTTP ni la base desplegada.

## Cobertura de este cambio

Las rutas de catálogo, casas, visitas por ID, QR, preregistro y evidencias incorporan comprobaciones de alcance. Las rutas de visitas por `condominio_id` conservan su validador de scope original; no heredan automáticamente la membresía MSP. Se debe unificar ese contrato antes de declarar terminada la fase 1. Otras rutas (`meta`, `canario`, webhooks) requieren auditoría individual y el flujo de biometría Plus queda para una fase posterior, limitado a accesos privilegiados del residente.
