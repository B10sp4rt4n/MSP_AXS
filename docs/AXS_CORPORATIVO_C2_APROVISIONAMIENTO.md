# AXS Corporativo C2 — Aprovisionamiento reservado a Superadmin
**Fecha:** 2026-10-23 · **Estado:** PR draft, no productivo.

Dependencias obligatorias: [contrato PR #87](https://github.com/B10sp4rt4n/MSP_AXS/pull/87), [C0 PR #96](https://github.com/B10sp4rt4n/MSP_AXS/pull/96) y [C1 PR #97](https://github.com/B10sp4rt4n/MSP_AXS/pull/97).

## Flujo funcional
1. Superadmin de plataforma (autoridad activa `GLOBAL` en GOV, no `MSP_ADMIN` a secas) solicita el alta de una empresa. Debe existir un proveedor MSP y un usuario AXS que será el owner inicial. No crea usuario Clerk ni envía invitaciones.
2. El alta exige nombre, contacto de privacidad, URL HTTPS y versión del aviso. El cliente empresarial se crea con `corporativo_habilitado=false`, perfil propio y membresía owner, sin `Casa` ni `RESIDENTE` corporativo. El UUID `request_id` determina el tenant y permite reintentos sin duplicados; si la carga no coincide, HTTP 409.
3. Desde Superadmin se configuran dos capacidades/limitaciones por tenant: `max_sedes` (1–1000) y `max_destinos_por_sede` (1–2000). Quedan como políticas específicas AUP_GOV, nunca como valores por defecto de otra empresa ni como tarifas. No basta el rol owner para cambiarlas.
4. Se habilita **únicamente el directorio** de sedes/áreas por acción separada con confirmación explícita, comprobando aviso, contacto, owner activo y políticas con cuotas válidas. No habilita acceso de visitantes.
5. A partir de entonces el owner gestiona sedes/áreas dentro de su límite, sujeto además a sus permisos corporativos. El usuario GLOBAL no se convierte automáticamente en owner ni en anfitrión.

### APIs privadas
- `POST /plataforma/corporativo/empresas`: alta controlada, requiere UUID y datos de identidad corporativa.
- `PUT /plataforma/corporativo/empresas/{tenant_id}/capacidades`: cuotas AUP_GOV, reintentos idénticos sin duplicar.
- `POST /plataforma/corporativo/empresas/{tenant_id}/habilitar-directorio`: confirmación y validación de requisitos. No reactiva visitantes, fotos ni visitas canceladas.

## Separación técnica y autorización
- `AXS_CORPORATE_API_ENABLED` y `AXS_CORPORATE_PROVISIONING_ENABLED` se mantienen desactivadas por defecto. Ambos deben estar exactamente en `true`.
- `DATABASE_CORPORATE_PROVISIONING_URL` es una credencial **backend exclusivamente**, diferente del CORE ordinario. Ausente o con rol no conforme: HTTP 503 sin escritura. Nunca exponer URL, contraseña, token o cuenta en respuestas, eventos ni pruebas.
- `axs_corporate_provisioner` se crea con `NOLOGIN NOINHERIT NOBYPASSRLS`. Solo tras una decisión explícita posterior se le asignaría contraseña y `LOGIN` en un entorno controlado. Se conceden por columna la inserción del tenant y la habilitación, más inserts acotados de perfil, owner y outbox, sin DELETE ni DDL ni acceso de visitantes.
- La política RLS de C1 sigue siendo obligatoria en organizaciones/membresías y el contexto de tenant se fija por transacción. No alterar políticas o privilegios del rol `axs_core_app`.
- Se registra un evento CORE atómico con el alta y otro con la habilitación. Para cuotas GOV (base separada), se registra primero una *solicitud* en la outbox CORE, después el commit GOV, luego la *confirmación* en CORE. Los estados se distinguen para recuperación; no se declara atomicidad entre CORE y GOV. Un error entre commits requiere reconciliación supervisada.
- Las cuotas son capacidad comercial del **directorio**. No son autorización de entrada, ni están vinculadas a un sistema de cobros.

## Despliegue seguro (no ejecutado)
1. Validar el contrato y cerrar dependencias C0/C1 con CI y control de regresión residencial.
2. Probar SQL C2 `migrations/20261023_corporate_superadmin_c2.sql` en PostgreSQL local/descartable como propietario. Contiene `ALTER TABLE` aditivo, rol sin LOGIN y permisos mínimos. Verificar que una credencial de runtime no escribe membresías.
3. En una rama desechable de Neon, aplicar C0, C1, C2 en ese orden y validar permisos/RLS y reintentos. **No aplicar SQL a CORE productivo** sin revisión de DBA, orden de despliegue y aceptación del piloto.
4. Mantener los dos flags en false en todos los ambientes productivos. No configurar la URL segregada en Vercel/frontend.
5. Cuando se autorice operación real, designar operador, responsable de privacidad, versiones de avisos y pruebas de facultades, cuotas, RLS y auditoría. Activar primero en entorno de pruebas con empresa ficticia y owner de prueba.

## Límites pendientes
- El aviso y el contacto de empresa no demuestran por sí solos cumplimiento ARCO. Siguen pendientes los casos de acceso, rectificación, cancelación, oposición, bloqueo, supresión, retención de fotografías y recuperación de respaldos para visitantes y personal de empresa.
- No existe todavía la interfaz de Superadmin para esta operación ni se han verificado los avisos externos por HTTP. La API es la primera capa.
- No habilita mensajería, QR, entradas/salidas, biometría, hardware, recepción compartida ni piloto con datos reales.
- Sin revisión integral de rutas legacy ni verificación de Core/RLS con rol efectivo no se debe fusionar/desplegar.
