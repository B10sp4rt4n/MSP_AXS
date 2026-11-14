# AXS — backend efectivo y restauración real, 14 de noviembre de 2026

## Resultado

Se identificaron las conexiones dentro del contenedor productivo de Railway,
se ejecutaron los gates de CORE en transacciones READ ONLY y se creó un
snapshot de las tres bases. Su restauración aislada quedó comprobada.
La publicación queda pendiente por privilegios excesivos en EVENT/GOV y por
alinear la configuración JWKS de Clerk. No se cambiaron esos permisos,
variables, datos de aplicación ni deployments productivos.

[Manifiesto agregado sin credenciales ni datos de titulares](AXS_BACKEND_Y_RESTAURACION_REAL_20261114.json).

## Conexiones observadas en el contenedor

Auditoría iniciada: `2026-11-14T13:37:25.587766+00:00` (07:37 CDMX).
Servicio `web`, deployment `be9b87a6-8a58-4341-a181-b4fc70ebd808`, código
`a68d1149242dd0b16cd0e363df3ccda917199423`.

Las tres conexiones usan PostgreSQL 18.6 y el host
`ep-rough-voice-b5vx4odv-pooler.c-7.us-east-2.aws.neon.tech`, que Neon vincula a
`patient-tree-68362559 / br-empty-firefly-b5ob1gsg`.

| Dominio | Base efectiva | current_user / session_user | Resultado |
| --- | --- | --- | --- |
| CORE | `neondb` | `axs_core_app` / `axs_core_app` | Gate RLS PASS; gate de esquema PASS, seis tablas corporativas. |
| EVENT | `aup_event` | `neondb_owner` / `neondb_owner` | Conexión confirmada; rol propietario con permisos excesivos. |
| GOV | `aup_gov` | `neondb_owner` / `neondb_owner` | Conexión confirmada; rol propietario con permisos excesivos. |

Se confirmó `transaction_read_only=on` en las consultas de las tres bases.
Las URLs completas y contraseñas no salieron del contenedor.

## Configuración efectiva y hallazgos

Los flags `AXS_CORPORATE_API_ENABLED`, `AXS_CORPORATE_PROVISIONING_ENABLED` y
`AXS_CORPORATE_SANDBOX_ONLY` valen `false`. CORS incluye
`https://app.axs-mx.com`, además de localhost y el frontend Railway histórico.
Esta lectura no acredita los callbacks ni una sesión Clerk del piloto.

### EVENT y GOV

La consulta de catálogos mediante Neon confirmó que `neondb_owner` tiene
`rolbypassrls`, `rolcreatedb`, `rolcreaterole` y `rolinherit` activos. Posee las
tablas de ambos dominios; puede SELECT/INSERT/UPDATE/DELETE/TRUNCATE. No tiene
`rolsuper`. EVENT contiene `events_aup`; GOV contiene `authorities_gov`,
`delegations_gov`, `policies_gov` y `recovery_gov_checkpoints`. Ninguna de esas
cinco tablas tiene RLS activo.

Por tanto, las credenciales runtime actuales no imponen append-only en EVENT
ni separan la administración del esquema de la operación GOV. El gate CORE
aprobado no acredita los permisos de los otros dominios. Se requiere un cambio
separado y ensayado de roles/grants y conexiones runtime, con revisión de los
accesos que realmente necesita cada servicio. No se crearon roles ni grants
en producción durante esta comprobación.

### Clerk

Issuer observado: `https://clerk.auth.axs-mx.com`.
JWKS configurado: `https://vocal-bee-4163.clerk.accounts.dev/.well-known/jwks.json`.
El dominio público decodificado del backend es `clerk.auth.axs-mx.com` y existe
una clave pública fijada (`CLERK_JWT_PUBLIC_KEY`); sólo se imprimió su presencia.

El código `verify_clerk_token` utiliza primero esa clave fijada. Si no existe,
la ruta JWKS exige que la URL coincida con el dominio de Clerk y rechazaría la
URL Development actual. Esto demuestra una configuración incoherente de esa
ruta alternativa, no un fallo actual de login ni aceptación de tokens ajenos.
La propuesta concreta es alinear JWKS a
`https://clerk.auth.axs-mx.com/.well-known/jwks.json`, conservando la clave fijada
y verificando autenticación después del cambio. No se rotó ni se leyó la clave
secreta, y no se modificó la configuración remota.

