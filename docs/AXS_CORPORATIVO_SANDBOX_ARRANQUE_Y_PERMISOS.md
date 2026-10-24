# Sandbox corporativo: vaciedad inicial, arranque y permisos

Estado: implementación propuesta en C3, sin aplicación remota, LOGIN ni despliegue.
Esta especificación sustituye el bloqueo de «base vacía en cada arranque» del
inventario del 24 de octubre; el inventario remoto conserva su fecha y alcance.

## Dos operaciones distintas

1. **Certificación inicial offline**: después de revisar y aplicar manualmente C4
   y los tres SQL de permisos, el propietario verifica todas las tablas de cada
   base, con visibilidad completa y bloqueos hasta finalizar su transacción.
   Si hay una sola fila —incluida una constancia previa— se rechaza. Registra
   UUID compartido del ensayo, dominio, base, issuer Clerk, fecha, vencimiento
   de 24 horas y huella del catálogo. No imprime filas ni credenciales.
2. **Arranque runtime**: las cuatro conexiones segregadas comprueban su rol/base,
   permisos efectivos de tabla, columna, secuencia y función, ausencia de
   propiedad/membresías/DDL, FORCE RLS y constancia coincidente. Compara la huella
   del catálogo; rechaza permisos, columnas o políticas cambiadas. Acepta filas
   sintéticas posteriores y no ejecuta `create_all` ni migraciones.

La constancia acredita **vaciedad inicial y contrato de arranque**, no anonimato
permanente, funcionamiento de Clerk ni cumplimiento ARCO. El vencimiento se
comprueba al arrancar; no programa la terminación de un proceso ya iniciado.
La siembra posterior debe ser offline, sintética, revisada y sin datos de clientes.
No se certifica una copia poblada aunque sus filas estén ocultas por RLS.

La certificación no es atómica entre las tres bases. Una aplicación parcial,
constancia ausente o UUID diferente bloquea runtime: inspeccionar cada base,
no reintentar ni regenerar certificados por fuerza. Una vez poblada la base no
se vuelve a certificar con este comando; preparar otras bases limpias mediante
un cambio revisado si se necesita otro ensayo.

## SQL concreto, de una sola aplicación

- `migrations/20261024_corporate_sandbox_core_permissions.sql`
- `migrations/20261024_corporate_sandbox_gov_permissions.sql`
- `migrations/20261024_corporate_sandbox_event_permissions.sql`

Cada archivo exige su nombre exacto de base y mantiene roles NOLOGIN,
NOINHERIT, sin BYPASSRLS ni propiedad. No crea contraseñas. CORE requiere el
journal de `20261023_corporate_reconciliation_c4.sql` previamente revisado;
no repetir el bootstrap de las tablas existentes ni C1 sobre bases heredadas.
No se aplica este SQL a `neondb`, `aup_gov`, `aup_event` ni producción.

| Rol | Acceso permitido | Límite principal |
| --- | --- | --- |
| `axs_corp_sandbox_core` | Catálogo sintético de identidades/MSP/raíces corporativas; lectura de membresías; escritura de sedes, destinos, casos ARCO y outboxes | No escribe usuarios, membresías, raíz, visitas ni evidencias; los scopes/MSP/contratos legados devuelven cero mediante RLS |
| `axs_corporate_provisioner` | Alta corporativa, owner, habilitación y conciliación C4; INSERT en outbox operativo | Actualiza solo habilitación y campos de confirmación, no payload C4 ni outbox; sin DELETE |
| `axs_corp_sandbox_gov` | Lee autoridad preinscrita; crea y actualiza cuotas de directorio del tenant en contexto | No concede autoridades ni políticas GLOBAL; no cambia identidad/acción de una cuota existente |
| `axs_corp_sandbox_event` | SELECT/INSERT por tenant para entrega idempotente | Append-only: sin UPDATE/DELETE; seguridad usa dominio explícito `PLATFORM_SECURITY` |

