# ═══════════════════════════════════════════════════════════════════════════
# AUP STRUCTURAL GUARDRAILS
# ═══════════════════════════════════════════════════════════════════════════
#
# ADVERTENCIA:
#   Estos NO son tests unitarios clásicos.
#   NO son pytest ejecutables todavía.
#   Son GUARDRAILS ESTRUCTURALES del modelo AUP.
#
# PROPÓSITO:
#   Asegurar que el sistema no puede ejecutarse fuera del orden ontológico AUP,
#   incluso si el código "funciona".
#
# DERIVACIÓN:
#   Generados 1:1 desde AUP_PSEUDOCODIGO_CONTRATO.md
#   Sin interpretación, sin optimización, sin traducción a patrones clásicos.
#
# USO:
#   Estos guardrails NO son opcionales.
#   NO se parametrizan.
#   NO se negocian.
#   Son el cinturón de seguridad del modelo AUP.
#
# ═══════════════════════════════════════════════════════════════════════════

## 🧪 TEST S-01 — No acción sin sesión (AUP_SESSION)

**Precondición:**
- No existe sesión válida
- Se intenta cualquier operación (ej. generar QR)

**Acción:**
- Invocar operación protegida sin proporcionar sesión
- Intentar acceder directamente al router/endpoint

**Resultado esperado:**
```
Operación DENEGADA
Código HTTP: 401 Unauthorized
Evento registrado:
  action = "intento_de_operacion"
  result = "DENIED_NO_SESSION"
  timestamp = [UTC]
  actor = null
  metadata = {endpoint: "/qr/generate", method: "POST"}
```

**Violación AUP si:**
- ❌ La operación continúa sin sesión
- ❌ No se registra evento del intento
- ❌ Se "infieren" datos de identidad desde otros contextos
- ❌ Se permite "modo anónimo" para operaciones gobernadas

**Axioma validado:**
> Nada ocurre sin sesión.

**Consecuencia estructural:**
Si este guardrail falla, todo el modelo AUP_SESSION colapsa.
No hay actor identificable, no hay auditoría, no hay gobierno.

---

## 🧪 TEST S-02 — El alcance no vive en el token (AUP_SCOPE)

**Precondición:**
- Token JWT válido
- Token NO contiene claims de scope/tenant
- Alcance solo existe en memoria CORE (base de datos, Redis, etc.)

**Acción:**
- Resolver alcance para acción específica en tenant_X
- Deserializar token
- Consultar scope dinámicamente

**Resultado esperado:**
```
Sistema consulta memoria CORE (no el token)
Query ejecutado:
  SELECT scope FROM scopes
  WHERE identity_id = {session.identity_id}
  AND tenant_id = {tenant_X}
  AND estado = 'ACTIVO'

Alcance resuelto dinámicamente
```

**Violación AUP si:**
- ❌ El token contiene permisos o roles
- ❌ El router infiere alcance desde el token
- ❌ Se reutiliza un scope cacheado en el token
- ❌ El scope se "serializa" en la sesión

**Axioma validado:**
> El alcance vive en la memoria, no en la credencial.

**Consecuencia estructural:**
Si el scope vive en el token, revocación en caliente es imposible.
Multi-tenant se convierte en multi-token.
El modelo AUP_SCOPE colapsa.

---

## 🧪 TEST S-03 — No gobierno sin alcance (orden obligatorio)

**Precondición:**
- Sesión válida
- No existe scope para la acción solicitada
- Políticas de gobierno existen y están activas

**Acción:**
- Intentar evaluar gobierno (políticas/delegaciones)
- Verificar orden de evaluación

**Resultado esperado:**
```
Gobierno NO se evalúa
Flujo se detiene en SCOPE
Evento registrado:
  action = "generar_qr"
  result = "DENIED_NO_SCOPE"
  tenant_id = {tenant_X}
  actor = {identity_id}
  stage = "SCOPE"
```

**Violación AUP si:**
- ❌ GOV se evalúa sin scope previo
- ❌ Políticas se consultan "por si acaso"
- ❌ Se permite evaluar gobierno "globalmente" sin tenant
- ❌ El orden es SESSION → GOV → SCOPE

**Axioma validado:**
> El poder se evalúa solo sobre alcance existente.

**Consecuencia estructural:**
Si gobierno se evalúa sin scope, se rompe el aislamiento multi-tenant.
Políticas globales pueden interferir con tenants específicos.
El modelo AUP pierde coherencia estructural.

---

## 🧪 TEST S-04 — Gobierno siempre decide antes del negocio (AUP_GOV)

**Precondición:**
- Sesión válida
- Scope válido
- Operación gobernada (ej. GENERATE_QR)

**Acción:**
- Ejecutar operación completa
- Verificar orden de ejecución

