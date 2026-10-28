# AXS Corporativo: cierre del ensayo y revisión de integración

Las secciones 1–5 conservan el corte de revisión inicial. La sección 6 registra la integración técnica posterior y sustituye los pendientes I1/I2 en lo que corresponde al código; el resultado final de CI se registra en el PR para no cambiar el SHA que se valida.

Corte: 27 de octubre de 2026, hora de Ciudad de México. Repositorio: B10sp4rt4n/MSP_AXS.
Alcance: sandbox corporativo con identidades Clerk Development, dos empresas de ensayo y un expediente ficticio. Revisión de dependencias, diferencias relevantes y CI; no constituye aprobación de todas las líneas de código ni autorización de producción.

## Dictamen

**El recorrido ensayado pasó. La cadena sigue en borrador y no está lista para fusionarse como paquete final.**

El directorio corporativo, las cuotas configuradas, los rechazos de creación cruzada de sedes y el registro asistido ARCO funcionaron en el sandbox. La revocación ARCO de A conservó el directorio y bloqueó la consulta privada con el mismo token. Tras restaurarla, la captura final confirmó Empresa A y su expediente cerrado.

Antes de integrar hay que reunir el último ajuste UX de #102 con el SQL de #103 en un head común, ejecutar CI sobre ese resultado y resolver la incorporación del contrato #87 y la auditoría #95. No se necesitan más altas manuales para demostrar otra vez lo ya ensayado.

## 1. Evidencia y límites

Se distinguen tres tipos de evidencia:
- **Interfaz:** capturas y resultados aportados por Salvador durante la sesión.
- **HTTP real:** bloques ejecutados por Salvador en su navegador con sesiones Clerk Development, validación previa del subject esperado y consulta propia antes de la petición cruzada. El asistente no recibió tokens.
- **Persistencia/CI:** lecturas y pruebas SQL con el conector Neon; estados y jobs de GitHub Actions recuperados del proveedor.

Las capturas originales permanecen en la conversación. Este documento consolida sus resultados; no publica capturas, correos, claves ni tokens y no es un paquete de custodia forense.

| Prueba | Evidencia observada | Resultado y alcance |
|---|---|---|
| Empresa A y Empresa B | Alta Superadmin, owner distinto, confirmación CORE/GOV, habilitación | Dos empresas de ensayo habilitadas para directorio |
| Propietario igual a Superadmin | Primer intento B rechazado; lectura CORE confirmó ausencia de empresa | Protección aplicada; el identificador del intento no acreditaba un alta |
| Persistencia del directorio A | Recarga y selección de sede | Dos sedes; Recepción pertenece a Oficina Central |
| Separación de sedes | Sucursal Norte sin destinos | No se mezcló Recepción con la segunda sede |
| Cuota de 2 sedes | Intento de tercera sede, auditoría corregida y aviso UX | Rechazo; dos sedes siguen visibles |
| Consulta de directorio A→B y B→A | Portal rechaza ambos accesos y retira formularios/datos | Consulta cruzada denegada; retorno a A conserva sus registros |
| Creación de sede A→B y B→A | POST real, tras GET propio 200 y subject esperado | Ambos 403: "Sin membresia corporativa vigente" |
| RLS de escritura | LOGIN axs_corp_sandbox_core, sin SUPERUSER/BYPASSRLS, INSERT concedido | Cuatro rechazos 42501: sede A→B, sede B→A, destino B→A y caso ARCO B→A |
| ARCO de A | Alta ficticia y cuatro avances | recibida→verificada→resuelta→ejecutando→cerrada; versión final 5 |
| Cierre ARCO con pendientes | Intento con 1 pendiente y constancia ficticia | Rechazo; conserva ejecutando/1; cierre posterior aceptado con 0 |
| Panel ARCO B | Empresa B seleccionada sin expedientes | No muestra el expediente de A |
| Consulta ARCO B→A por API | GET real a /arco/<A> | 403 por falta de membresía |
| Cambio de estado ARCO B→A | POST real con folio y versión 5 de A | 403 por membresía antes de validar la transición; no acredita otras operaciones |
| Revocación ARCO de A | Se retiró solo su designación; sesión conservada | Selector sin clientes y sin formularios |
| Revocación por HTTP | Un token para GET directorio A y GET ARCO A | Directorio 200 / 2 registros; ARCO 403: "Requiere designación de privacidad para este cliente" |
| Restauración de designación A | Despliegue SUCCESS y captura final del panel | Vuelve Empresa A y el mismo caso cerrado/0 |
| Conservación final | Lecturas CORE anteriores y posteriores a los intentos | 2 sedes, 1 destino, 1 caso cerrado versión 5; dos memberships owner activas |