Los outboxes permiten UPDATE únicamente de `delivered_at`, `attempts`,
`next_attempt_at` y `last_error`; no de hechos o identidad. Ningún rol puede
escribir o borrar su constancia, delegar permisos o crear objetos.

CORE usa una función SECURITY DEFINER que **solo adquiere un bloqueo de fila**
sobre raíz corporativa y retorna void. No retorna registros ni ejecuta SQL
dinámico; usa identificadores calificados y search_path fijo. EXECUTE está
revocado a PUBLIC. Evita conceder UPDATE de raíz a la aplicación para satisfacer
`SELECT FOR UPDATE`. El provisioner comparte el mismo bloqueo de fila.

## Secuencia operativa pendiente de aprobación

1. Confirmar las tres bases frescas del endpoint `ep-bitter-snow-b5sgxc4h`.
2. Revisar/aplicar C4 y el SQL de permisos de cada dominio como propietario.
3. Certificar **antes de sembrar**, en un proceso offline distinto del servicio:

```bash
python -m scripts.corporate_sandbox_attestation --certify-empty \
  --run-id UUID_DEL_ENSAYO --clerk-issuer https://INSTANCIA.clerk.accounts.dev
```

El comando usa únicamente `AXS_CORPORATE_BOOTSTRAP_CORE_URL`,
`AXS_CORPORATE_BOOTSTRAP_GOV_URL` y `AXS_CORPORATE_BOOTSTRAP_EVENT_URL`, con
`neondb_owner`, TLS y destino exacto. Nunca poner estas variables en Railway.
Los secretos se suministran por un canal seguro, no en argumentos ni documentos.

4. Sembrar fuera de runtime identidades y autoridad sintéticas con subjects Clerk
   exactos. No existe autovinculación por correo ni aceptación de JWT local en
   sandbox. No se añaden usuarios mediante webhook o API con el rol runtime.
5. Habilitar LOGIN y crear credenciales segregadas solo mediante otra operación
   revisada. El rol legado `axs_core_app` no se reutiliza.
6. Configurar `AXS_CORPORATE_SANDBOX_PHASE=runtime`, UUID en
   `AXS_CORPORATE_SANDBOX_RUN_ID`, `CLERK_JWT_ISSUER` idéntico al del certificado,
   publishable key `pk_test_` que decodifique a ese host y secret key `sk_test_`.
   Se rechaza `CLERK_JWT_PUBLIC_KEY` alternativa; JWKS procede de esa instancia.
   `ALLOWED_ORIGINS` exige orígenes HTTPS explícitos. TESTING y credenciales de
   propietario están prohibidos. Alexa, fotos y retención permanecen cerrados.
7. CORE y su alias usan `axs_corp_sandbox_core`; GOV/EVENT sus roles dedicados;
   `DATABASE_CORPORATE_PROVISIONING_URL` usa el provisioner. Todos los URLs
   requieren host/base exactos y TLS. Las tres banderas de corporativo,
   aprovisionamiento y casos ARCO son true únicamente en fase runtime explícita.
8. Sustituir el predeploy staged por:

```bash
python scripts/check_corporate_sandbox_config.py && python scripts/check_corporate_sandbox_data.py
```

No agregar `check_core_rls.py`: su contrato residencial requiere CRUD sobre
visitas, casetas y evidencias. El nuevo gate valida el contrato corporativo real.
La fase omitida/`closed` conserva las banderas cerradas y la comprobación de
vaciedad; nunca habilita el ensayo automáticamente.

Faltan la aplicación remota revisada, siembra, credenciales, frontend aislado y
sesión Clerk real para ejecutar la matriz HTTP del inventario. CI usa PostgreSQL
local descartable y `SET ROLE` sobre roles NOLOGIN; no demuestra LOGIN con
contraseña, conectividad Neon, despliegue Railway ni autenticación Clerk real.
