# INFORME DE AUDITORÍA FORENSE — BOOTSTRAP AUP

**Sistema:** MSP_AXS  
**Componente:** Script de Bootstrap Inicial (`bootstrap_aup_sistema.sql`)  
**Tipo de auditoría:** Forense de seguridad estructural  
**Fecha:** 2026-01-01  
**Auditor:** Senior PostgreSQL Security Auditor

---

## 1. ESCALAMIENTO IMPLÍCITO

### 1.1 Campo `rol` en tabla `usuarios`

**Hallazgo:** RIESGO ALTO

El campo `rol` se inserta con valor `'MSP_ADMIN'` pero:
- NO existe validación formal de que este campo sea consultado por `authorities_gov`
- Nombre del rol coincide con `AccessLevel.MSP_ADMIN` de tabla `user_tenant_scope`
- Potencial confusión semántica: ¿`rol` otorga poder o es metadata?

**Vectores de riesgo:**
1. Desarrollador futuro podría asumir que `usuarios.rol = 'MSP_ADMIN'` otorga poder global sin verificar `authorities_gov`
2. Código legacy podría evaluar `rol` sin consultar gobierno explícito
3. Confusión entre `usuarios.rol`, `user_tenant_scope.access_level` y `authorities_gov.tipo`

**Contramedida observada:**
- Bootstrap declara autoridad explícita en `authorities_gov` (correcto)
- Pero no documenta que `rol` es SOLO metadata descriptiva

**Clasificación:** ALTO — Campo ambiguo con nombre que sugiere poder.

---

### 1.2 Campo `condominio_id` en tabla `usuarios`

**Hallazgo:** RIESGO MEDIO

Usuario root tiene `condominio_id = 'tenant_demo_0000000000000001'`:
- Sugiere "pertenencia" a un tenant específico
- Contradice autoridad `global` que debería operar sobre TODOS los tenants
- Campo marcado como "legacy, usar scope" pero sigue poblado

**Vectores de riesgo:**
1. Lógica de negocio podría filtrar por `condominio_id` ignorando `authorities_gov`
2. Usuario con autoridad `global` podría verse limitado implícitamente al tenant especificado
3. Inconsistencia: root tiene autoridad global pero `condominio_id` vincula a un solo tenant

**Contramedida observada:**
- Scope explícito declara alcance en `user_tenant_scope` (correcto)
- Pero `condominio_id` persiste como fuente de verdad alternativa

**Clasificación:** MEDIO — Fuente de verdad duplicada con potencial de inconsistencia.

---

### 1.3 Valores de string sin enumeración forzada

**Hallazgo:** RIESGO MEDIO

Campos críticos usan VARCHAR sin validación PostgreSQL:
- `authorities_gov.tipo`: `'global'` (esperado: `AuthorityType`)
- `user_tenant_scope.access_level`: `'msp_admin'` (esperado: `AccessLevel`)
- `user_tenant_scope.estado`: `'activo'` (esperado: `ScopeStatus`)
- `policies_gov.ambito`: `'global'`, `'tenant'` (esperado: `PolicyScope`)
- `policies_gov.estado`: `'activo'` (esperado: `GovStatus`)

**Vectores de riesgo:**
1. Typo manual → `'globa1'` (con "1") pasa sin error
2. Inyección de valor no contemplado → `'super_global'`
3. Sistema de gobierno falla silenciosamente si valor no coincide con lógica aplicativa

**Contramedida observada:**
- Ninguna. PostgreSQL no valida valores, depende de aplicación.

**Clasificación:** MEDIO — Sin guardrails de base de datos. Validación delegada a aplicación.

---

### 1.4 Escalamiento vía scope sin verificación de authority

**Hallazgo:** NO VULNERABLE (condicionado)

Bootstrap crea:
1. Usuario root
2. Scope root → tenant demo (`access_level = 'msp_admin'`)
3. Autoridad global

**Pregunta crítica:** ¿Puede un usuario con `access_level = 'msp_admin'` operar sin `authority_id` en `authorities_gov`?

