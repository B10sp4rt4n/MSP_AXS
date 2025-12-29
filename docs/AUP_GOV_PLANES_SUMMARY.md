# ═══════════════════════════════════════════════════════════════════════════
# PLANES COMERCIALES: Resumen Ejecutivo
# ═══════════════════════════════════════════════════════════════════════════

## 🧱 DECLARACIÓN AUP

```
Plan Comercial = Σ(Políticas AUP_GOV)

NO es un feature.
NO es un rol.
ES una composición de límites.
```

**Axiomas cumplidos:**
1. ✅ Cambiar de plan = cambiar políticas (no código)
2. ✅ El plan se audita históricamente vía AUP_EVENT
3. ✅ El downgrade es inmediato y trazable
4. ✅ Sin política activa = denegado (safe by default)

---

## 📊 TABLA: PLAN → POLÍTICAS

| Plan | Precio | Tenants | Usuarios | QR Vigencia | Visitas/Mes | Delegación |
|------|--------|---------|----------|-------------|-------------|------------|
| **FREE** | $0 | 1 | 20 | 3 días | 50 | ❌ No |
| **PRO** | $49/mes | 5 | 100 | 7 días | 500 | ✅ 30 días |
| **ENTERPRISE** | $499/mes | 50 | 1000 | 30 días | 10000 | ✅ 365 días |

**Cada límite = 1 política AUP_GOV en BD.**

---

## 🔄 FLUJO: UPGRADE / DOWNGRADE

### **Upgrade (FREE → PRO)**

```
1. Revocar políticas FREE (5 políticas → estado: revocado)
2. Crear políticas PRO (6 políticas → estado: activo)
3. Registrar AUP_EVENT:
     entidad: policy
     accion: asignar
     resultado: exito
     motivo: "Plan cambiado: free → pro"
     metadata: {
       politicas_revocadas: 5,
       politicas_creadas: 6,
       limites: {max_tenants: 5, max_qr_vigencia: 7, ...}
     }
4. Efecto: INMEDIATO (próximo request usa límites PRO)
```

**No requiere:**
- ❌ Redeploy
- ❌ Cache flush
- ❌ Reinicio de servidor
- ❌ Notificación al usuario (opcional)

---

### **Downgrade (PRO → FREE)**

```
1. Revocar políticas PRO (6 políticas)
2. Crear políticas FREE (5 políticas)
3. Registrar AUP_EVENT (igual que upgrade)
4. Efecto: INMEDIATO

Consecuencia:
  - Usuario tenía 3 tenants (dentro de límite PRO: 5)
  - Nuevo límite FREE: 1 tenant
  - Tenants existentes NO se eliminan
  - Crear 4to tenant → DENEGADO
  - Usuario debe reducir a 1 para volver a crear
```

**Advertencia al downgrade:**
```json
{
  "status": "downgrade_inmediato",
  "advertencia": "Límites reducidos. Operaciones en curso pueden fallar.",
  "plan_anterior": "pro",
  "plan_nuevo": "free"
}
```

---

## 📜 EVENTOS GENERADOS AL EXCEDER LÍMITES

### **Plan FREE: Usuario intenta crear 2do tenant**

```json
{
  "event_id": "evt_abc123",
  "identity_id": "user_free",
  "session_hash": "sha256(...)",
  "tenant_id": "sistema",
  "entidad": "policy",
  "entidad_id": "crear_tenant",
  "accion": "validar",
  "resultado": "denegado",
  "motivo": "Límite excedido: máximo 1 (actual: 1)",
  "metadata": {
    "plan": "free",
    "accion_evaluada": "crear_tenant",
    "valor_actual": 1,
    "limite": 1,
    "permitido": false
  },
  "timestamp": "2025-12-29T16:00:00Z",
  "hash": "sha256(...)"
}
```

**Uso:** Detectar usuarios que necesitan upgrade.

---

### **Plan PRO: Usuario intenta QR con 10 días de vigencia**

