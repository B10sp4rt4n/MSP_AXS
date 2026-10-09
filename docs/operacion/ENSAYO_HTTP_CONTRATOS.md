# Dos ciclos contractuales por HTTP en desarrollo

Este ensayo complementa las regresiones de #39 y el navegador con transporte
simulado de #40. Ejecuta peticiones HTTPS reales contra el backend de desarrollo,
con PostgreSQL CORE/GOV/EVENT y su outbox real. No utiliza Clerk ni acredita la
integración de sesión Clerk → panel Next → API. Producción permanece retenida.

## Destinos permitidos

- Railway: proyecto **AXS Development** `c04faff4-37ba-4df4-a6ce-a4d5d5ff881b`;
  environment `5f5b4e0c-c4ce-457c-96a4-b65ebf723354`. Su nombre es `production`,
  pero pertenece al proyecto separado de desarrollo.
- API fija: `https://axs-development-backend-production.up.railway.app`.
- Neon: proyecto `patient-tree-68362559`, rama `br-blue-frog-b5o2ccsk`, endpoint
  `ep-withered-resonance-b59tusv3`; CORE `neondb`, GOV `aup_gov`, EVENT `aup_event`.
- Backend ensayado: `b349cb9bdd88707615314bb6c79b27aa0e95a8ff`, deployment
  `d44e11a5-ec37-4cca-80a1-43675f1be9e5`. No requiere otro despliegue del backend.

## Preparación reproducible

1. Verificar los IDs de proyecto/rama/servicio; nunca usar destinos por defecto.
2. Ejecutar `scripts/development_contract_cycles_core.sql` en una transacción CORE.
   Crea sólo fixtures `lab261009_cycles_v1_*`: proveedor, dos condominios, cuatro
   identidades sin contraseña/Clerk, permisos locales, visita y evidencia ficticias.
   No usar `ON CONFLICT` ni reactivar fixtures existentes: una colisión aborta.
3. Registrar antes del ensayo los digest de la visita/evidencia con
   `scripts/development_contract_cycles_verify.sql`. Son comparaciones de filas,
   no una prueba criptográfica sobre el contenido de un archivo externo.
4. Crear una Railway Function con `scripts/development_contract_cycles.ts`, sin
   dominio, listener ni cron. Sin secreto imprime WAITING y no realiza peticiones.
   Configurar `restartPolicyType=NEVER` antes de iniciar la ejecución autenticada.
5. Ejecutar `scripts/development_contract_cycles_gov.sql` únicamente en GOV de
   desarrollo. Crea una autoridad GLOBAL temporal para el operador **sintético**.
6. Configurar únicamente en el runner `APP_ENV=development`,
   `NEON_DEV_ENDPOINT=ep-withered-resonance-b59tusv3` y
   `AXS_TEST_SECRET=${{axs-development-backend.SECRET_KEY}}`. Railway resuelve la
   referencia dentro del proceso. No leer, copiar ni registrar el secreto/JWT.

El runner firma un JWT local por identidad, válido cinco minutos, y reutiliza
exactamente ese token durante toda la ejecución. Tiene un plazo global de cuatro
minutos, timeout por petición de 30 segundos, origen fijo y rechaza redirecciones.
No reintenta automáticamente operaciones. Un fallo parcial exige inspección; no
se reinicia con los mismos datos. Para otra ejecución, crear otro conjunto de
fixtures con prefijo y UUID nuevos en todos los archivos, conservando el anterior.

## Criterios funcionales

- Operador sin autoridad (administrador local): historial denegado 403.
- Apertura C1 versión 1; mismo UUID devuelve el mismo evento. C2 con C1 abierto: 409.
- Abrir contrato no concede permisos. Dos guardias reciben scopes nuevos en C1.
- Baja sin contrato esperado: 409. Baja C1 revoca ambos y conserva permiso local.
- Mismo JWT: guardias 200 antes de baja, 403 después, aun tras abrir C2.
- C2 versión 2 para el mismo MSP. Repetir baja C1 devuelve su comprobante original
  y deja C2 abierto. Otorgar personal sobre C1 cerrado: 409.
