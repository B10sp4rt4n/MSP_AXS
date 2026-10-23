# AXS Corporativo — C1: empresa, sedes, destinos y alcance

**23 de octubre de 2026 · PR de desarrollo, no liberación productiva.**

Depende de [C0 PR #96](https://github.com/B10sp4rt4n/MSP_AXS/pull/96) y del [contrato funcional PR #87](https://github.com/B10sp4rt4n/MSP_AXS/pull/87). No fusionar C1 antes de la migración y aceptación de C0.

## Qué se implementó

- Perfil empresarial `corporate_organizations` vinculado por FK compuesta a una raíz técnica con `modalidad=corporativo`. El esquema físico sigue usando `condominios_exo` para no romper referencias históricas; **no se crean viviendas ni residentes corporativos**.
- Sedes `corporate_sites` y destinos `corporate_destinations` por tenant y sede, con claves foráneas compuestas.
- Miembros explícitos `corporate_memberships` (owner/admin/host/reception), asignados por sede en `corporate_site_assignments`. El campo global `Usuario.rol` nunca autoriza la operación corporativa.
- API privada `/corporativo/{tenant_id}/sedes` para consultar y crear sedes y `/corporativo/{tenant_id}/sedes/{site_id}/destinos` para consultar y crear destinos. Creaciones solo por miembro owner/admin, lecturas de host/recepción limitadas a sedes asignadas.
- Operaciones de alta y rechazo llevan auditoría; se evita enviar nombres de personas e imágenes al evento general.
- Las dependencias antiguas `set_tenant_context` y `require_tenant_context` no aceptan modalidad corporativa aunque el actor tenga scope residencial, pero deben continuar las auditorías del resto de vías legadas.

## Tres barreras necesarias

1. **Global:** `AXS_CORPORATE_API_ENABLED` debe estar exactamente en `true`. Ausente/falso responde 404.
2. **Por tenant:** la raíz debe estar marcada corporativa y `corporativo_habilitado=true`. Sin esa habilitación, responde 403 para un miembro autenticado.
3. **Por persona y sede:** membresía corporativa vigente, función suficiente y, para host/recepción, asignación activa en la sede. Ser superadmin/MSP o residente no crea automáticamente membresía empresarial.
4. **Gobierno de altas:** las acciones de creación necesitan política AUP_GOV de tenant y cupos suficientes; sin política o al exceder el máximo, se deniega y audita.

Por ahora **no existe endpoint de alta empresarial, activación comercial ni asignación de owner**. Esas operaciones deben llegar en un PR específico autorizado únicamente para superadmin, con trazabilidad y reglas GOV.

## Políticas SQL y despliegue

Migración `migrations/20261023_corporate_directory_c1.sql`: requiere primero `20261023_tenant_modalidad_c0.sql`. Se aplica solo por propietario del esquema, nunca por el rol de aplicación. Las cinco tablas fuerzan RLS con `app.tenant_id`; los datos de otra empresa no se ven ni se actualizan aun con SQL directo por el runtime. La FK fuerte impide que una compañía se refiera a un tenant residencial o que una asignación use sede o usuario de otra empresa.

Permisos propuestos para `axs_core_app`: SELECT en perfil, membresías y asignaciones; SELECT/INSERT/UPDATE en sedes y destinos. **Sin DELETE ni escritura de membresías/asignaciones**. El futuro aprovisionamiento por superadmin deberá usar un flujo con credencial mínima y separación explícita de autoridad, sin abrir un endpoint que entregue privilegios al owner.

La migración está **versionada, no ejecutada en CORE productivo**. Los tests con PostgreSQL desechable ejercitan el SQL real reejecutable y sus restricciones. La suite SQLite comprueba permisos de los handlers pero no representa aislamiento PostgreSQL.

## Pendientes antes de un piloto corporativo

- Flujo superadmin para empresa, asignación de owner, habilitación y creación/revocación de políticas GOV por plan/tenant. **Ya se evalúan** las acciones `crear_sede_corporativa` y `crear_destino_corporativo` contra políticas GOV del tenant y su cuota `max_count`, serializando altas por empresa/sede; en ausencia de política se rechazan. La API no crea ni habilita por sí misma esas políticas, por lo que sigue sin estar lista para habilitar comercialmente.
- Revisión total de rutas residenciales que no usan guards canónicos.
- Portal separado para owner, anfitrión y recepción, con mensajes propios.
- Invitación, decisión remota, entrada/salida, QR por sede, hora local y evidencia configurable.
- Privacidad: identificar responsable, aviso por tratamiento/sede, plazos, mínimo de captura, canal y expediente ARCO, bloqueo/supresión y restauración; el expediente asistido de San Luis no acredita aún un piloto corporativo.
- Integración de políticas GOV, pruebas integrales RLS/roles y recorrido manual de aceptación.
- Sin datos personales reales de visitantes ni activación de empresa hasta completar los controles anteriores.

## Criterio de salida de este PR

Compilación e importación correctas, tests de API y PostgreSQL aprobados, no-regresión residencial, bloqueo por feature flag y tenant, trazabilidad y revisión de mínimos privilegios. Mantener en draft hasta estas evidencias y aprobación de la dependencia C0.