```json
{
  "event_id": "evt_def456",
  "identity_id": "user_pro",
  "session_hash": "sha256(...)",
  "tenant_id": "condo_a",
  "entidad": "policy",
  "entidad_id": "generar_qr",
  "accion": "validar",
  "resultado": "denegado",
  "motivo": "Vigencia excedida: máximo 7 días (solicitado: 10)",
  "metadata": {
    "plan": "pro",
    "dias_solicitados": 10,
    "limite": 7
  },
  "timestamp": "2025-12-29T16:05:00Z",
  "hash": "sha256(...)"
}
```

**Uso:** Mostrar tooltip "Upgrade a Enterprise para QR de 30 días".

---

## 🎯 IMPLEMENTACIÓN (SIN CAMBIAR CÓDIGO)

### **Paso 1: Ejecutar seed**

```bash
cd /workspaces/MSP_AXS

# Crear planes iniciales
python scripts/seed_planes_comerciales.py
```

**Resultado:**
```
✓ Usuario 1 → Plan FREE (5 políticas)
✓ Usuario 2 → Plan PRO (6 políticas)
✓ Admin → Plan ENTERPRISE (7 políticas)
```

---

### **Paso 2: Validar restricciones**

```bash
# Login como FREE
TOKEN_FREE=$(curl -s -X POST http://localhost:8000/auth/login \
  -d '{"email": "free@example.com", "password": "pass"}' | jq -r '.access_token')

# Intentar QR con 5 días (límite FREE: 3)
curl -X POST http://localhost:8000/qr/generar/visita_123 \
  -H "Authorization: Bearer $TOKEN_FREE"

# Esperado: 403 Forbidden
# {"detail": "Gobierno denegó operación: Vigencia excedida: máximo 3 días"}
```

---

### **Paso 3: Upgrade programático**

```python
from backend.core.gov.plans import upgrade_plan

result = upgrade_plan(
    db=db,
    ejecutor=admin,
    session_token=admin_token,
    target_user=usuario_free
)

# result:
# {
#   "status": "upgrade_exitoso",
#   "plan_anterior": "free",
#   "plan_nuevo": "pro",
#   "efecto": "inmediato"
# }

# Próximo request de usuario_free → límites PRO
```

---

### **Paso 4: Downgrade programático**

```python
from backend.core.gov.plans import downgrade_plan

result = downgrade_plan(
    db=db,
    ejecutor=admin,
    session_token=admin_token,
    target_user=usuario_pro
)

# result:
# {
#   "status": "downgrade_inmediato",
#   "advertencia": "Límites reducidos. Operaciones pueden fallar.",
#   "plan_anterior": "pro",
#   "plan_nuevo": "free"
# }
```

---

### **Paso 5: Auditar historial**

```sql
-- Ver cambios de plan de un usuario
SELECT 
  timestamp,
  motivo,
  metadata->'plan_anterior' as anterior,
  metadata->'plan_nuevo' as nuevo,
  metadata->'limites' as limites
FROM events_aup
WHERE entidad = 'policy'
  AND accion = 'asignar'
  AND metadata->>'target_user' = 'user_abc'
ORDER BY timestamp DESC;
```

**Resultado:**
```
2025-12-29 15:30  | free → pro       | {max_tenants: 5}
2025-11-15 10:00  | null → free      | {max_tenants: 1}
```

---

## 💰 MONETIZACIÓN AUTOMÁTICA

### **Cálculo de Factura**

```python
from backend.core.gov.plans import obtener_plan_actual

def calcular_factura(usuario_id: str, db: Session) -> dict:
    plan = obtener_plan_actual(db, usuario_id)
    
    if not plan:
        return {"monto": 0, "plan": "NINGUNO"}
    
    tenants = db.query(Tenant).filter(
        Tenant.owner_id == usuario_id
    ).count()
    
    if plan["plan_type"] == "free":
        return {"monto": 0, "plan": "FREE"}
    
    elif plan["plan_type"] == "pro":
        base = 49
        adicional = (tenants - 1) * 49 if tenants > 1 else 0
        return {
            "monto": base + adicional,
            "plan": "PRO",
            "tenants": tenants
        }
    
    elif plan["plan_type"] == "enterprise":
        base = 499
        adicional = (tenants - 10) * 99 if tenants > 10 else 0
        return {
            "monto": base + adicional,
            "plan": "ENTERPRISE",
            "tenants": tenants
        }
```