## Snapshot y restauración

| Elemento | Valor |
| --- | --- |
| Snapshot | `snap-orange-hill-b5sz65pw`, `axs-preliberacion-20261114` |
| Origen | `br-empty-firefly-b5ob1gsg` |
| Creación | 14 noviembre, 07:40:13 CDMX (`2026-11-14T13:40:13Z`) |
| Punto de datos declarado por la rama restaurada | 14 noviembre, 07:39:39 CDMX; LSN `0/58F97F0` |
| Vencimiento del snapshot | 21 noviembre, 07:40:13 CDMX (`2026-11-21T13:40:13Z`) |
| Rama restaurada | `br-fancy-firefly-b5ov421w`, `axs-restauracion-aislada-20261114` |
| Método | `restore_snapshot`, sin target de producción y con `finalize=false` |
| Endpoint de comprobación | `ep-lingering-tree-b54koo6i`, read_only, 0.25 CU, autosuspensión 300 s |
| Cierre del endpoint | `disabled=true`, estado `idle`, confirmado por lectura posterior |
| Vencimiento de la copia temporal | 15 noviembre, 07:46:24 CDMX (`2026-11-15T13:46:24Z`) |

La rama quedó `ready/restored`, contiene las tres bases y no es default ni
primary. No se conectó a ella ninguna aplicación o worker. El endpoint
productivo `ep-rough-voice-b5vx4odv` permaneció en la rama original, activo y
habilitado. No se ejecutó finalize ni sustitución de computes.

## Comprobaciones sobre datos restaurados

| Comprobación | CORE | EVENT | GOV |
| --- | --- | --- | --- |
| Tablas públicas recuperadas | 23 | 1 | 4 |
| Columnas | 204 | 14 | 34 |
| Constraints | 198 | 12 | 26 |
| Índices | 70 | 16 | 24 |
| Políticas RLS | 13 | 0 | 0 |
| Catálogo y ACL de tablas frente al origen observado | Iguales | Iguales | Iguales |
| Relaciones FK revisadas sin huérfanos | 34 | No aplica | 1 |

La comparación excluye datos de filas y objetos externos al catálogo público
seleccionado; no equivale a igualdad de todas las propiedades administradas
por Neon. Se contaron todas las tablas restauradas. Entre ellas: seis
condominios, 22 usuarios, 38 visitas, 12 evidencias, 91 filas de event_outbox,
56 de security_outbox, 267 eventos, una autoridad y seis políticas. Los conteos
completos están en el JSON adjunto, sin nombres ni contenido de titulares.

Desde el contenedor Railway se conectó a la copia cambiando sólo el host de
las URLs en memoria. `pg_is_in_recovery=true` y transacciones READ ONLY
confirmaron el endpoint de lectura. CORE volvió a aprobar ambos gates bajo
`axs_core_app`.

Se recorrieron los 267 eventos dentro del proceso y se utilizó la función
existente `verificar_integridad_evento`, sin exportar sus campos:

- 202 tienen hash verificable y coincidente.
- 65 carecen de event_uid o session_hash: son históricos no verificables con
  ese contrato; no se presentan como íntegros ni como alterados.
- Cero discrepancias entre los eventos verificables.

## Límites y decisión

La restauración consultable, los gates, los catálogos, las relaciones y los
hashes delimitados quedaron verificados. No se compararon todas las filas
contra una exportación independiente del instante original; producción siguió
operando. No se reencolaron ni enviaron outboxes, ni se reactivaron permisos.
Antes de usar la copia como aplicación debe conciliarse cualquier revocación
o escritura posterior al punto de recuperación.

Este snapshot respalda PostgreSQL dentro de Neon. No es un dump externo ni
incluye los binarios privados de Vercel Blob; las 12 filas de evidencia son
referencias/metadatos, no prueba de disponibilidad de cada fotografía.
RPO/RTO productivos, recuperación de objetos y aceptación real de cámara/Clerk
permanecen pendientes. El snapshot es anterior a una futura ventana de deploy:
deberá refrescarse el punto de recuperación cuando se acuerde esa ventana.

Siguiente cambio a preparar: segregación de EVENT/GOV y corrección JWKS,
ensayados antes de publicar. La comprobación presente no autoriza su aplicación
remota ni una liberación productiva.
