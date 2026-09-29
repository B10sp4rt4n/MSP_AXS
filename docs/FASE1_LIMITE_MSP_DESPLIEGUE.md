# Fase 1: límite de proveedor y condominio

Estado: propuesta de implementación. No desplegar antes de verificar los tres dominios de datos reales.

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
3. Revisar índices, claves foráneas, respaldo y plan de reversión. Aplicar la migración en staging y probar creación/revocación de membresía, dos MSP y dos condominios por MSP.
4. Verificar en PostgreSQL las políticas RLS y las rutas que crean o modifican visitas. `set_config(..., true)` dura la transacción: los servicios actuales hacen `commit()` y `refresh()`, por lo que hay que demostrar el comportamiento después del commit. Las rutas por `visita_id` aún resuelven la visita antes de fijar contexto de tenant. No afirmar aislamiento de base de datos hasta cerrar ambas pruebas.
5. Validar gobierno de `crear_tenant` y límites por proveedor. La política actual es global y cuenta todos los condominios; un cupo contractual por MSP requiere un diseño separado. Comprobar también registro EVENT de las altas y revocaciones de membresía antes de habilitar operación real.
6. Solo después de estas verificaciones, desplegar de forma escalonada y repetir los casos de acceso cruzado en staging y producción controlada. Si falta la tabla o la autoridad, las nuevas rutas deniegan acceso.

## Pruebas recuperadas y EVENT

Las pruebas de sesión, planes y verificación de eventos ya se ejecutan en SQLite. El verificador de EVENT ahora conserva `event_uid` y `session_hash` para eventos nuevos. Antes de desplegar el código, aplicar `database/migration_07_event_integrity_inputs.sql` en EVENT, además de la migración de CORE; `create_all` no añade columnas a una tabla existente. Los eventos históricos carecen de esos insumos y el verificador responde `false` (no verificable); no rellenarlos con valores inventados. La prueba de `set_config` requiere una base PostgreSQL desechable mediante `AXS_TEST_POSTGRES_URL`. Esa prueba valida el contexto de transacción, pero todavía no comprueba políticas RLS ni el comportamiento después de `commit()` en el flujo real.

La prueba `tests/smoke/test_postgres_rls.py` crea un esquema aislado en PostgreSQL con el ORM actual, aplica RLS a `visitas` y ensaya lectura y escritura cruzada después de `commit()` y `refresh()`. Debe correr con un rol sin `BYPASSRLS`, permiso de crear esquemas y una base **desechable**, nunca con el URL de producción. El entorno actual no expone un PostgreSQL de AX-S ni `AXS_TEST_POSTGRES_URL`; la prueba queda pendiente de ejecución real.

**Bloqueo de diseño detectado:** `database/NEON_SETUP_COMPLETE.sql` define RLS sobre `visitas.tenant_id` de otro esquema histórico, mientras el ORM vigente usa `visitas.condominio_id`. No ejecutar esa sección SQL en el esquema vigente. Las rutas por `visita_id` consultan la fila antes de establecer el contexto del tenant; al activar RLS deberán recibir o resolver primero un `condominio_id` autorizado. Tampoco asumir que la política antigua `tenant_bypass_visitas` es segura para un rol de aplicación compartido entre proveedores. El ensayo aislado valida la mecánica, no da por cerrado ese contrato HTTP ni la base desplegada.

## Cobertura de este cambio

Las rutas de catálogo, casas, visitas por ID, QR, preregistro y evidencias incorporan comprobaciones de alcance. Las rutas de visitas por `condominio_id` conservan su validador de scope original; no heredan automáticamente la membresía MSP. Se debe unificar ese contrato antes de declarar terminada la fase 1. Otras rutas (`meta`, `canario`, webhooks) requieren auditoría individual y el flujo de biometría Plus queda para una fase posterior, limitado a accesos privilegiados del residente.