**Respuesta según estructura:**
- `AccessLevel` declara DÓNDE puede actuar (alcance espacial)
- `Authority` declara QUÉ puede gobernar (poder estructural)
- Separación conceptual correcta

**Condición de NO VULNERABILIDAD:**
La aplicación DEBE verificar ambos:
```python
# Correcto
if scope.access_level == 'msp_admin' AND authority.tipo == 'global':
    permitir()
```

**Riesgo residual:**
Si aplicación evalúa solo `access_level` sin consultar `authorities_gov`, escalamiento implícito existe.

**Clasificación:** NO VULNERABLE — Si aplicación implementa verificación dual. RIESGO ALTO si no.

---

## 2. AMBIGÜEDAD DE GOBIERNO

### 2.1 Doble semántica de "admin"

**Hallazgo:** RIESGO ALTO

Tres lugares usan "admin" con significados distintos:
1. `usuarios.rol = 'MSP_ADMIN'` → metadata de identidad
2. `user_tenant_scope.access_level = 'msp_admin'` → alcance espacial
3. `authorities_gov.tipo = 'global'` → poder estructural

**Problema:**
¿Qué otorga poder real? Sin documentación clara, desarrollador puede asumir cualquiera de los tres.

**Test de ambigüedad:**
- Usuario A: `rol = 'MSP_ADMIN'`, sin scope, sin authority → ¿Puede crear tenants? **NO (correcto)**
- Usuario B: `rol = 'RESIDENTE'`, scope `access_level = 'msp_admin'`, sin authority → ¿Puede crear tenants? **AMBIGUO**
- Usuario C: `rol = 'RESIDENTE'`, sin scope, con authority `tipo = 'global'` → ¿Puede crear tenants? **AMBIGUO**

**Clasificación:** ALTO — Tres fuentes de verdad sin jerarquía explícita.

---

### 2.2 Autoridad `global` sin tenant vs Scope en tenant específico

**Hallazgo:** RIESGO MEDIO

Usuario root tiene:
- Authority: `tipo = 'global'`, `tenant_id = NULL` → Opera sobre TODA la plataforma
- Scope: `tenant_id = 'tenant_demo_0000000000000001'` → Opera solo en tenant demo

**Contradicción lógica:**
Si root tiene autoridad global, ¿por qué necesita scope limitado a un tenant?

**Interpretaciones posibles:**
1. Authority declara QUÉ puede hacer (crear tenants, políticas)
2. Scope declara DÓNDE puede actuar operativamente (generar QR, validar visitas)
3. Root puede gobernar toda plataforma, pero operar en demo específicamente

**Riesgo:**
Sin documentación, desarrollador puede:
- Requerir scope para TODO (anulando autoridad global)
- Requerir authority para TODO (anulando scopes específicos)
- Confundir qué verificar en cada caso

**Clasificación:** MEDIO — Separación conceptual correcta pero no explicitada.

---

### 2.3 Política sin enlace a autoridad

**Hallazgo:** RIESGO MEDIO

Políticas declaradas:
1. `policy_global_crear_tenant` → `require_authority_global: true` (en JSON)
2. `policy_tenant_demo_qr_vigencia` → No menciona qué autoridad puede usarla

**Problema:**
¿Quién puede invocar `policy_tenant_demo_qr_vigencia`?
- ¿Cualquier usuario con scope en tenant demo?
- ¿Solo autoridades `first_tier` sobre tenant demo?
- ¿Cualquier autoridad global?

**Sin relación formal `policy → authority`, enforcement queda en aplicación.**

**Clasificación:** MEDIO — Gobierno no autocontenido. Requiere lógica externa.

---

### 2.4 Estado `'activo'` vs ausencia de `valida_hasta`

**Hallazgo:** NO VULNERABLE

Políticas tienen:
- `estado = 'activo'`
- `valida_hasta = NULL`

**Interpretación correcta:**
- `estado = 'activo'` → Política vigente ahora
- `valida_hasta = NULL` → Sin fecha de expiración

