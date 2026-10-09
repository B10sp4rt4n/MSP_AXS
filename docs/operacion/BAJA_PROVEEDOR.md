# Baja integral de un proveedor por condominio

Sólo un operador de plataforma con Authority GLOBAL activa puede registrar
procedencia, consultar el inventario completo y ejecutar la baja. El director
MSP y el administrador del condominio no pueden clasificar sus propios permisos
como locales ni ejecutar esta operación.

1. GET `/condominios/{id}/permisos/procedencia` devuelve cada scope y su origen.
2. PUT `/condominios/{id}/permisos/{scope_id}/procedencia`, con `kind` igual a
   `msp` o `condominio`, `msp_id` sólo para MSP y `evidence_ref`, documenta los
   permisos antiguos. Si el origen ya está definido no puede cambiarse: se debe
   revocar el permiso y conceder otro. No se deduce del rol o del campo legacy
   `Usuario.msp_id`. La referencia es declaración del operador; no se verifica
   automáticamente el expediente externo.
3. POST `/condominios/{id}/proveedor/baja`, con `msp_id` esperado y `reason`,
   bloquea la fila del condominio y comprueba TODOS los scopes no revocados,
   incluidos inactivos/suspendidos. Si uno carece de origen o corresponde a otro
   proveedor, devuelve 409 sin ejecutar la baja.
4. Revoca los scopes del MSP saliente, conserva los locales, desvincula el MSP y
   guarda actor, fecha, motivo e IDs afectados en el outbox, todo en una única
   transacción CORE. No toca visitas, evidencias, identidades, membresías globales
   ni permisos de otros condominios. Las autoridades de plataforma siguen siendo
   independientes de la relación comercial.
5. Repetir la solicitud devuelve el mismo comprobante sin otro evento. Si ahora
   hay otro proveedor devuelve 409 para la ruta legacy. En relaciones versionadas
   se exige `contract_id`: un cierre ya realizado devuelve su comprobante sin
   afectar un contrato posterior. Ver CONTRATOS_PROVEEDOR.md para la recontratación.

Las autorizaciones operativas que pasan por require_condominio y la baja toman
el mismo bloqueo de fila. Una solicitud ya autorizada termina antes de la baja;
las siguientes consultan los permisos vigentes incluso con el mismo JWT. Esto
se comprueba con PostgreSQL, además de fallas de auditoría e idempotencia.

## Procedencia de altas nuevas

Personal creado por un administrador MSP queda atribuido al MSP vigente. Un
administrador local con permiso de origen condominio crea permisos locales;
uno con permiso de proveedor los atribuye a ese proveedor. Altas de operador
GLOBAL y de administradores legacy sin origen quedan `unknown` hasta una
declaración explícita. Los permisos de residencia concedidos mediante asignación
de vivienda y el administrador local aprobado en recuperación se registran como
condominio por el acto que los origina, no por inferencia sobre un permiso antiguo.

Las ediciones de cuentas conservan esta procedencia. Helpers legacy que no pasan
por estas altas pueden seguir generando permisos sin origen: la baja se bloquea
hasta clasificarlos. No hay reclasificación masiva ni migración automática de
permisos existentes. No se ejecuta ninguna baja real al desplegar este código.