- Sólo un guardia recibe scope nuevo en C2: obtiene 200, el otro mantiene 403.
- Baja C2 revoca únicamente su scope. Reintentos no crean eventos adicionales.
- Intentar abrir otra vez C1 devuelve historia cerrada, no lo reactiva.
- Final: dos contratos cerrados, tres scopes de proveedor revocados, permiso local
  activo y permiso del guardia en el condominio de control intacto.
- Verificación SQL: siete eventos únicos (2 aperturas, 3 permisos, 2 bajas), cada
  uno entregado una vez a EVENT; correspondencia por `event_uid` y contenido.
  Visita y evidencia con los mismos digest antes/después.

## Verificación y cierre del ensayo

Exigir `AXS_CYCLES_RESULT` con `status=PASS`; el estado SUCCESS de Railway o código
de salida cero no basta (FAIL sale cero para impedir reinicios de escrituras).
Ejecutar `development_contract_cycles_verify.sql` en transacción CORE y consultar
EVENT con `SELECT * FROM events_aup WHERE tenant_id='lab261009_cycles_v1_condo'
AND accion IN ('abrir_contrato','otorgar_permiso_contrato','baja_proveedor')`.
Comparar por UID todos los campos del payload, no sólo el total. Si outbox tiene
pendientes, esperar un ciclo del worker y repetir lectura, sin repetir mutaciones.

Siempre al terminar, incluso ante FAIL:

- Vaciar `AXS_TEST_SECRET` **sólo en el runner**, con `skipDeploys=true`.
- Revocar sólo su autoridad sintética en GOV:

```sql
UPDATE authorities_gov SET estado='REVOCADO', revoked_at=now()
WHERE authority_id='lab261009_cycles_v1_authority'
  AND identity_id='lab261009_cycles_v1_operator'
  AND metadata_json->>'run'='lab261009_cycles_v1' AND estado='ACTIVO';
```

Conservar fixtures e historial para revisión. No borrar eventos ni cambiar
autorizaciones heredadas de la rama. Las identidades sintéticas no tienen login
Clerk ni contraseña. La autoridad temporal debe quedar REVOCADO; los JWT caducan.

La limitación funcional encontrada en #37 ya fue corregida por #38. Este PR añade
un ensayo conectado y evidencia, no otra implementación del modelo contractual.
No fusionar a main: Railway de producción despliega esa rama automáticamente.

## Resultado ejecutado — 2026-10-09

- Runner `ef5a55db-f043-4ace-8475-6d74b69cee62`, deployment
  `9c507348-831b-484c-afa3-e254f5732ae8`: **PASS, 40 peticiones HTTP**,
  de 19:12:11 a 19:12:41 UTC (13:12 en Ciudad de México).
- Contratos `f8e30960-7c68-42ae-a87c-d7c328da8601` y
  `f8e30960-7c68-42ae-a87c-d7c328da8602`, versiones 1 y 2, cerrados.
- Scopes 27 y 28 revocados por C1; scope nuevo 29 revocado por C2.
  Scope local 25 y control 26 permanecen activos.
- Siete eventos únicos confirmados en CORE y EVENT. Comparación campo por campo
  y recálculo de SHA-256 aprobados; una entrega por evento, sin error pendiente.
  El hash de sesión del operador es el mismo en los siete eventos.
- Digest de visita antes/después: `560c797ac232c5d3a4212cad2bac5f86`;
  evidencia: `a9a75011050aa4796ff0f09451c11cdf`.
- Autoridad temporal revocada a las 19:13:26 UTC; variable del secreto del runner
  vaciada. No se modificó el secreto del backend.
- TypeScript del runner validado localmente con `tsc --noEmit` (módulo ESNext,
  resolución bundler). Bun 1.4.0 ejecutó el archivo real en Railway.

Evidencia capturada sin credenciales:
`docs/operacion/evidencias/contract-cycles-20261009.json`.
Verificación offline reproducible, sin acceder a ningún ambiente:

```sh
python scripts/verify_contract_cycles_evidence.py
```

El verificador confirma la consistencia de la captura; no vuelve a ejecutar el
backend ni certifica que su estado futuro sea idéntico. La evidencia de ejecución
es el log del runner y la lectura posterior de las tres bases de desarrollo.
No se ejecutaron aquí concurrencia, fallos de transacción ni autenticación Clerk:
las primeras cuentan con regresiones de backend separadas; Clerk + UI + API sigue
pendiente de una sesión integrada de prueba. Ningún PR fue fusionado.
