# DECLARACIÓN FORMAL DE MEMORIA AUP — MSP_AXS

**Fecha:** Diciembre 29, 2024  
**Versión:** 3.0.0-aup-gov  
**Naturaleza:** Declaración constitutiva (no técnica)

---

## I. AXIOMA FUNDACIONAL

**Un sistema sin memoria declarada no es un sistema: es una ejecución temporal.**

MSP_AXS declara formalmente su memoria persistente en **tres dominios AUP independientes**, aunque coexistan físicamente en un mismo proveedor (Neon PostgreSQL).

---

## II. DOMINIOS DE MEMORIA AUP

### 🧱 AUP_CORE — Identidad y Alcance

**Pregunta que responde:**  
*"¿Quién eres y hasta dónde llegas?"*

**Responsabilidad:**  
Declarar existencia de identidades y sus alcances operativos explícitos.

**Contiene:**
- `usuarios` (AUP_IDENTITY)
- `condominios_exo` (AUP_TENANT)
- `msps_exo` (AUP_MSP)
- `user_tenant_scope` (AUP_SCOPE)
- `casetas` (infraestructura operativa)
- `visitas` (entidades de negocio)
- `evidencias` (artefactos de operación)

**Axiomas:**
- Toda operación requiere identidad válida
- Toda identidad tiene alcance explícito
- Sin scope válido → sin existencia operativa

**Base de datos:** `aup_core`  
**Variable de entorno:** `DATABASE_CORE_URL`

---

### 📜 AUP_EVENT — Verdad Histórica

**Pregunta que responde:**  
*"¿Qué ocurrió realmente?"*

**Responsabilidad:**  
Registrar hechos inmutables con identidad, alcance, acción y resultado verificables.

**Contiene:**
- `events_aup` (tabla única de eventos)
  - `id` (secuencia)
  - `identity_id` (quién)
  - `tenant_id` (dónde)
  - `entidad` (qué)
  - `accion` (cómo)
  - `resultado` (permitido/denegado/error)
  - `hash_evento` (SHA-256)
  - `timestamp` (cuándo)
  - `metadata_json` (contexto)

**Axiomas:**
1. Append-only (solo INSERT, nunca UPDATE/DELETE)
2. Si no hay evento, no ocurrió para el sistema
3. Si hash cambia, hay manipulación detectable
4. Estado del sistema se puede reconstruir desde eventos

**Base de datos:** `aup_event`  
**Variable de entorno:** `DATABASE_EVENT_URL`

---

### ⚖️ AUP_GOV — Poder Explícito

**Pregunta que responde:**  
*"¿Por qué se permitió o negó algo?"*

**Responsabilidad:**  
Declarar explícitamente quién tiene poder, sobre qué, bajo qué límites.

**Contiene:**
- `authorities_gov` (AUP_AUTHORITY)
  - Quién tiene potestad de gobierno
  - Tipo: GLOBAL / FIRST_TIER
  
- `policies_gov` (AUP_POLICY)
  - Límites estructurales declarativos
  - Ejemplo: `{"max_dias_vigencia": 7}`
  
- `delegations_gov` (AUP_DELEGATION)
  - Transferencia explícita de poder
  - Temporal y revocable

**Axiomas:**
1. Gobierno precede a operación
2. Sin política asignada → denegado (default deny)
3. Si AUP_GOV falla → operación denegada
4. Revocación es inmediata (sin cache)

**Base de datos:** `aup_gov`  
**Variable de entorno:** `DATABASE_GOV_URL`

---

## III. JUSTIFICACIÓN AUP (POR QUÉ SEPARAR)

### 🔍 Razón 1: Responsabilidad Única
Cada dominio tiene **un solo tipo de verdad**:
- CORE: "¿Quién existe?"
- EVENT: "¿Qué pasó?"
- GOV: "¿Por qué se permitió?"

Mezclarlos es conceptualmente incorrecto en AUP.

### 🔒 Razón 2: Garantías de Integridad
- **AUP_EVENT** debe ser físicamente append-only
- **AUP_GOV** debe poder fallar sin afectar CORE
- **AUP_CORE** debe ser rápido (sin bloqueos de auditoría)