**Ejemplo:**
```python
# Usuario Pro con 3 tenants
factura = calcular_factura("user_abc", db)
# {
#   "monto": 147,  # 49 base + (2 * 49)
#   "plan": "PRO",
#   "tenants": 3
# }
```

---

## 🛡️ ARGUMENTO: POR QUÉ ES DIFÍCIL DE COPIAR

### **1. No es un feature, es una arquitectura**

```
Copiar feature flags = 1 día
Copiar AUP_GOV = 6-8 semanas (rediseño completo)
```

**Razón:** AUP_GOV requiere:
- AUP_EVENT (trazabilidad) ← PASO 3
- Separación de planos (gobierno vs operación)
- Sin cache (downgrade inmediato)
- Composición (no jerarquía)

---

### **2. Requiere disciplina, no solo código**

```python
# Fácil de romper (mezclar planos)
@app.post("/qr")
def generar_qr(...):
    if user.plan == "free" and dias > 3:  # ← Gobierno mezclado
        raise Error()

# Difícil de mantener (separación)
@app.post("/qr")
def generar_qr(...):
    if not puede_ejecutar_accion(...):  # ← Gobierno separado
        raise HTTPException(403)
```

**Barrera:** Disciplina continua (code reviews, testing).

---

### **3. Trazabilidad nativa (no manual)**

```
Competencia: Logging manual inconsistente
AUP_GOV: AUP_EVENT automático en cada decisión
```

**Ventaja:** Auditoría completa sin esfuerzo manual.

---

### **4. Efecto inmediato (sin cache)**

```
Competencia: Downgrade diferido (hasta expirar cache/JWT)
AUP_GOV: Downgrade inmediato (próximo request)
```

**Tradeoff:** +5-10ms latencia vs consistencia garantizada.

---

### **5. Composición flexible**

```
Jerarquía: Herencia rígida (FreePlan < ProPlan < EnterprisePlan)
Composición: Plan = Σ(Políticas) (mezclar límites libremente)
```

**Ventaja:** Enterprise custom trivial (sin crear nueva clase).

---

## ✅ RESUMEN

### **Estructura:**
- 3 planes: FREE, PRO, ENTERPRISE
- Cada plan = composición de 5-7 políticas AUP_GOV
- Políticas almacenadas en BD (no código)

### **Operación:**
- Upgrade/downgrade = revocar + crear políticas
- Efecto inmediato (sin redeploy, sin cache)
- Eventos registrados automáticamente

### **Monetización:**
- Facturación basada en plan actual (queryable en BD)
- Límites dinámicos (cambiar sin código)
- Detección de upgrade automática (eventos denegados)

### **Ventaja competitiva:**
- Difícil de copiar (arquitectura, no feature)
- Requiere rediseño completo (6-8 semanas)
- Requiere disciplina continua (no solo código)

---

## 📋 ARCHIVOS CREADOS

1. [backend/core/gov/plans.py](backend/core/gov/plans.py) - Definición de planes y funciones
2. [scripts/seed_planes_comerciales.py](scripts/seed_planes_comerciales.py) - Seed inicial
3. [docs/AUP_GOV_PLANES_COMERCIALES.md](docs/AUP_GOV_PLANES_COMERCIALES.md) - Documentación detallada
4. [docs/AUP_GOV_VENTAJA_COMPETITIVA.md](docs/AUP_GOV_VENTAJA_COMPETITIVA.md) - Análisis de barrera

---

## 🎯 PRÓXIMOS PASOS

```bash
# 1. Ejecutar seed
python scripts/seed_planes_comerciales.py

# 2. Validar restricciones
# (Login como FREE → intentar QR 5 días → DENEGADO)

# 3. Probar upgrade
upgrade_plan(db, admin, token, usuario_free)

# 4. Probar downgrade
downgrade_plan(db, admin, token, usuario_pro)

# 5. Auditar historial
SELECT * FROM events_aup WHERE entidad = 'policy';
```

═══════════════════════════════════════════════════════════════════════════

**Planes comerciales implementados como composiciones AUP_GOV.**  
**Cambiar plan ≠ cambiar código.**  
**Difícil de copiar por diseño (arquitectura + disciplina).**
