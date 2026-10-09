# Cambio de proveedor y recontratación

El operador AX-S con Authority GLOBAL activa administra el ciclo. La identidad
MSP mantiene su membresía global: al abrir el contrato, sus administradores
vuelven a administrar ese condominio. El personal requiere permisos propios
del nuevo contrato; no se reactivan scopes antiguos.

## Secuencia

1. Cerrar la relación actual mediante `POST /condominios/{id}/proveedor/baja`.
   Los vínculos anteriores a esta función se cierran como antes. Si hay contrato
   versionado, el cuerpo debe incluir su `contract_id`, además de `msp_id` y `reason`.
2. Abrir con `POST /condominios/{id}/proveedor/contratos`: enviar `contract_id`
   (UUID nuevo, conservarlo para reintentos), `msp_id` y `evidence_ref`.
   El proveedor debe existir y el condominio estar desvinculado. Cualquier permiso
   no revocado que no sea propio del condominio bloquea el alta.
3. Si se reincorpora personal existente, usar
   `POST /condominios/{id}/proveedor/contratos/{contract_id}/personal/{usuario_id}`
   con `evidence_ref`. Crea un scope nuevo para guardia o administrador ya asociado
   a ese condominio, sin modificar la identidad ni el permiso revocado. Permisos
   activos distintos se rechazan. Una repetición devuelve el mismo scope.
4. Las altas de personal del panel atribuidas al MSP registran automáticamente el
   contrato vigente. Las altas locales conservan origen condominio.
5. Consultar `GET /condominios/{id}/proveedor/contratos` para el historial, fechas,
   versiones y referencias de eventos. Este endpoint también exige operador GLOBAL.

Se puede cambiar de MSP o volver a contratar al mismo: la versión aumenta por
condominio. Los dos pasos cierre/alta son transacciones independientes; si falla
el alta, el condominio queda desvinculado y conserva sus permisos locales. Esto
permite un intervalo deliberado sin proveedor, no una sustitución silenciosa.

## Reintentos y autoridad

Un UUID de apertura es inmutable: reutilizarlo con otros datos devuelve 409.
Repetir una apertura cerrada devuelve su estado cerrado y nunca la reabre.
Repetir un cierre antiguo devuelve el comprobante anterior, incluso si ya existe
un contrato nuevo, sin revocar permisos de éste. Omitir `contract_id` mientras
hay contrato activo devuelve 409. La referencia de evidencia es una declaración
del operador; no valida por sí misma un contrato legal externo.

Cada mutación guarda su evento en la misma transacción CORE. El bloqueo del
condominio y un índice único parcial impiden dos contratos activos. Los scopes
con origen MSP sólo autorizan si proveedor y contrato coinciden con la relación
vigente; reactivar un permiso antiguo por un helper legacy no lo vuelve válido.

## Despliegue

Aplicar `migrations/20261009_provider_contracts.sql` como propietario de migración
antes de publicar la aplicación. Es una migración aditiva sin asignaciones reales.
La tabla es catálogo de autorización CORE, como MSPMembership: no está expuesta
como datos de tenant ni usa RLS. Las consultas públicas son exclusivas de GLOBAL,
filtradas por condominio. El runtime recibe SELECT/INSERT/UPDATE, no DELETE.
El historial se almacena independientemente del outbox para preservar reintentos
de cierres versionados. La recuperación conserva el historial y revoca scopes
según el procedimiento existente; no reactiva personal al reabrir el servicio.

Verificación automatizada: cambio de MSP, recontratación, JWT sintético reutilizado,
permisos locales/otros condominios intactos, asignación nueva, solicitudes antiguas,
fallo de auditoría y aperturas concurrentes en PostgreSQL.