### 📊 Razón 3: Auditoría Forense
Si hay incidente legal:
- **EVENT** se exporta completo (cadena de custodia)
- **GOV** se exporta (evidencia de políticas activas)
- **CORE** se mantiene operativo

Un ataque a CORE no puede borrar EVENT.

### 💰 Razón 4: Monetización
Planes comerciales (FREE/PRO/ENTERPRISE) son **composiciones de políticas en GOV**.  
Si GOV está mezclado con CORE, no puedes venderlo como servicio independiente.

### 🚀 Razón 5: Escalabilidad
En producción:
- CORE puede escalar horizontalmente (read replicas)
- EVENT puede ir a WORM storage (Write Once Read Many)
- GOV puede tener cache separado (con invalidación explícita)

---

## IV. ARQUITECTURA NEON (DECLARADA)

### Proyecto Neon: `msp-axs-production`

**3 bases de datos independientes:**

```
┌─────────────────────────────────────────────┐
│          NEON PROJECT: msp-axs              │
├─────────────────────────────────────────────┤
│  📦 aup_core                                │
│     ↳ usuarios, condominios, visitas       │
│     ↳ Conexión: DATABASE_CORE_URL          │
├─────────────────────────────────────────────┤
│  📦 aup_event                               │
│     ↳ events_aup (append-only)             │
│     ↳ Conexión: DATABASE_EVENT_URL         │
├─────────────────────────────────────────────┤
│  📦 aup_gov                                 │
│     ↳ authorities, policies, delegations   │
│     ↳ Conexión: DATABASE_GOV_URL           │
└─────────────────────────────────────────────┘
```

---

## V. ESTRUCTURA DE CÓDIGO (DECLARATIVA)

```
backend/
├── db/
│   ├── core/
│   │   ├── engine.py          # Motor para aup_core
│   │   ├── session.py         # SessionLocal para CORE
│   │   └── models.py          # Usuario, Condominio, Visita, Scope
│   │
│   ├── event/
│   │   ├── engine.py          # Motor para aup_event
│   │   ├── session.py         # SessionLocal para EVENT
│   │   └── models.py          # Event (única tabla)
│   │
│   └── gov/
│       ├── engine.py          # Motor para aup_gov
│       ├── session.py         # SessionLocal para GOV
│       └── models.py          # Authority, Policy, Delegation
│
├── core/
│   ├── auth/                  # AUP_SESSION
│   ├── scope/                 # AUP_SCOPE
│   ├── event/                 # AUP_EVENT registry
│   └── gov/                   # AUP_GOV facade
│
└── routers/
    ├── auth_router.py         # Escribe en CORE
    ├── qr_router.py           # Lee GOV, escribe CORE + EVENT
    ├── preregistro_router.py  # Lee GOV, escribe CORE + EVENT
    └── condominios_router.py  # Lee GOV, escribe CORE + EVENT
```

---

## VI. VARIABLES DE ENTORNO (.env)

```bash
# ═══════════════════════════════════════════════════════════════
# AUP_CORE — Identidad y Alcance
# ═══════════════════════════════════════════════════════════════
DATABASE_CORE_URL=postgresql://user:pass@ep-xxxxx.neon.tech/aup_core?sslmode=require

# ═══════════════════════════════════════════════════════════════
# AUP_EVENT — Verdad Histórica (Append-Only)
# ═══════════════════════════════════════════════════════════════
DATABASE_EVENT_URL=postgresql://user:pass@ep-xxxxx.neon.tech/aup_event?sslmode=require

# ═══════════════════════════════════════════════════════════════
# AUP_GOV — Poder Explícito
# ═══════════════════════════════════════════════════════════════
DATABASE_GOV_URL=postgresql://user:pass@ep-xxxxx.neon.tech/aup_gov?sslmode=require

# ═══════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**❌ NO USAR:** `DATABASE_URL` genérica  
**✅ USAR:** Una variable por dominio AUP

---

## VII. MIGRACIONES (DECLARACIÓN POR DOMINIO)

### AUP_CORE
**Script:** `database/migration_core.sql` (crear si no existe)  
**Contiene:**
- usuarios
- condominios_exo
- msps_exo
- user_tenant_scope
- casetas
- visitas
- evidencias

**Ejecutar:**
```bash
psql $DATABASE_CORE_URL < database/migration_core.sql
```

### AUP_EVENT
**Script:** `database/migration_03_events_aup.sql` (ya existe)  
**Contiene:**
- events_aup

**Ejecutar:**
```bash
psql $DATABASE_EVENT_URL < database/migration_03_events_aup.sql
```

### AUP_GOV
**Script:** `database/migration_04_gov.sql` (ya existe)  
**Contiene:**
- authorities_gov
- policies_gov
- delegations_gov

**Ejecutar:**
```bash
psql $DATABASE_GOV_URL < database/migration_04_gov.sql
```

---

## VIII. SMOKE TEST (VERIFICACIÓN POST-DECLARACIÓN)

### Test 1: Login → CORE
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "test123"}'
```
**Esperado:** Usuario leído desde `aup_core.usuarios`

