# Modo de recuperación operativa

## Contrato

Antes de conectar una restauración, configurar un UUID NUEVO en
`AXS_RECOVERY_INCIDENT` en todos los procesos API y workers, fuera de las bases
restauradas. Reiniciar y drenar procesos anteriores; mantener el destino aislado.
No reutilizar el UUID de una recuperación anterior ni quitarlo para abrir tráfico.
La aplicación no detecta por sí sola que un proveedor restauró una base: este
paso forma parte obligatoria del procedimiento de restauración.

Sin la variable, la operación existente continúa normalmente. Una variable vacía
o inválida bloquea. Con un UUID configurado, CORE y GOV deben contener checkpoints
`released` para ese UUID y el mismo nonce de liberación. Ausencia de tablas,
checkpoint faltante, diferencia entre dominios o conexión fallida bloquean.
Un respaldo anterior al incidente no contiene esos marcadores. Restaurar otra vez
requiere siempre otro UUID, incluso si el respaldo contiene marcadores anteriores.

Mientras está bloqueado:

- Toda operación HTTP devuelve 503, incluyendo QR por GET, autenticación,
  registro, webhooks y lecturas. No se ejecuta el middleware de sesión ni sus
  escrituras de auditoría. El rechazo se observa en los logs HTTP del proveedor.
- `/health` mantiene liveness 200 con `ready=false`; `/ready` devuelve 503.
  Usar `/ready` para decidir si el destino puede recibir tráfico operativo.
- El worker no envía ciclos del outbox. Una vez liberado vuelve a comprobar los
  marcadores en cada ciclo. Las llamadas offline de conciliación son explícitas.
- CORS puede responder preflight OPTIONS; no ejecuta operaciones de negocio.

## Operación offline

Desde la raíz del repositorio, suministrar explícitamente las tres conexiones
DEL DESTINO (`DATABASE_CORE_URL`, `DATABASE_GOV_URL`, `DATABASE_EVENT_URL`) y el
UUID en `AXS_RECOVERY_INCIDENT`. El CLI no carga `.env` ni usa URLs por defecto.
El operador necesita visibilidad completa y permisos de recuperación; el CLI
rechaza un rol cuya RLS pueda esconder filas. Nunca otorgar bypass al rol runtime.
Ejecutar un único operador y mantener detenidos otros escritores y workers
externos durante todo el procedimiento. No conectar producción a estas URLs.

El CLI crea únicamente las tablas nuevas de checkpoints si no existen. El rol
runtime requiere SELECT sobre `recovery_checkpoints` en CORE y
`recovery_gov_checkpoints` en GOV; el operador conserva escritura. Aplicar esos
grants con el administrador del destino y los nombres reales de sus roles antes
de probar `/ready`. No conceder escritura de checkpoints a clientes o usuarios.

1. Cuarentena (reintentable antes de liberar):

```sh
python -m scripts.recovery quarantine --incident "$AXS_RECOVERY_INCIDENT" --actor operador
```

Revoca scopes, membresías MSP, autoridades y delegaciones activas. Cancela las
visitas pendientes/activas e invalida todos los tokens QR anteriores. Conserva
estados de personas ya ingresadas, evidencias y ledger. Guarda conteos y operador
en el checkpoint. Ante una falla entre CORE/GOV el bloqueo permanece.

2. Conciliación:

```sh
python -m scripts.recovery reconcile --incident "$AXS_RECOVERY_INCIDENT" --backup-cutoff 2026-10-09T05:00:00+00:00
```

Reemplazar la fecha de ejemplo por el corte real del respaldo. Compara todo el
outbox de visitas y seguridad, incluyendo filas marcadas entregadas, con EVENT.
Reinserta sólo eventos faltantes por event_uid mediante el publicador idempotente;
un payload distinto o hash inválido impide la liberación y nunca sobrescribe el
ledger. Lista eventos posteriores al corte y genera una huella de todos los datos
de CORE/GOV/EVENT, excluyendo checkpoints.

Los eventos posteriores disponibles ayudan a investigar movimientos; no prueban
que se conservaron todos los hechos perdidos. Permisos o usos no documentados
siguen sin autorizar: no se reconstruyen ni conceden por inferencia. La herramienta
no recrea visitas desaparecidas ni ajusta automáticamente la ocupación física.

3. Verificar ocupación, identidades externas, evidencia externa y discrepancias.
Conservar el reporte y referencia del expediente del incidente fuera del destino.
Si se corrigen datos, ejecutar de nuevo la conciliación. Elegir un administrador
existente del condominio cuya identidad haya sido verificada por el operador.

4. Liberación explícita:

```sh
python -m scripts.recovery release --incident "$AXS_RECOVERY_INCIDENT" --actor operador --evidence-ref expediente-verificado --occupancy-verified --admin-id administrador-validado --tenant-id condominio-validado
```

Exige conciliación, misma huella de datos, ausencia de permisos/QR anteriores
activos y confirmación explícita de ocupación. La referencia y la confirmación
son declaraciones del operador; la herramienta no verifica físicamente el lugar
ni autentica el contenido del expediente. Concede únicamente un scope NUEVO de
administrador para el usuario/condominio indicados. No recupera autoridad global
ni membresías MSP. Registra la decisión y libera ambos checkpoints con un nonce
nuevo. Si el commit entre dominios falla, permanece cerrado; iniciar un incidente
nuevo para repetir el procedimiento. No editar marcadores a mano para forzar paso.

5. Validar `/ready`, denegación de usuarios antiguos y QR previos, acceso nuevo
expresamente autorizado y conciliación del outbox. Reconectar tráfico gradualmente.
Mantener el UUID configurado. Reautorizar otros usuarios por el procedimiento de
administración vigente, sin reactivar en lote los permisos del respaldo.

## Alcance y límites

La suite usa bases separadas en SQLite y tres esquemas/conexiones independientes
PostgreSQL en CI. Cubre bloqueo HTTP, worker, fallas parciales, reconciliación
idempotente, cambios posteriores a conciliación y reapertura con QR nuevo.
El ensayo pg_dump/pg_restore de la PR #33 sigue ejecutándose en el mismo gate.

No se ha activado un incidente ni ejecutado cuarentena en producción. Esta versión
requiere aislamiento y un solo operador: no coordina escrituras de sistemas
externos ni solicitudes que ya estaban en vuelo. La huella completa está pensada
para recuperación offline; su costo crece con los datos y debe medirse en un
ensayo de tamaño productivo. No certifica RTO/RPO ni recuperación Clerk/Cloudinary.