La primera ejecución del conjunto SQL revirtió por usar el identificador reservado right sin comillas; la ejecución corregida pasó. Las pruebas usan subtransacciones y abortan si una escritura inesperadamente se acepta. Se verificaron cero filas residuales de esas sondas.

Las pruebas RLS cambian el contexto de tenant de la cuenta SQL y demuestran esa capa. No sustituyen el guard de membresía de la API, que establece el contexto del tenant solicitado. Los POST autenticados se comprobaron por separado.

**No demostrado por este ensayo:** todas las rutas; ARCO A→B por HTTP; POST ARCO tras revocar designación; revocación de membership con sesión real; concurrencia bajo carga real; operaciones corporativas de visitantes, QR, fotos, hardware o voz. Los ensayos sintéticos de CI cubren otros casos, sin convertirlos en evidencia operativa real.

## 2. Estado final del sandbox

| Elemento | Estado al cierre |
|---|---|
| Empresa A | corp_f9e6900162c24716964e5ac190d2960d; owner axs_corp_sbx_owner_a; 2 sedes y 10 destinos por sede |
| Empresa B | corp_cbf1b8df457d43d0bef55ec0d7deb6e6; owner axs_corp_sbx_owner_b; 1 sede y 2 destinos por sede |
| Expediente ficticio | 3e74dbee-2d8e-49d4-bd7c-f9464999288c; ENSAYO_ARCO_A_001; acceso; cerrado, versión 5, sin pendientes |
| Designaciones ARCO | Owner A solo para A; owner B solo para B; GLOBAL no designado |
| Frontend activo | 3ba15f70ec890544e95bd50438f5a6b03c34b878; despliegue bc92e94c-9251-482d-bd4e-493c445f5142 SUCCESS |
| API activa | df428926ef3f48a3572e13da387f050c49c067cf; restauración 78c9d9fe-e09a-4f5a-b6d2-9dceb0401de6 SUCCESS y healthcheck 200 |
| SQL aplicado | Corrección RLS de #103 ya aplicada al CORE del sandbox; no confundir su aplicación con merge Git |
| Constancia inicial | Vence para nuevos arranques el 28/10/2026 a las 11:54:09 CDMX; no se renovó ni se volvió a certificar vaciedad |
| Producción y main | No cambiados por este ensayo ni por esta revisión |

La revocación temporal se publicó en a4dcd3ba-bddf-4b0c-b591-1ecceed59e2c; se retiró A y se conservó B. La restauración siguiente repuso ambos pares. No se cambiaron las memberships para simular la revocación de privacidad.

## 3. PR, dependencia y CI por SHA

Los SHA corresponden al código revisado antes de añadir este documento. Una adición documental posterior no acredita CI del nuevo head por sí sola.

