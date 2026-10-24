# Sandbox corporativo: preparación y verificación del 24 de octubre de 2026

> Actualización de implementación: ver [Arranque y permisos](AXS_CORPORATIVO_SANDBOX_ARRANQUE_Y_PERMISOS.md). Este documento conserva el inventario remoto inicial; los bloqueos de vaciedad y SQL descritos abajo son el diagnóstico anterior a ese cambio.

Estado: inventario remoto de solo lectura y plan revisable. **No listo para
desplegar ni cargar personas reales.** No se aplicaron SQL, grants, LOGIN,
contraseñas, variables, dominios ni cambios staged de Railway.

## Destino exacto comprobado

| Recurso | Identificación | Resultado observado |
| --- | --- | --- |
| Neon | proyecto `patient-tree-68362559`, rama `br-soft-leaf-b59xcclw` | Rama no default, no production |
| CORE | `axs_corp_core_sbx` | 23 tablas, 23 FORCE RLS, 5 políticas; journal C4 ausente |
| GOV | `axs_corp_gov_sbx` | 4 tablas, 0 políticas operativas |
| EVENT | `axs_corp_event_sbx` | 1 tabla, 0 políticas operativas |
| Railway | proyecto `cf44e5f4-1a41-4d25-a13e-a39211cda7b6` | AXS Corporativo Sandbox |
| Entorno | `cd1b2ff7-509e-4c6b-9ea0-c537295d4cd3` | sandbox |
| Servicio | `e395d483-dd09-4f50-a1e8-415787be5b30` | Solo staged; configuración live vacía |
| Patch staged | `3049bbc4-ff6e-44fa-9d35-552dee64b944` | STAGED, 22 cambios; no aplicado |
| Fuente staged | `ee25113efd94006c36525db53075ecfc622f179a` | Anterior a C3 validado `8c3290e6f0a358dc577287d0f45b241957a5c57c` |

Se comprobó `EXISTS` en las **28 tablas**: ninguna contiene filas. La inspección
usó internamente `neondb_owner`, cuyo BYPASSRLS fue comprobado antes, por lo que
estos ceros no proceden de una vista filtrada por tenant. No se leyeron valores
de registros ni se extrajeron contraseñas.

En las tres bases nuevas, `axs_core_app`, `axs_corp_sandbox_gov`,
`axs_corp_sandbox_event` y `axs_corporate_provisioner` tienen **cero tablas con
SELECT/INSERT/UPDATE/DELETE**. Ninguno tiene SUPERUSER, BYPASSRLS o membresías.
`axs_core_app` sí tiene LOGIN; los otros tres no. No equivale a un ensayo de
contraseña/login ni demuestra aislamiento de ese rol en las bases heredadas.

Railway tiene staged los tres checks de configuración, datos y CORE RLS.
No constan en live ni staged los nombres DATABASE_CORE_URL/DATABASE_URL,
DATABASE_GOV_URL, DATABASE_EVENT_URL, DATABASE_CORPORATE_PROVISIONING_URL,
CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY o SECRET_KEY. No se consultaron secretos.

## Bloqueos técnicos que hay que resolver antes de aplicar permisos

1. El código actual obliga a flags corporativos/ARCO en false y rechaza la URL
   del provisioner. Es un modo cerrado, no una configuración de ensayo funcional.
2. El gate exige bases vacías en cada arranque: una siembra legítima impediría
   reinicios. Debe separarse una **preparación offline inicial** de un **runtime
   acotado a fixtures**. No eliminar el gate ni cambiar todos los flags para pasar.
3. Un runtime sin bypass puede leer cero filas por RLS aunque existan datos.
   `require_empty` ahora usa `SET LOCAL row_security=off`: PostgreSQL deniega
   la consulta si una política podría ocultar filas; no concede bypass. Las
   pruebas PG comprueban tablas vacías y con filas ocultas. Por diseño, una cuenta
   filtrada no puede certificar vaciedad global. La certificación pertenece a
   una inspección offline autorizada, nunca a una credencial privilegiada del API.
4. Falta C4 y faltan políticas/grants operativos. La exportación del ORM inicial
   no incluía el journal de metadata separada. No repetir el bootstrap completo.
5. Falta identidad Clerk de prueba vinculada al issuer concreto. Prefijos
   `sk_test_`/`pk_test_` por sí solos no prueban correspondencia de instancia.
6. Falta frontend aislado con API sandbox explícita y CORS exacto. El fallback
   residencial de `src/lib/api.ts` no debe utilizarse en el ensayo corporativo.

## Matriz propuesta de permisos mínimos (no aplicada)