**Posible ambigüedad:**
¿Política sin `valida_hasta` expira alguna vez?
- Respuesta: NO (correcto para bootstrap)

**Clasificación:** NO VULNERABLE — Semántica clara: NULL = sin fin.

---

## 3. RIESGOS DE POSTGRES / NEON

### 3.1 Ausencia de Foreign Keys entre dominios

**Hallazgo:** RIESGO ALTO

Bootstrap asume 3 bases separadas (`aup_core`, `aup_event`, `aup_gov`):
- `authorities_gov.identity_id` → `usuarios.usuario_id` (sin FK física)
- `authorities_gov.tenant_id` → `condominios_exo.condominio_id` (sin FK física)
- `events_aup.identity_id` → `usuarios.usuario_id` (sin FK física)
- `policies_gov.target_tenant_id` → `condominios_exo.condominio_id` (sin FK física)

**Vectores de riesgo:**
1. Insert de autoridad con `identity_id` inexistente → Aceptado por DB
2. Delete de usuario root → Autoridad queda huérfana (sin cascada)
3. Update de `usuario_id` → Autoridad apunta a identidad inexistente
4. Inconsistencias detectables solo por aplicación (no por DB)

**Mitigaciones posibles:**
- CHECK constraint manual con subquery (caro)
- Validación en aplicación antes de INSERT
- Reconciliación periódica (batch job)

**Clasificación:** ALTO — Integridad referencial no garantizada por DBMS.

---

### 3.2 UUID como VARCHAR(36)

**Hallazgo:** RIESGO BAJO

IDs críticos son strings literales:
- `'user_root_000000000000000001'`
- `'msp_root_00000000000000000001'`
- `'tenant_demo_0000000000000001'`

**Vectores de riesgo:**
1. Collation differences → Comparación case-sensitive/insensitive inconsistente
2. Espacio en blanco → `'user_root_000000000000000001 '` (con trailing space) ≠ original
3. Sin validación de formato → `'cualquier_cosa'` es válido
4. Índice B-tree sobre string más lento que sobre UUID nativo

**Mitigación observada:**
- Valores hardcodeados en bootstrap (sin input externo)

**Clasificación:** BAJO — Riesgo controlado en bootstrap, potencial en runtime.

---

### 3.3 Ausencia de Row Level Security (RLS)

**Hallazgo:** RIESGO ALTO

Ninguna tabla tiene RLS habilitado:
```sql
-- NO existe:
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON usuarios FOR SELECT USING (condominio_id = current_setting('app.tenant_id'));
```

**Vectores de riesgo:**
1. Conexión DB comprometida → Acceso total a todos los tenants
2. SQL injection → Bypass de filtros aplicativos
3. Usuario con acceso directo a DB → Lee todos los condominios

**Mitigación actual:**
- Aislamiento delegado a aplicación (filtros WHERE en queries)

**Clasificación:** ALTO — Tenant isolation no garantizado por DBMS. Defense-in-depth ausente.

---

### 3.4 Hash de evento hardcodeado

**Hallazgo:** RIESGO MEDIO

Evento de génesis tiene hash:
```sql
hash_evento = '8a3f9c1b2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a'
```

**Problema:**
Hash no calculado dinámicamente. Posible discrepancia:
1. Comentario dice: "echo -n '...' | sha256sum"
2. Orden de concatenación de campos no especificado formalmente
3. Timestamp usa `now()` → Hash no reproducible

**Consecuencia:**
Verificación de hash fallará si campos cambian o si timestamp difiere.

**Clasificación:** MEDIO — Integridad de evento de génesis no verificable.

---

### 3.5 Uso de `now()` sin timezone

**Hallazgo:** RIESGO BAJO

Todas las inserciones usan `now()`:
```sql
created_at = now()
```

**Problema en Neon/PostgreSQL:**
- `now()` usa timezone de sesión (puede variar)
- Recomendado: `CURRENT_TIMESTAMP` o `now() AT TIME ZONE 'UTC'`

**Impacto:**
- Timestamps pueden variar según cliente
- Auditoría de eventos pierde precisión