**Resultado esperado:**
```
Orden de ejecución:
  1. SESSION (validada)
  2. SCOPE (resuelta)
  3. GOV (evaluada) ← DEBE ocurrir ANTES del negocio
  4. NEGOCIO (ejecutado solo si GOV = ALLOW)
  5. EVENT (registrado)

Evento de gobierno registrado SIEMPRE:
  action = "evaluar_gobierno"
  accion_objetivo = "generar_qr"
  result = "PERMITIDO" | "DENEGADO"
  policies_evaluadas = [policy_ids]
```

**Violación AUP si:**
- ❌ El negocio se ejecuta antes del gobierno
- ❌ El router "confía" en el rol sin consultar GOV
- ❌ El gobierno solo se consulta en algunos casos ("operaciones críticas")
- ❌ Se permite "modo rápido" que omite GOV

**Axioma validado:**
> El negocio ocurre después del poder, nunca antes.

**Consecuencia estructural:**
Si negocio se ejecuta antes de gobierno, no hay control de poder.
El sistema se convierte en RBAC tradicional (permisos estáticos).
El modelo AUP_GOV pierde propósito.

---

## 🧪 TEST S-05 — Default DENY en ausencia de políticas

**Precondición:**
- Sesión válida
- Scope válido
- NO existen políticas cargadas para la acción solicitada
- NO existen delegaciones activas

**Acción:**
- Ejecutar operación gobernada
- Evaluar gobierno sin políticas

**Resultado esperado:**
```
Operación DENEGADA
Código HTTP: 403 Forbidden
Evento registrado:
  action = "evaluar_gobierno"
  accion_objetivo = "generar_qr"
  result = "DENIED_NO_POLICY"
  policies_encontradas = []
  motivo = "sin_politica_aplicable"
```

**Violación AUP si:**
- ❌ El sistema permite por defecto
- ❌ Se asume "policy implícita" (ej. "si tiene scope, puede todo")
- ❌ Se ejecuta por conveniencia ("es un admin")
- ❌ Se permite "modo desarrollo" sin políticas

**Axioma validado:**
> El poder explícito es el único poder válido.

**Consecuencia estructural:**
Si default es ALLOW, gobierno es decorativo.
No hay control real, solo teatro de seguridad.
El modelo AUP_GOV se convierte en formalidad sin poder.

---

## 🧪 TEST S-06 — Evento siempre existe, incluso en fallo (AUP_EVENT)

**Precondición:**
- Cualquier intento de acción (éxito o fallo)
- Operación denegada en SESSION, SCOPE o GOV

**Acción:**
- Ejecutar flujo completo (incluyendo fallos)
- Verificar registro de eventos

**Resultado esperado:**
```
Evento registrado para CADA intento:

Caso éxito:
  event_id = {uuid}
  actor = {identity_id}
  accion = "generar_qr"
  resultado = "EXITO"
  timestamp = [UTC]
  hash = SHA256(...)

Caso fallo en SCOPE:
  event_id = {uuid}
  actor = {identity_id}
  accion = "generar_qr"
  resultado = "DENEGADO"
  motivo = "sin_scope_activo"
  timestamp = [UTC]
  hash = SHA256(...)

Caso fallo en GOV:
  event_id = {uuid}
  actor = {identity_id}
  accion = "generar_qr"
  resultado = "DENEGADO"
  motivo = "limite_excedido"
  timestamp = [UTC]
  hash = SHA256(...)
```

**Violación AUP si:**
- ❌ Eventos solo se registran en éxito
- ❌ El evento es opcional
- ❌ Se permite modificar eventos (UPDATE)
- ❌ Se permite eliminar eventos (DELETE)

**Axioma validado:**
> Sin evento, no hay existencia.

**Consecuencia estructural:**
Si eventos solo se registran en éxito, auditoría es inútil.
Intentos de intrusión son invisibles.
Análisis forense es imposible.
El modelo AUP_EVENT pierde integridad.

---

## 🧪 TEST S-07 — Inmutabilidad detectiva (forense)

**Precondición:**
- Evento registrado en memoria append-only
- Hash calculado y almacenado

**Acción:**
- Alterar el contenido del evento en almacenamiento directo (SQL UPDATE)
- Ejemplo: Cambiar resultado de "DENEGADO" a "EXITO"
- Recalcular integridad

**Resultado esperado:**
```
Sistema DETECTA inconsistencia:
  hash_esperado = SHA256(event_data_original)
  hash_actual = SHA256(event_data_alterado)
  
  SI hash_esperado != hash_actual:
    ALERTA_FORENSE("Evento alterado", event_id)
    MARCAR como COMPROMETIDO
    NO bloquear silenciosamente

Sistema NO corrige automáticamente
Sistema genera señal forense explícita
```

