# C4: propuesta de conciliación CORE/GOV

Estado: implementación local; no publicada ni aplicada en Neon/Railway. Base de
revisión: PR #100, `e9320128fff8b89c3aeaec30d7072b4e0c40678d`. No habilita
visitas, QR, acceso físico ni cambios residenciales. ARCO continúa pendiente.

## Contrato HTTP

`PUT /plataforma/corporativo/empresas/{tenant_id}/capacidades` exige:

```json
{
  "request_id": "UUID nuevo por intención",
  "expected_revision": 0,
  "max_sedes": 2,
  "max_destinos_por_sede": 10
}
```

- Primera intención/empresa legacy: revisión 0. Las siguientes usan la revisión
  obtenida de GET. El servidor incrementa la revisión bajo lock por empresa.
- UUID + tenant + revisión previa + cuotas + versión de contrato identifican
  una intención. Reutilizar UUID con otro contenido devuelve 409 sin cambios.
- El reintento conserva UUID, revisión y payload incluso tras pérdida de ACK.
  Si está confirmado y todavía corresponde a GOV, devuelve 200 sin escribir.
- Una operación anterior sustituida devuelve 409, incluso en A→B→A. Una
  revisión obsoleta no permite una intención nueva desde una pantalla vieja.
- Otra intención mientras existe `pending`/`needs_review` devuelve 409.
- Fallos de commit/ACK devuelven 503 y el UUID, nunca un éxito inferido del
  rollback local. La siguiente petición abre sesiones nuevas y consulta estado.
- GET expone `capacidades_revision`, `capacidades_operacion` y
  `capacidades_confirmadas`. Números GOV presentes no equivalen a confirmación.
  Habilitar exige la operación CORE confirmada y el par GOV vigente coincidente.

## Transacciones y concurrencia

1. CORE: lock de empresa, validar revisión, insertar operación y solicitud en
   outbox en una misma transacción. El registro conserva su UID de solicitud.
2. Reabrir CORE, bloquear empresa/operación y revalidar estado/revisión después
   de la ventana de prepare. Mantener ese lock hasta terminar la conciliación.
3. GOV: bloquear ambas políticas en orden estable. Si ya tienen el marcador
   `{request_id,payload_hash,revision}` y las cuotas efectivas correctas, no
   reaplicar. Si no, comparar los hashes del snapshot previo bajo el lock.
   Cuotas y ambos marcadores se guardan juntos en un único commit GOV.
4. Releer GOV bajo lock. CORE inserta confirmación y cambia estado/UID/fecha
   atómicamente. El provisioner no necesita leer event_outbox.

No se adquiere un lock CORE manteniendo locks GOV de una fase anterior.
El índice parcial permite una sola operación no resuelta por tenant. La FK
apunta al perfil corporativo; RLS se fuerza con app.tenant_id. No se almacena
token ni se copia metadata arbitraria GOV: sólo cuotas, actor, IDs y hashes.

La metadata de eventos permite correlación; el hash de eventos preexistente no
protege criptográficamente todos los campos metadata. No se afirma lo contrario.

## Deriva e historia anterior

- Un marcador parcial, cuotas/estado/vigencia cambiados o snapshot divergente
  durante pending quedan en `needs_review` con evento de conflicto. No se pisa
  GOV, no se confirma y la UI bloquea reintentos/nuevas intenciones.
- Resolver `needs_review` requiere una decisión y procedimiento explícitos;
  este cambio no introduce cancelación/reparación automática de deriva externa.
- Los escritores soportados de estas dos políticas pasan por este protocolo.
  Un administrador externo capaz de restaurar exactamente todo el estado
  A→B→A puede escapar a una comparación de snapshots. No es un diario global
  de cambios externos ni una transacción distribuida.
- Las cuotas legacy sin registro siguen visibles pero no confirmadas. Una
  nueva intención explícita de revisión 0 establece trazabilidad hacia delante.
  No inventa correlación ni borra eventos históricos huérfanos.