**Clasificación:** BAJO — Impacto en auditoría, no en seguridad directa.

---

## 4. EVENTOS Y TRAZABILIDAD

### 4.1 Evento de génesis: Suficiencia para reconstrucción

**Hallazgo:** RIESGO ALTO

Evento de génesis declara:
```json
"components_initialized": [
  "msp_root",
  "tenant_demo",
  "user_root",
  "scope_root_demo",
  "authority_global_root",
  "policy_global_crear_tenant",
  "policy_tenant_demo_qr_vigencia"
]
```

**Problema:**
Metadata lista componentes pero NO sus valores:
- ¿Qué `usuario_id` se creó? → No registrado
- ¿Qué `authority_id` se asignó? → No registrado
- ¿Qué `policy_id` se declaró? → No registrado

**Consecuencia:**
Imposible reconstruir estado inicial desde eventos. Event sourcing incompleto.

**Para reconstrucción completa, se requeriría:**
```json
{
  "msp_root": {"msp_id": "msp_root_00000000000000000001", "nombre": "MSP_ROOT_PLATFORM"},
  "user_root": {"usuario_id": "user_root_000000000000000001", "email": "root@mspaxs.platform"},
  ...
}
```

**Clasificación:** ALTO — Evento de génesis es metadata, no fuente de verdad reconstruible.

---

### 4.2 Acciones críticas sin registro

**Hallazgo:** RIESGO ALTO

Bootstrap ejecuta 7 inserciones críticas:
1. Insert MSP → Sin evento
2. Insert tenant → Sin evento
3. Insert usuario → Sin evento
4. Insert scope → Sin evento
5. Insert authority → Sin evento
6. Insert policy 1 → Sin evento
7. Insert policy 2 → Sin evento
8. Insert evento génesis → **Único evento**

**Problema:**
Solo 1 evento registra 7 operaciones. Granularidad insuficiente.

**Consecuencia:**
- No se puede auditar QUÉ pasó si bootstrap falla parcialmente
- No se puede detectar QUÉ componente falta si evento existe pero inserts fallaron
- Rollback parcial deja sistema inconsistente sin traza

**Patrón recomendado:**
Cada INSERT crítico debería generar evento:
```sql
INSERT INTO events_aup (...) VALUES (...); -- evento: crear_msp
INSERT INTO msps_exo (...) VALUES (...);
INSERT INTO events_aup (...) VALUES (...); -- evento: crear_usuario
INSERT INTO usuarios (...) VALUES (...);
```

**Clasificación:** ALTO — Trazabilidad de bootstrap insuficiente.

---

### 4.3 Evento de génesis con `scope_id = NULL`

**Hallazgo:** NO VULNERABLE

Evento de génesis tiene:
```sql
scope_id = NULL  -- Evento de sistema, no atado a scope específico
```

**Interpretación:**
Eventos de sistema (bootstrap, mantenimiento) no requieren scope.

**Pregunta crítica:**
¿Puede aplicación diferenciar eventos de sistema vs eventos operativos?

**Respuesta:**
- Sí, vía `entidad = 'sistema'` y `accion = 'bootstrap_sistema'`

**Clasificación:** NO VULNERABLE — Eventos de sistema correctamente identificados.

---

### 4.4 `session_hash = 'genesis_hash'`

**Hallazgo:** RIESGO MEDIO

Evento de génesis usa:
```sql
session_hash = 'genesis_hash'  -- Hash especial para evento de génesis
```

**Problema:**
Valor hardcodeado colisiona con posible hash JWT real:
- ¿Qué pasa si un JWT genera hash `'genesis_hash'` por coincidencia?
- ¿Sistema puede diferenciar evento de génesis vs evento operativo con mismo hash?

**Mitigación recomendada:**
Usar prefijo distinguible: `'SYSTEM_GENESIS_BOOTSTRAP_NONCE'`

**Clasificación:** MEDIO — Bajo riesgo de colisión, pero no imposible.

---

### 4.5 Inconsistencias temporales

**Hallazgo:** RIESGO BAJO