**Violación AUP si:**
- ❌ El sistema "corrige" silenciosamente
- ❌ El sistema ignora la alteración
- ❌ Se permite UPDATE/DELETE en tabla de eventos
- ❌ No existe mecanismo de detección

**Axioma validado:**
> La verdad no se corrige; se detecta.

**Consecuencia estructural:**
Si eventos son mutables, no hay verdad histórica.
Auditoría forense es imposible.
Cumplimiento normativo falla.
El modelo AUP_EVENT pierde propósito.

---

## 🧪 TEST S-08 — Prohibición de consultas cruzadas entre dominios

**Precondición:**
- Dominios separados:
  - CORE (identity, scope, negocio)
  - GOV (authority, policy, delegation)
  - EVENT (append-only truth)

**Acción:**
- Intentar que:
  - CORE consulte EVENT directamente
  - GOV escriba en tablas de negocio
  - EVENT consulte CORE para "enriquecer" datos

**Resultado esperado:**
```
Arquitectónicamente IMPOSIBLE

CORE NO puede:
  SELECT * FROM events  # Violación de dominio

GOV NO puede:
  INSERT INTO qrs  # Violación de responsabilidad

EVENT NO puede:
  SELECT * FROM scopes  # Violación de inmutabilidad

Única comunicación permitida:
  - Paso de referencias (IDs)
  - Invocación de servicios
  - NO import directo
```

**Violación AUP si:**
- ❌ Existe import cruzado (ej. `from event import EventService` en GOV)
- ❌ Un dominio "sabe" demasiado del otro (acoplamiento)
- ❌ Consultas JOIN entre dominios
- ❌ Dependencia circular

**Axioma validado:**
> Los dominios se relacionan por referencia, no por dependencia.

**Consecuencia estructural:**
Si dominios se acoplan, separación de responsabilidades colapsa.
Gobierno y verdad se mezclan con negocio.
Modelo AUP se convierte en monolito distribuido.

---

## 🧪 TEST S-09 — El router no es fuente de verdad

**Precondición:**
- Router recibe request HTTP
- Endpoint protegido

**Acción:**
- Evaluar decisión de acceso
- Verificar dónde se toma cada decisión

**Resultado esperado:**
```
Router delega TODO:

1. Identidad → AUP_SESSION
   router NO valida JWT
   router NO verifica expiración
   router NO infiere usuario

2. Alcance → AUP_SCOPE
   router NO verifica tenant
   router NO compara roles
   router NO asume permisos

3. Poder → AUP_GOV
   router NO decide si permite
   router NO evalúa políticas
   router NO omite gobierno

4. Verdad → AUP_EVENT
   router NO omite registro
   router NO decide qué registrar
   router NO modifica eventos

Router SOLO:
  - Recibe request
  - Llama dependencias
  - Retorna respuesta
```

**Violación AUP si:**
- ❌ El router decide permitir/denegar
- ❌ El router infiere reglas de negocio
- ❌ El router omite EVENT
- ❌ El router implementa lógica (más allá de orquestación)

**Axioma validado:**
> El router orquesta, no gobierna.

**Consecuencia estructural:**
Si router contiene lógica, separación de responsabilidades falla.
Cambios en reglas requieren modificar routers.
Modelo AUP se convierte en "smart routing" (anti-patrón).

---

## 🧪 TEST S-10 — Axioma global de cierre

**Verificación:**
El sistema NO puede ejecutar una operación si falla cualquiera:

```
SESSION ✗  → STOP (401 Unauthorized)
SCOPE   ✗  → STOP (403 Forbidden, sin scope)
GOV     ✗  → STOP (403 Forbidden, sin poder)
EVENT   ✗  → STOP (500 Internal, fallo crítico)
```

**Precondición:**
- Sistema completo operativo
- Operación gobernada de prueba

**Acción:**
- Ejecutar operación forzando fallo en cada paso:
  1. Sin sesión → Verificar STOP en SESSION
  2. Sin scope → Verificar STOP en SCOPE
  3. Sin política → Verificar STOP en GOV
  4. Sin registro → Verificar STOP (no existe)

**Resultado esperado:**
```
Caso 1: SESSION ✗
  HTTP 401
  No se consulta SCOPE
  No se consulta GOV
  No se ejecuta NEGOCIO
  Evento: DENIED_NO_SESSION

Caso 2: SCOPE ✗
  HTTP 403
  SESSION OK
  No se consulta GOV
  No se ejecuta NEGOCIO
  Evento: DENIED_NO_SCOPE

Caso 3: GOV ✗
  HTTP 403
  SESSION OK
  SCOPE OK
  No se ejecuta NEGOCIO
  Evento: DENIED_NO_POLICY | DENIED_LIMITE_EXCEDIDO

Caso 4: EVENT ✗
  HTTP 500
  SESSION OK
  SCOPE OK
  GOV OK
  NEGOCIO NO se ejecuta (rollback)
  Evento: ERROR_CRITICO
```