- GOV puede quedar aplicado mientras falta confirmación CORE. El intento está
  conservado y el control-plane no declara éxito; no se promete atomicidad
  instantánea entre bases ni se cambia el evaluador de cuotas existente.

## Migración propuesta y aprobación pendiente

`migrations/20261023_corporate_reconciliation_c4.sql` es manual y transaccional,
one-shot. Crea `corporate_provisioning_operations`, restricciones/índice y FORCE
RLS. Cualquier tabla/índice previo o ACL por defecto inesperada aborta: un
resultado incierto debe inspeccionarse, no repetirse a ciegas.

Permisos nuevos exactos, sólo después de autorización sobre el destino concreto:

- `axs_corporate_provisioner`: SELECT e INSERT en la tabla nueva; UPDATE sólo
  de estado, confirmed_at y confirmation_event_uid.
- Ningún UPDATE de tenant, UUID, revisión, payload, hash, actor o snapshot.
- Ningún DELETE, TRUNCATE, DDL, BYPASSRLS, LOGIN, contraseña, membresía, permiso
  nuevo en event_outbox ni cambio de axs_core_app.
- GOV utiliza el UPDATE de políticas ya requerido por C2; no concede permisos
  GOV ni convierte el sandbox actualmente cerrado en operativo.

El modelo utiliza metadata separada: importar/iniciar el backend no crea esta
tabla mediante el create_all legacy. Sin migración/permisos aprobados, el flujo
de conciliación queda bloqueado. No ejecutar este SQL desde deploy/startup.

## Validación reproducible

- Suite Python completa y regresiones HTTP en `tests/test_corporate_reconciliation.py`.
- Gate PostgreSQL existente incorpora `tests/smoke/test_corporate_reconciliation_postgres.py`:
  CORE/GOV usan conexiones/sesiones y schemas PostgreSQL independientes, datos
  sintéticos, JWT real de prueba, provisioner restringido y permisos/RLS reales.
  No usa Neon ni Clerk real. EVENT sigue fixture sintético.
- Inyección antes/después de los tres commits, ACK perdido, sesiones nuevas,
  concurrencia, A→B→A, revisión obsoleta, payload conflictivo, deriva, aislamiento,
  permisos negativos y ausencia de creación automática del journal.
- Frontend: roles, gate SSR y TypeScript. Browser sintético ampliado en el
  workflow existente; ejecución local Chromium limitada por sockets del entorno.

Antes de publicar: revisar diff, aprobar publicación del cambio concreto y
ejecutar CI del SHA publicado. Antes de aplicar: aprobar por separado destino
de migración y privilegios. Esta propuesta no autoriza merge ni despliegue.

### Evidencia local final — 23 octubre 2026

- Python: **714 aprobadas, 49 omitidas**; las omisiones requieren el gate PG.
- Gate PostgreSQL **17.11** descartable: **109 aprobadas**, incluidas **18** de
  conciliación con dos conexiones/schemas y sesiones nuevas por petición.
- Frontend: roles **34/34**, gate SSR **4/4**, DOM corporativo **6/6**;
  Next typegen y TypeScript aprobados. DOM utiliza React/componente reales con
  API/Clerk sintéticos y jsdom **26.1.0** fijado en el workflow.
- Chromium local no pudo iniciarse por `socket() Operation not permitted`;
  la ejecución escalada tampoco pudo iniciar por bwrap/filesystem de sólo lectura.
  No se eludió el bloqueo. El browser ampliado queda pendiente de CI autorizado.
- ESLint dirigido mantiene un error preexistente `react-hooks/set-state-in-effect`,
  reproducido también sobre la base; no se presentó como una pasada de lint.
- PostgreSQL temporal apagado al terminar. Sin cambios externos, publicación,
  ampliación de permisos persistentes, merge ni despliegue.