Todas las inserts usan `now()`:
- MSP creado en `now()`
- Tenant creado en `now()`
- Usuario creado en `now()`
- Scope creado en `now()`
- Authority creado en `now()`
- Policies creadas en `now()`
- Evento creado en `now()`

**Problema:**
Orden temporal no garantizado. Todas las entradas pueden tener mismo timestamp.

**Consecuencia:**
Auditoría no puede determinar orden de creación si timestamps coinciden (precisión de milisegundos).

**Clasificación:** BAJO — Impacto en auditoría forense detallada, no en funcionalidad.

---

## 5. ATAQUES LÓGICOS POSIBLES

### 5.1 Abuso de scope: Scope sin authority

**Vector de ataque:**
1. Atacante obtiene credenciales de usuario con `access_level = 'msp_admin'`
2. Usuario NO tiene entry en `authorities_gov`
3. Aplicación verifica solo `access_level` → **Escalamiento**

**Explotación:**
```python
# Código vulnerable:
if user_scope.access_level == 'msp_admin':
    crear_tenant()  # SIN verificar authorities_gov
```

**Condición de éxito:**
Aplicación asume que `access_level = 'msp_admin'` otorga poder de gobierno.

**Contramedida AUP:**
Sistema declara que `access_level` define DÓNDE, no QUÉ. Enforcement en aplicación.

**Clasificación:** RIESGO ALTO si aplicación no verifica authorities_gov.

---

### 5.2 Abuso de authority: Authority sin scope

**Vector de ataque:**
1. Atacante obtiene credenciales de usuario con authority `tipo = 'global'`
2. Usuario NO tiene entry en `user_tenant_scope`
3. Aplicación verifica solo `authorities_gov` → **Operación sin alcance**

**Explotación:**
```python
# Código vulnerable:
if authority.tipo == 'global':
    generar_qr(tenant_id='cualquier_tenant')  # SIN verificar scope
```

**Condición de éxito:**
Aplicación asume que authority `global` permite operar en todos los tenants sin scope explícito.

**Contramedida AUP:**
Sistema declara que authority gobierna, scope opera. Enforcement en aplicación.

**Clasificación:** RIESGO ALTO si aplicación no verifica ambos.

---

### 5.3 Abuso de policy: Límites en JSON sin validación

**Vector de ataque:**
1. Atacante con acceso a DB modifica `policies_gov.limites`:
   ```json
   {"max_dias_vigencia": 7} → {"max_dias_vigencia": 999999}
   ```
2. Aplicación lee límite de JSON sin validación
3. QR generados con vigencia de 2739 años

**Explotación:**
```python
# Código vulnerable:
policy = get_policy('generar_qr')
max_dias = policy.limites['max_dias_vigencia']  # 999999
crear_qr(vigencia=max_dias)  # Sin validar rango razonable
```

**Condición de éxito:**
Aplicación confía ciegamente en valores de JSON sin sanitización.

**Contramedida:**
Validación de rangos en aplicación antes de aplicar límites.

**Clasificación:** RIESGO MEDIO — Requiere acceso a DB. Defense-in-depth ausente.

---

### 5.4 Replay lógico: Reusar `authority_id`

**Vector de ataque:**
1. Authority revocada: `UPDATE authorities_gov SET estado = 'revocado', revoked_at = now() WHERE authority_id = 'auth_global_root_0000000001'`
2. Atacante con acceso a DB ejecuta:
   ```sql
   UPDATE authorities_gov SET estado = 'activo', revoked_at = NULL WHERE authority_id = 'auth_global_root_0000000001'
   ```
3. Autoridad resucitada sin evento de auditoría

**Explotación:**
Sistema no registra cambios de estado en `events_aup`. Revocación silenciosa revertible.

**Condición de éxito:**
Acceso directo a DB bypass de aplicación.

**Contramedida:**
- RLS para proteger tabla `authorities_gov`
- Triggers que registren cambios en `events_aup`
- Validación de que `estado` solo cambia via API (no SQL directo)