**Violación AUP si:**
- ❌ Cualquier bypass existe
- ❌ El orden es reordenable
- ❌ Se permite "modo rápido"
- ❌ Algún paso es opcional

**Axioma validado:**
```
No SESSION  → No acción
No SCOPE    → No permiso
No GOV OK   → No ejecución
No EVENT    → No existencia
```

**Consecuencia estructural:**
Si este guardrail falla, TODO el modelo AUP colapsa.
No hay integridad ontológica.
No hay garantía de poder.
No hay verdad histórica.

---

## 🧭 Cómo usar estos guardrails

### ✅ Deben usarse en:

1. **Revisión de arquitectura**
   - Verificar que el diseño no permite violaciones
   - Validar separación de dominios
   - Confirmar orden de ejecución

2. **Revisión de código**
   - Detectar lógica de negocio en routers
   - Identificar scope en tokens
   - Verificar registro de eventos

3. **Implementación de tests**
   - Derivar tests unitarios desde estos guardrails
   - Crear tests de integración que validen orden
   - Construir tests de regresión para prevenir violaciones

4. **Documentación técnica**
   - Incluir en onboarding de desarrolladores
   - Referenciar en pull requests
   - Usar como checklist de calidad

### ❌ NO deben:

- Ser opcionales
- Ser parametrizables
- Ser negociables
- Simplificarse por conveniencia
- Omitirse en "modo rápido"

### 🔒 Garantía estructural:

```
Si TODOS los guardrails pasan → Sistema AUP íntegro
Si UN guardrail falla         → Modelo comprometido
```

### 🚨 Severidad de violaciones:

| Guardrail | Severidad | Impacto si falla |
|-----------|-----------|------------------|
| S-01 (No sesión) | CRÍTICO | Auditoría imposible |
| S-02 (Scope dinámico) | CRÍTICO | Multi-tenant roto |
| S-03 (Orden obligatorio) | ALTO | Aislamiento comprometido |
| S-04 (GOV antes de negocio) | CRÍTICO | Control de poder inexistente |
| S-05 (Default DENY) | CRÍTICO | Seguridad decorativa |
| S-06 (Evento siempre) | CRÍTICO | Verdad histórica rota |
| S-07 (Inmutabilidad) | ALTO | Auditoría forense imposible |
| S-08 (Dominios separados) | MEDIO | Arquitectura acoplada |
| S-09 (Router orquesta) | MEDIO | Lógica en capa incorrecta |
| S-10 (Axioma global) | CRÍTICO | Modelo AUP colapsado |

---

## 📋 Checklist de cumplimiento

Antes de considerar el sistema AUP-compliant, verificar:

```
[ ] S-01: Ninguna operación sin sesión
[ ] S-02: Scope resuelto desde memoria viva
[ ] S-03: Gobierno solo evalúa con scope
[ ] S-04: Negocio después de gobierno
[ ] S-05: Default DENY aplicado
[ ] S-06: Eventos en éxito Y fallo
[ ] S-07: Hash de integridad calculado
[ ] S-08: Dominios sin import cruzado
[ ] S-09: Router sin lógica de decisión
[ ] S-10: Orden SESSION → SCOPE → GOV → NEGOCIO → EVENT
```

---

## 🎯 Relación con otros documentos

- **[AUP_PSEUDOCODIGO_CONTRATO.md](AUP_PSEUDOCODIGO_CONTRATO.md)**
  - Estos guardrails derivan 1:1 del contrato
  - El contrato define QUÉ, los guardrails definen CÓMO validar

- **[AUP_GRAPH.md](AUP_GRAPH.md)**
  - Grafo define relaciones ontológicas
  - Guardrails validan que esas relaciones se respetan

- **[CODE_REVIEW_COPILOT.md](CODE_REVIEW_COPILOT.md)**
  - Code review identificó testing como crítico (3/10)
  - Guardrails son la base para implementar tests estructurales

---

## ⚖️ Filosofía de los guardrails

```
Estos NO son tests de performance.
Estos NO son tests de usabilidad.
Estos NO son tests de optimización.

Son GUARDRAILS ESTRUCTURALES.

Su propósito es asegurar que el modelo AUP
no puede ser violado por conveniencia,
no puede ser simplificado por ignorancia,
no puede ser omitido por urgencia.

Son el cinturón de seguridad del modelo AUP.

Si algo "funciona" pero viola un guardrail,
entonces NO funciona correctamente.
```

# ═══════════════════════════════════════════════════════════════════════════
# FIN DE AUP STRUCTURAL GUARDRAILS
# ═══════════════════════════════════════════════════════════════════════════