| Cuenta / dominio | Permisos a revisar por objeto | Prohibiciones |
| --- | --- | --- |
| CORE runtime corporativo dedicado, propuesto `axs_corp_sandbox_core` | Lectura de identidades sintéticas, raíz/MSP y membresías; directorio: SELECT/INSERT/UPDATE solo sedes/destinos; ARCO: SELECT/INSERT/UPDATE de casos; outbox operativo/seguridad según productor-worker | Sin DDL, DELETE, TRUNCATE, grants o escritura de membresías; no reutilizar la contraseña del runtime residencial |
| GOV `axs_corp_sandbox_gov` | SELECT de autoridades vigentes; SELECT/INSERT/UPDATE de las dos políticas corporativas por tenant; RLS específica | Sin administrar autoridades/delegaciones, sin DELETE ni acceso a CORE/EVENT |
| EVENT `axs_corp_sandbox_event` | SELECT/INSERT de eventos y USAGE de la secuencia exacta; política del publicador revisada por dominio | Sin UPDATE/DELETE, DDL o acceso a CORE/GOV |
| CORE `axs_corporate_provisioner` | Columnas y secuencia exactas de C2; C4: SELECT/INSERT y UPDATE solo estado/confirmed_at/confirmation_event_uid | Sin SELECT del outbox, sin UPDATE del payload/actor/revisión, sin roles heredados ni BYPASSRLS |
| Bootstrap/inspección offline | Preparar solo identidades sintéticas, membresías y autoridad GLOBAL de prueba; certificar esquema/datos antes de runtime | No instalar esa cuenta en backend/frontend; no copiar registros de desarrollo |

La matriz no es SQL listo para ejecutar: faltan cerrar las políticas necesarias
de identidad, outbox, ARCO y worker con el rol dedicado. Las referencias de
columnas existentes son `20261023_corporate_directory_c1.sql`,
`20261023_corporate_superadmin_c2.sql`, `20261023_corporate_reconciliation_c4.sql`
y las migraciones de ARCO/outbox. No ejecutarlas completas a ciegas contra el
esquema existente: C4 es one-shot y las demás contienen grants específicos.

## Secuencia preparada para el recorrido

1. Preparar y probar offline el contrato de dos fases y el conjunto exacto de
   SQL/políticas/grants. Mantener pins de host/bases/TLS/roles, y roles nuevos sin
   LOGIN hasta revisar el delta completo. Certificar que no haya acceso a bases
   heredadas ni grants por PUBLIC/default ACL que abran objetos.
2. Revisar/aprobar por separado el delta SQL en las tres bases de ensayo, el
   manejo de secretos y el consumo de infraestructura. Nada se aplica por este
   documento ni por una prueba CI aprobada.
3. Instalar solo lo faltante, sembrar dos empresas sintéticas y personas de
   prueba (GLOBAL, owner A, owner B, operador ARCO y actor sin facultades).
   Verificar los sujetos Clerk reales contra esos registros exactos, sin emails
   ni invitaciones automáticas.
4. Probar conexiones con las cuentas limitadas; luego preparar Railway con SHA
   validado, variables backend secretas y frontend de prueba con issuer/API
   explícitos. Revisar el patch completo antes de `accept-deploy`.
5. Iniciar sesión con Clerk de prueba y recorrer la matriz de aceptación de
   abajo. Ninguna aprobación implica merge a main o activación residencial.

## Matriz de aceptación del ensayo

| Actor / acción | Resultado exigido |
| --- | --- |
| GLOBAL crea empresa A, repite UUID/payload | Una empresa/owner, sin casas ni residentes ficticios |
| UUID reutilizado con otro payload | 409 sin cambios |
| Cuotas: ACK perdido, reconsulta y reintento | Journal conserva intención/revisión; no duplica ni confirma deriva |
| Habilitar directorio | Requiere confirmación y cuotas confirmadas vigentes |
| Owner A consulta/crea sede o destino B | Denegado, sin cambios ni filtración |
| MSP sin GLOBAL intenta aprovisionar | 403 |
| Operador ARCO designado | Selector solo clientes vigentes; recepción/avance privados e idempotentes |
| Revocar membresía/designación con el mismo JWT | Siguiente petición denegada y cliente retirado al actualizar |
| Empresa deshabilitada, operador de privacidad vigente | ARCO disponible; directorio operativo denegado |
| Cambio de sesión/cliente y respuesta tardía | Formularios y expedientes previos retirados |
| Reiniciar después de la siembra | Contrato runtime valida fixtures; nunca exige volver a cero ni borra datos |
| Restauración de ensayo | Cuarentena revoca facultades antiguas; revisión ARCO documentada antes de liberar |

Cierre: reporte de pasos, códigos HTTP, registros sintéticos afectados y CI por
SHA, sin tokens, contraseñas ni capturas con secretos. Eliminar/rotar secretos de
prueba por procedimiento aprobado al terminar. Mantener los PR en borrador.

Esta preparación no acredita ejecución ARCO empresarial general, borrado de
proveedores reales ni reaplicación automática de decisiones sobre respaldos.
