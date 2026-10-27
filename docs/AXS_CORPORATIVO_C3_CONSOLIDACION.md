# AXS Corporativo C3 — consolidación de consola Superadmin (2026-10-23)

**Decisión técnica:** la implementación canónica es [PR #100](https://github.com/B10sp4rt4n/MSP_AXS/pull/100), con base en C2 [#98](https://github.com/B10sp4rt4n/MSP_AXS/pull/98). [PR #99](https://github.com/B10sp4rt4n/MSP_AXS/pull/99) queda sustituido, sin fusión. Ambos estaban en draft y C0 [#96](https://github.com/B10sp4rt4n/MSP_AXS/pull/96), C1 [#97](https://github.com/B10sp4rt4n/MSP_AXS/pull/97) y C2 [#98](https://github.com/B10sp4rt4n/MSP_AXS/pull/98) siguen sujetos a revisión.

## Matriz comparativa (código observado)

| Aspecto | PR #99 (alternativa) | PR #100 (canónico) | Resolución |
| --- | --- | --- | --- |
| Base Git | `main`, incluye cambios C0–C2 en 69 commits | Rama C2, 17 commits al inicio de la revisión | Conservar base C2 sin adelantar dependencias |
| UI | `/dashboard/corporativo/plataforma` | `/dashboard/corporativo-superadmin` | Mantener exclusivamente la ruta del #100 |
| Autorización | Layout SSR con Clerk y GET de autoridad GLOBAL | Página Clerk y comprobación en cliente | Incorporado guard SSR en la ruta del #100, además de validación backend por operación |
| Retomar altas | GET de empresa por ID; lectura de cuotas/estado | Wizard lineal | Incorporado GET y acción de reanudar por ID corporativo |
| Verificar owner | GET privado del usuario existente | Campo de ID sin verificación preliminar | Incorporada comprobación del owner antes del alta |
| Idempotencia | UUID persistente durante reintentos; formulario bloqueado | UUID persistente ante respuesta incierta | Se congela el formulario tras intento y se conserva el UUID hasta reinicio explícito |
| Cuotas GOV | Reconsulta posterior a escritura | Avance al siguiente paso después de PUT | Se verifica lectura GOV tras el PUT antes de permitir habilitación |
| Privacidad HTTP | Cache-Control: private, no-store | No constaba para todas las respuestas del router | Incorporado no-store y GET sin enumeración |
| Evidencia aislada | Pruebas sintéticas SSR/Chromium/API | 90 PostgreSQL, pruebas Python/navegador, ensayo Neon C0–C2 y sandbox sin desplegar (según PR) | Se mantienen evidencias y pruebas de #100, se añaden controles #99 |
| Entornos | No desplegado | Neon aislado; Railway staged-create sin backend operativo | Ningún flag o credencial productiva se activa |

## Contrato que sigue vigente

1. **GLOBAL:** solamente una autoridad `GLOBAL` activa en AUP_GOV permite entrar y mutar. No basta `MSP_ADMIN`; backend vuelve a verificar cada GET/POST/PUT. Guard de servidor falla cerrado sin sesión/token/GOV/flag.
2. **Aislamiento:** solo `corp_[0-9a-f]{32}` y modalidad corporativa para lectura de empresa; RLS y rol provisioner restringido de C0–C2. No crear `Casa`, asignar residentes ficticios, mostrar empresas como condominios ni conferir rol owner por ser GLOBAL.
3. **Idempotencia:** `request_id` UUID define unívocamente empresa; mismo UUID + distinto payload debe ser 409. Se prohíbe cambiar campos tras envío incierto; el operador puede consultar ID antes de decidir un reintento.
4. **GOV:** cuotas por empresa (1–1000 sedes, 1–2000 destinos por sede), con política AUP_GOV tenant específica y comprobación de lectura. Commit GOV y outbox CORE **no son una única transacción**; falta conciliador automático.
5. **ARCO:** contacto, versión y URL HTTPS del aviso son **datos mínimos**, no cumplimiento ARCO integral. La separación por modalidad conserva las facultades ARCO existentes; deben revisarse titular/responsable, derechos y procedimientos de acceso, rectificación, cancelación y oposición, revocación, exportación, retención/borrado y evidencias corporativas antes de pilotos con datos reales.
6. **Residencial:** el listado, conteos y gestión de condominios mantienen ámbito residencial; pruebas de regresión sobre residentes/guardia/visitas, solicitudes, ARCO y RLS deben seguir pasando.

## Evidencia y pruebas de esta consolidación

- `tests/test_corporate_superadmin.py`: negativa sin GLOBAL, lectura protegida de owner, empresa, cuotas y cabeceras no-store, idempotencia, activación escalonada, cero casas, auditoría.
- `frontend-next/tests/corporate-superadmin-gate.test.cjs`: guard SSR sin Clerk, sin token, sin GLOBAL y API caída, todos con formulario oculto.
- `frontend-next/tests/corporate-superadmin.browser.cjs`: transporte de red sintético, owner previo, mismo UUID tras ACK incierto, cuotas consultadas, recuperación por ID, activación explícita y anchos 320/360/1280.
- PostgreSQL descartable: `.github/workflows/postgres-rls.yml` conserva RLS, FK, roles, aislamiento y pruebas corporativas/residenciales; `.github/workflows/tests.yml` incluye TypeScript, Python, roles y navegador.
- **Los resultados de CI del último SHA deben revisarse; los éxitos históricos de #100 no certifican automáticamente estos nuevos commits.** El ensayo Neon anterior no equivale a un despliegue ni valida credenciales LOGIN reales.

## Bloqueos de liberación

- Mantener **draft** y dependencia lineal **C0 #96 → C1 #97 → C2 #98 → C3 #100**. No apuntar C3 a main mientras las otras estén en draft.
- Cerrar inventario de rutas legacy fuera de guards, RLS con rol no-bypass, validación interempresa/inter-MSP y regresiones residenciales.
- Completar y revisar documental/operativamente ARCO corporativo; no habilitar accesos físicos, visitantes, QR, fotos, Alexa ni biometría por implicación de la consola.
- Acordar procedimiento de conciliación CORE ↔ GOV ante resultados inciertos y comprobar rollback/auditoría.
- Correr CI sobre el último commit y aprobar de forma explícita migraciones y despliegues **después** de cumplir los bloqueos. `AXS_CORPORATE_API_ENABLED` y `AXS_CORPORATE_PROVISIONING_ENABLED` siguen apagados por defecto. No cargar secretos ni habilitar provisioner LOGIN productivo.

**Estado:** revisión/consolidación de código en branch; NO implica aprobación de merge, piloto o producción.