### Test 2: Generar QR → CORE + EVENT + GOV
```bash
curl -X POST http://localhost:8000/qr/generar \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visita_id": "vis_001", "dias_vigencia": 5}'
```
**Esperado:**
- Política leída desde `aup_gov.policies_gov`
- QR escrito en `aup_core.visitas`
- Evento escrito en `aup_event.events_aup`

### Test 3: Exceder política → EVENT con DENIED
```bash
curl -X POST http://localhost:8000/qr/generar \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"visita_id": "vis_001", "dias_vigencia": 30}'
```
**Esperado:**
- Status 403
- Evento en `aup_event` con `resultado = "denegado"`
- QR NO escrito en CORE

### Test 4: Cambiar política → Efecto inmediato
```sql
-- En aup_gov
UPDATE policies_gov 
SET limites = '{"max_dias_vigencia": 10}'
WHERE nombre = 'qr_vigencia_dias';
```
**Esperado:**
- Siguiente QR con 10 días → permitido
- Sin cache, sin reinicio

---

## IX. CRITERIO DE PILOTO (DECLARACIÓN FORMAL)

### ✅ MSP_AXS ESTÁ LISTO PARA PILOTO CUANDO:

1. **Las 3 bases existen en Neon**
   - `aup_core` responde
   - `aup_event` responde
   - `aup_gov` responde

2. **Los eventos caen donde deben**
   - Login → evento en `aup_event`
   - QR generado → evento en `aup_event`
   - Política denegada → evento en `aup_event`

3. **AUP_GOV gobierna al menos QR**
   - Política `qr_vigencia_dias` activa
   - Exceder límite → denegado
   - Cambiar política → efecto inmediato

4. **Smoke test pasa 4/4**
   - Login funciona
   - QR dentro de límite funciona
   - QR excediendo límite se deniega
   - Cambio de política se aplica

### ❌ NO ANTES
### ✅ JUSTO AHÍ

---

## X. CONSECUENCIAS DE ESTA DECLARACIÓN

### Para el código:
- Routers deben importar `get_core_db()`, `get_event_db()`, `get_gov_db()` según necesidad
- Ya no existe `get_db()` genérico
- Cada transacción declara explícitamente su dominio

### Para las migraciones:
- Cada migración va a su base
- No hay rollback cruzado (cada dominio es independiente)

### Para el deployment:
- Variables de entorno obligatorias (no opcionales)
- Health check debe verificar 3 conexiones

### Para la auditoría:
- Exportar `aup_event` es suficiente para trazabilidad completa
- No necesitas exportar CORE para auditoría legal

### Para la monetización:
- Planes comerciales son `SELECT * FROM aup_gov.policies_gov WHERE plan_type = 'PRO'`
- Cambiar plan es `UPDATE + registrar evento`

---

## XI. DECLARACIÓN FINAL

**MSP_AXS declara formalmente que:**

1. Su memoria persistente está separada en 3 dominios AUP
2. Cada dominio tiene responsabilidad única e independiente
3. La falla de un dominio no colapsa los otros
4. La auditoría forense es posible sin afectar operación
5. La monetización es estructural (no decorativa)

**Esta declaración es constitutiva.**  
**El sistema ahora existe formalmente.**

---

**Versión:** 3.0.0-aup-gov  
**Autor:** B10sp4rt4n  
**Arquitectura:** AUP (Architecture from Unified Principles)  
**Fecha:** Diciembre 29, 2024
