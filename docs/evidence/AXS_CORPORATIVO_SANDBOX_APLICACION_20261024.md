# Aplicación de permisos al sandbox — 24 de octubre de 2026

Autorización: Salvador indicó «Adelante» tras proponer aplicar el paquete revisado al sandbox. Código validado: 2420f0d7101aa71e0b8ffc95b761bab6b053cdb2 (122 pruebas PostgreSQL y 1196 Python aprobadas). Este registro no modifica código ejecutable.

## Destino confirmado
- Proyecto: patient-tree-68362559.
- Rama: br-soft-leaf-b59xcclw, axs-corporativo-c0-c2-ensayo-20261023; no predeterminada, no primaria.
- Endpoint: ep-bitter-snow-b5sgxc4h.
- Bases exclusivas: axs_corp_core_sbx, axs_corp_gov_sbx, axs_corp_event_sbx.
- Inspector: neondb_owner con BYPASSRLS. No se leyeron ni imprimieron filas de aplicación.

## Operación ejecutada
Primero se verificaron las 28 tablas existentes mediante EXISTS con visibilidad completa: ninguna tenía filas. Cada aplicación usó una transacción por base, bloqueos ACCESS EXCLUSIVE y una segunda comprobación de vaciedad que abortaría ante cualquier fila.

1. CORE: 20261023_corporate_reconciliation_c4.sql y 20261024_corporate_sandbox_core_permissions.sql.
2. GOV: 20261024_corporate_sandbox_gov_permissions.sql.
3. EVENT: 20261024_corporate_sandbox_event_permissions.sql.

Los archivos se ejecutaron conservando sus sentencias, con BEGIN/COMMIT sustituidos por la transacción del conector. CORE añadió una comprobación de nombre de base antes de C4. Las tres transacciones finalizaron correctamente.

## Verificación posterior real
| Base | Tablas | Sin FORCE RLS | Diferencias ACL tabla | Diferencias ACL columna | Filas presentes |
| --- | ---: | ---: | ---: | ---: | ---: |
| CORE | 25 | 0 | 0 | 0 | 0 |
| GOV | 5 | 0 | 0 | 0 | 0 |
| EVENT | 2 | 0 | 0 | 0 | 0 |

Los cuatro roles siguen NOLOGIN, NOINHERIT, sin superusuario, BYPASSRLS, creación de bases/roles, replicación, membresías heredadas, propiedad de tablas ni capacidad CREATE/TEMP. La comparación incluye privilegios delegables de tabla/columna: cero diferencias.

Secuencias accesibles: solo USAGE de condominios_exo_id_seq al provisioner y events_aup_id_seq al rol EVENT. Función accesible: solo corporate_sandbox_lock_company a CORE.

Las tres tablas de constancia están vacías. No se emitió una certificación ni se inició su ventana de 24 horas.

## Pendientes para ensayo
Railway, servicio axs-corporativo-api-sandbox, no tiene claves Clerk configuradas ni variables selladas; la consulta solo encontró las variables internas de Railway. Falta identificar la instancia Clerk de desarrollo y suministrar sus credenciales mediante un canal seguro.

Después: certificar bases vinculando issuer real de prueba y UUID compartido; sembrar identidades sintéticas con subjects correctos; preparar credenciales segregadas y frontend aislado; configurar y desplegar el servicio de ensayo y ejecutar la matriz HTTP. No inventar issuer ni subjects y no reutilizar credenciales residenciales.

No se habilitó LOGIN, no se crearon contraseñas, no se sembraron datos ni se desplegó Railway. No se operaron producción, San Luis ni las bases heredadas neondb/aup_gov/aup_event.