**Clasificación:** RIESGO ALTO — Sin auditoría de cambios de estado.

---

### 5.5 Confusión de tenant: Usuario con múltiples scopes

**Vector de ataque:**
1. Usuario tiene scopes en 2 tenants:
   - Scope A: `tenant_id = 'tenant_demo_0000000000000001'`, `access_level = 'residente'`
   - Scope B: `tenant_id = 'tenant_prod_0000000000001'`, `access_level = 'msp_admin'`
2. Usuario autentica y obtiene JWT
3. JWT contiene solo `usuario_id` (no `tenant_id` ni `scope_id`)
4. Request a endpoint sin especificar tenant → **¿Qué scope aplica?**

**Explotación:**
```python
# Código vulnerable:
user_scopes = get_scopes(identity_id)  # Retorna 2 scopes
# ¿Cuál usar? Sistema no tiene contexto.
if user_scopes[0].access_level == 'msp_admin':  # Elige scope B
    operar_en_tenant_A()  # Operación en tenant equivocado
```

**Condición de éxito:**
Sistema no valida que operación ocurre en tenant correcto según scope activo.

**Contramedida AUP:**
Request DEBE incluir `tenant_id` explícito. Validar match con scope.

**Clasificación:** RIESGO MEDIO — Requiere lógica aplicativa correcta.

---

## RESUMEN EJECUTIVO

| Categoría | Hallazgos ALTO | Hallazgos MEDIO | Hallazgos BAJO | NO VULNERABLE |
|-----------|----------------|-----------------|----------------|---------------|
| 1. Escalamiento Implícito | 2 | 2 | 0 | 1 |
| 2. Ambigüedad de Gobierno | 1 | 2 | 0 | 1 |
| 3. Riesgos PostgreSQL/Neon | 2 | 1 | 2 | 0 |
| 4. Eventos y Trazabilidad | 2 | 1 | 1 | 1 |
| 5. Ataques Lógicos | 3 | 2 | 0 | 0 |
| **TOTAL** | **10** | **8** | **3** | **3** |

---

## HALLAZGOS CRÍTICOS (RIESGO ALTO)

1. **Campo `rol` en usuarios** — Ambigüedad semántica con potencial de escalamiento
2. **Ausencia de FKs entre dominios** — Integridad referencial no garantizada
3. **Ausencia de RLS** — Tenant isolation delegado a aplicación
4. **Evento de génesis no reconstruible** — Event sourcing incompleto
5. **Bootstrap sin eventos granulares** — Trazabilidad insuficiente
6. **Abuso de scope sin authority** — Escalamiento si aplicación no verifica ambos
7. **Abuso de authority sin scope** — Operación sin alcance si aplicación no valida
8. **Replay lógico de authorities** — Cambios de estado sin auditoría
9. **Valores string sin validación DB** — Typos y valores inválidos pasan silenciosamente
10. **Ambigüedad de "admin"** — Tres fuentes de verdad sin jerarquía explícita

---

## CONCLUSIÓN

El script de bootstrap es **ESTRUCTURALMENTE CORRECTO** según principios AUP declarados:
- Separación de scope (DÓNDE) vs authority (QUÉ) vs policy (LÍMITES) → Correcta
- Declaración explícita de poder → Correcta
- Sistema cerrado por defecto → Correcto (si aplicación implementa)

**PERO:**

La arquitectura depende **ENTERAMENTE** de que la aplicación:
1. Verifique scope Y authority simultáneamente
2. Valide políticas antes de operaciones
3. No confíe en campos `rol` o `condominio_id`
4. Implemente tenant isolation en queries

**Sin enforcement a nivel de base de datos, el sistema es vulnerable a:**
- Bypass de aplicación (acceso directo a DB)
- Errores de lógica aplicativa (verificar solo scope o solo authority)
- Manipulación silenciosa de estados (sin eventos)

**VEREDICTO FINAL:**

Bootstrap correcto bajo supuesto de **aplicación perfecta**.  
Sin guardrails en DB → **RIESGO ALTO en producción**.

---

**FIN DE INFORME**
