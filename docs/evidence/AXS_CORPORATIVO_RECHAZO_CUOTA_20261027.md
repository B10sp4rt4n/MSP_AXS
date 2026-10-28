# Rechazo de cupo y auditoría del sandbox

## Incidente comprobado

El 27 de octubre a las 21:59:36 UTC, el propietario intentó crear una tercera sede en la empresa de ensayo `corp_f9e6900162c24716964e5ac190d2960d`, limitada a dos. El backend rechazó la operación con motivo CORPORATE_DISABLED. La persistencia independiente del rechazo falló con ProgrammingError; el middleware devolvió 503 «Acceso rechazado; auditoría no disponible». La interfaz bloqueó nuevas altas por respuesta incierta.

La consulta autorizada al CORE confirmó exactamente dos sedes (Oficina Central y Sucursal Norte) y un destino (Recepción). No se creó la tercera sede. El rechazo fallido no se recrea como si hubiese sido auditado originalmente.

## Causa y cambio acotado

La política `sandbox_security_outbox` omitía tres motivos ya admitidos por el backend: INVALID_CREDENTIALS, TENANT_MODE_DENIED y CORPORATE_DISABLED. Se amplía únicamente ese enum. Se conservan el dominio PLATFORM_SECURITY, correspondencia de event_uid, acción/resultado de denegación y entidades session/scope. No se conceden privilegios SQL adicionales ni se cambia la cuota.

La migración `20261027_corporate_sandbox_security_reasons.sql` incluye precondiciones de base, inspector, run UUID, certificado vigente y catálogo completo esperado. Bloquea las tablas durante la transacción, compara el catálogo completo antes y después y solo admite el delta ensayado. Actualiza únicamente catalog_hash de la atestación existente; conserva run_id, certified_at y expires_at. No ejecuta certify_empty, no vuelve a afirmar que la base esté vacía ni prolonga la vigencia.

- CORE antes: `9a4132bc1fa2489c84df6641908bfe9680398a94c9192d5542abab2b0a2a53fe`.
- CORE después: `2ff44c18b5930ceeda0f759891f173045e298277166ed8a8458a5c42ea71615e`.
- Vigencia original conservada: 2026-10-27 17:54:09.117026 UTC a 2026-10-28 17:54:09.117026 UTC.

También se corrige el SQL de permisos para futuros sandboxes vacíos; ese script completo NO se vuelve a aplicar al ensayo poblado. GOV y EVENT no cambian de catálogo, certificado ni cuota. No hay cambios en backend/frontend ni es necesario reiniciar Railway.

## Ensayo antes de aplicar

Copia aislada `br-long-bar-b5blo81e`, padre `br-soft-leaf-b59xcclw`, dentro de MSP_AXS. El hash del padre coincide con el certificado inicial. La comparación de nueve secciones de catálogo muestra como única diferencia el WITH CHECK de sandbox_security_outbox.

- Migración completa aprobada en la copia con datos: dos sedes y un destino conservados; timestamps de certificado idénticos.
- Inserciones de los tres motivos aprobadas conectando como `axs_corp_sandbox_core`.
- Motivo desconocido rechazado por RLS. Todas las inserciones de prueba se revierten mediante savepoints; quedan cero filas sintéticas de prueba.
- Reejecución de la migración rechazada por precondición, sin sobrescribir la atestación.
- El primer ensayo falló al comparar timestamps redondeados a milisegundos; rollback completo. La migración conserva y compara la precisión real de microsegundos.

La aplicación al sandbox activo y la repetición del rechazo desde la sesión real se registrarán por separado. Producción, main, San Luis y bases legadas fuera del alcance.