| PR | Base | Head revisado | Workflows recuperados | Estado |
|---|---|---|---|---|
| [#96 C0](https://github.com/B10sp4rt4n/MSP_AXS/pull/96) | main | 2267ee1268ae96dd301e1e5379e94407bc216d80 | [Tests 40060740206](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40060740206), [PG 40060740216](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40060740216): SUCCESS | Draft, mergeable |
| [#97 C1](https://github.com/B10sp4rt4n/MSP_AXS/pull/97) | C0 | 1ba0bae0eba9b766fea2de497c670acef2875ca0 | [Tests 40061762604](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40061762604), [PG 40061762585](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40061762585): SUCCESS | Draft, mergeable |
| [#98 C2](https://github.com/B10sp4rt4n/MSP_AXS/pull/98) | C1 | 9e6c885b15fd62770d8d6bb4d203d4fafbfe8276 | [Tests 40061774149](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40061774149), [PG 40061774180](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40061774180): SUCCESS | Draft, mergeable |
| [#100 C3/C4](https://github.com/B10sp4rt4n/MSP_AXS/pull/100) | C2 | df428926ef3f48a3572e13da387f050c49c067cf | [Tests 40565686406](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40565686406), [PG 40565686586](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40565686586): SUCCESS | Draft, mergeable |
| [#102 C5](https://github.com/B10sp4rt4n/MSP_AXS/pull/102) | C3 | 3ba15f70ec890544e95bd50438f5a6b03c34b878 | [Tests 40595484278](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/40595484278): SUCCESS; sin run PG en este SHA | Draft, mergeable |
| [#103 SQL sandbox](https://github.com/B10sp4rt4n/MSP_AXS/pull/103) | C5 | 4d6eed96e49bfbb6d1081137ab8e4b8d55801abf | Sin workflow runs encontrados para este SHA | Draft, mergeable; falta head común y CI |

GitHub compare confirmó ancestry sin divergencia en main→C0→C1→C2→C3→C5. Main observado: 76bc9d619836f0872241741570fb7974e51d2bf6. El resultado mergeable solo informa ausencia de conflicto calculado por GitHub, no aprobación técnica.

Se consultaron las revisiones de los seis PR: no hay revisiones registradas al corte. No se presentó una aprobación formal ni se marcaron ready. Las cifras de tests descritas en cada PR son históricas de sus ejecuciones; aquí se verificó el estado de runs y, para C3/C5, también sus jobs.

## 4. Hallazgos concretos para integración

### I1 — #103 no reúne el último UX de #102

[Compare C5 vs SQL](https://github.com/B10sp4rt4n/MSP_AXS/compare/3ba15f70ec890544e95bd50438f5a6b03c34b878...4d6eed96e49bfbb6d1081137ab8e4b8d55801abf): diverged, ahead 1 / behind 1; base común 3c7397b1a35e48631e003ff7af8bf5e88bc34e35.

El SQL agrega tres motivos de seguridad al bootstrap y una migración guardada para el sandbox poblado; el commit C5 posterior aclara la cuota y conserva la vista autorizada. En los heads revisados no existe aún una punta que contenga ambos cambios. Esto no implica que fusionar #103 sobre C5 borre automáticamente el UX: una integración correcta conserva ambos. Falta ejecutar y probar ese resultado conjunto.

**Salida exigida:** sincronizar la rama de #103 con el C5 vigente, comprobar que conserva los dos deltas y probar el head resultante antes de su integración final.

### I2 — Los filtros de CI omiten la rama correctiva

En los workflows de #103:
- tests.yml: push solo main, develop, feature/* y feat/axs-corporativo-c[1235]-*; pull_request solo main/develop; sin workflow_dispatch.
- postgres-rls.yml: push solo feat/axs-corporativo-c[123]-*; pull_request solo main; sí declara workflow_dispatch.

La rama fix/axs-corporativo-sandbox-auditoria-20261027 y su PR dirigido a C5 no coinciden con esos filtros. C5 tampoco coincide con el push de PG. La ausencia de run no es una prueba fallida ni una aprobación heredada.

**Salida exigida:** habilitar una vía de CI para la rama correctiva y el head combinado (Tests + PG RLS), ejecutarla y comprobar el SHA exacto. El conector disponible no ofrece dispatch de workflow; no se lanzó un job por un mecanismo alternativo ni se modificaron workflows en esta revisión.

### I3 — Contrato y auditoría documentales aún fuera de la cadena

[#87](https://github.com/B10sp4rt4n/MSP_AXS/pull/87) y [#95](https://github.com/B10sp4rt4n/MSP_AXS/pull/95) siguen abiertos y draft. El árbol C5 revisado no contiene docs/AXS_CORPORATIVO_CONTRATO_V1.md ni docs/AXS_CORPORATIVO_AUDITORIA_BASE_20261023.md.

El contrato exige recorrido de visitas y atención de los cuatro derechos, conservación/proveedores/restauración antes del piloto real. El ensayo cerrado aquí es una entrega estructural de directorio y registro asistido de un caso de acceso ficticio, no la aceptación total de ese contrato.

**Salida exigida:** incorporar o resolver explícitamente ambos documentos, manteniendo la delimitación del ensayo y sin declarar aceptado un piloto corporativo de visitantes o privacidad integral.

### I4 — Descripciones con estados históricos contradictorios

#100 aún contiene apartados de "falta primer login"; #102 acumula fases ya superadas; #103 aún dice pendiente repetir la tercera sede. Esos textos no son el estado final.

**Acción de esta revisión:** enlazar este cierre y reemplazar las descripciones de #102/#103 por su comportamiento final, evidencias y pendientes actuales. Las notas técnicas históricas de commits siguen siendo evidencia contextual; no deben confundirse con capacidades vigentes.

## 5. Orden recomendado para continuar

1. Resolver #87/#95; reunir #103 con C5 y cerrar los disparadores de CI. No reescribir los commits validados sin necesidad.
2. Ejecutar Tests y PostgreSQL RLS en el head conjunto, comprobar regresión residencial y revisar el delta final de permisos/migraciones. La migración fechada del sandbox poblado tiene precondiciones exactas y no es una migración genérica de producción; no aplicarla indiscriminadamente.
3. Con ese resultado listo, revisar la integración por dependencias C0 #96→C1 #97→C2 #98→C3 #100→C5 #102→#103. Al cambiar bases o integrar, volver a comprobar el SHA y sus checks. Revisar previamente los despliegues que main pueda disparar y el procedimiento de migración/recuperación correspondiente.

Esta revisión no fusionó PR, no cambió flags, designaciones, infraestructura o producción, y no añadió funcionalidades. Solo consolida evidencia y estado de integración. Las fuentes de datos, criterios de privacidad y funcionalidades excluidas no se amplían por cerrar el ensayo.


## 6. Integración del código y cierre de disparadores CI

Se reúne el head correctivo c7c502239c2549c9f9a670a4eafb2906758d5522 con el C5 vigente 3ba15f70ec890544e95bd50438f5a6b03c34b878 mediante un commit con ambos padres. El primer padre conserva SQL/evidencia de #103; el segundo incorpora el ajuste UX que faltaba. La comparación por blobs contra el ancestro 3c7397b confirmó tres archivos C5 modificados y cero conflictos; esos tres blobs se conservan exactamente como en #102.

Los workflows incorporan:
- Tests por push de fix/axs-corporativo-* y PR dirigido a ramas corporativas/correctivas, además de los filtros anteriores.
- PostgreSQL RLS por push de C5 y de la rama correctiva, y PR dirigido a ramas corporativas/correctivas.
- workflow_dispatch en Tests; PG ya lo tenía.

Se validaron ambos YAML con js-yaml y la coincidencia de filtros con los nombres reales de la rama correctiva y C5. No se modifican los comandos, matrices, servicios PostgreSQL desechables ni los casos ejecutados por los jobs.

Esta integración debe provocar ambos workflows al actualizar la rama de #103. El cierre exige observar Tests (Python, frontend y navegador) y PostgreSQL RLS aprobados sobre el mismo SHA resultante. Un job pendiente o un resultado heredado no lo sustituyen; consultar el resultado exacto en #103.

El contrato #87 y la auditoría #95 continúan pendientes y no se incorporan en esta tarea. No se fusiona a main ni se modifican infraestructura, datos, designaciones o despliegues. Los servicios del sandbox conservan sus versiones fijadas y el ensayo autenticado cerrado sigue siendo evidencia operativa de esas versiones.
