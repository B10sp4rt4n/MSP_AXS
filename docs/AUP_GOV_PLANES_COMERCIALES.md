# ═══════════════════════════════════════════════════════════════════════════
# PLANES COMERCIALES: Composiciones AUP_GOV
# ═══════════════════════════════════════════════════════════════════════════

## 🧱 DECLARACIÓN AUP

**Un plan comercial NO es un feature.**  
**Es una COMPOSICIÓN de políticas AUP_GOV.**

```
Plan = Σ(Políticas)

Cambiar plan = Revocar(P_anteriores) + Crear(P_nuevas)
```

**Axioma fundamental:**  
Sin política activa que permita = operación denegada (safe by default).

---

## 📊 TABLA: PLAN → POLÍTICAS

### **Plan FREE ($0/mes)**

| Política | Límite | Operación Bloqueada | AUP_EVENT Generado |
|----------|--------|---------------------|---------------------|
| `max_tenants` | 1 | Crear 2do condominio | `resultado: denegado, motivo: "Límite excedido: máximo 1"` |
| `max_usuarios` | 20 | Crear usuario #21 | `resultado: denegado, motivo: "Límite de usuarios excedido"` |
| `max_qr_vigencia` | 3 días | QR con vigencia > 3 días | `resultado: denegado, motivo: "Vigencia excedida: máximo 3 días"` |
| `max_visitas_mes` | 50 | Crear visita #51 en el mes | `resultado: denegado, motivo: "Límite mensual excedido"` |
| `delegacion_permitida` | `False` | Intentar delegar poder | `resultado: denegado, motivo: "Delegación no permitida en plan Free"` |

**Objetivo:** Probar sistema con máximas restricciones.  
**Monetización:** Gratis (hook para upgrade).

---

### **Plan PRO ($49/mes por tenant)**

| Política | Límite | Operación Bloqueada | AUP_EVENT Generado |
|----------|--------|---------------------|---------------------|
| `max_tenants` | 5 | Crear 6to condominio | `resultado: denegado, motivo: "Límite excedido: máximo 5"` |
| `max_usuarios` | 100 | Crear usuario #101 | `resultado: denegado, motivo: "Límite de usuarios excedido"` |
| `max_qr_vigencia` | 7 días | QR con vigencia > 7 días | `resultado: denegado, motivo: "Vigencia excedida: máximo 7 días"` |
| `max_visitas_mes` | 500 | Crear visita #501 en el mes | `resultado: denegado, motivo: "Límite mensual excedido"` |
| `delegacion_permitida` | `True` | - | - |
| `delegacion_max_dias` | 30 días | Delegación > 30 días | `resultado: denegado, motivo: "Delegación excede 30 días"` |

**Objetivo:** Uso productivo con límites razonables.  
**Monetización:** Modelo SaaS estándar.

---

### **Plan ENTERPRISE ($499/mes + custom)**

| Política | Límite | Operación Bloqueada | AUP_EVENT Generado |
|----------|--------|---------------------|---------------------|
| `max_tenants` | 50 | Crear tenant #51 | `resultado: denegado, motivo: "Límite excedido: máximo 50"` |
| `max_usuarios` | 1000 | Crear usuario #1001 | `resultado: denegado, motivo: "Límite de usuarios excedido"` |
| `max_qr_vigencia` | 30 días | QR con vigencia > 30 días | `resultado: denegado, motivo: "Vigencia excedida: máximo 30 días"` |
| `max_visitas_mes` | 10000 | Crear visita #10001 | `resultado: denegado, motivo: "Límite mensual excedido"` |
| `delegacion_permitida` | `True` | - | - |
| `delegacion_max_dias` | 365 días | Delegación > 1 año | `resultado: denegado, motivo: "Delegación excede 365 días"` |
| `politicas_personalizadas` | `True` | - | Permite crear políticas custom |

**Objetivo:** Clientes grandes sin límites operativos significativos.  
**Monetización:** High-touch + personalización.

---

## 🔄 FLUJO: UPGRADE / DOWNGRADE

### **Upgrade Progresivo**

```
FREE → PRO → ENTERPRISE

Estado inicial (FREE):
  policies_activas: 5 (restrictivas)
  
Upgrade a PRO:
  1. Revocar políticas FREE (estado: revocado)
  2. Crear políticas PRO (límites ampliados)
  3. Registrar AUP_EVENT:
       entidad: policy
       accion: asignar
       resultado: exito
       motivo: "Plan cambiado: free → pro"
       metadata: {
         politicas_revocadas: 5,
         politicas_creadas: 6,
         limites_nuevos: {...}
       }
  4. Efecto: INMEDIATO (próximo request usa nuevas políticas)

Upgrade a ENTERPRISE:
  1. Revocar políticas PRO
  2. Crear políticas ENTERPRISE
  3. Registrar AUP_EVENT
  4. Efecto: INMEDIATO
```

**Axioma:** Upgrade = ampliar límites (más permisivo).

---

### **Downgrade Inmediato**

```
ENTERPRISE → PRO → FREE

Estado inicial (ENTERPRISE):
  max_tenants: 50
  tenants_actuales: 8
  
Downgrade a PRO:
  1. Revocar políticas ENTERPRISE
  2. Crear políticas PRO (max_tenants: 5)
  3. Registrar AUP_EVENT:
       entidad: policy
       accion: asignar
       resultado: exito
       motivo: "Plan cambiado: enterprise → pro"
       metadata: {
         advertencia: "Límites reducidos. Operaciones pueden fallar."
       }
  4. Efecto: INMEDIATO
  5. Consecuencia: Si tiene 8 tenants pero límite ahora es 5:
       - Tenants existentes NO se eliminan
       - Crear 9no tenant → DENEGADO
       - Usuario debe reducir a 5 para volver a crear

Estado después de downgrade a FREE:
  max_tenants: 1
  tenants_actuales: 8
  
  Operaciones:
    - Crear tenant → DENEGADO
    - Generar QR vigencia > 3 días → DENEGADO
    - Delegar poder → DENEGADO
```

**Axioma:** Downgrade = reducir límites (más restrictivo).  
**Consecuencia:** Operaciones en curso pueden fallar inmediatamente.

---

## 📜 AUDITABILIDAD VÍA AUP_EVENT

### **Historial de Planes de un Usuario**

```sql
-- Ver todos los cambios de plan
SELECT 
  timestamp,
  motivo,
  metadata->'plan_anterior' as plan_anterior,
  metadata->'plan_nuevo' as plan_nuevo,
  metadata->'limites' as limites
FROM events_aup
WHERE entidad = 'policy'
  AND accion = 'asignar'
  AND metadata->>'target_user' = 'user_abc'
ORDER BY timestamp DESC;
```

**Resultado:**
```
timestamp             | plan_anterior | plan_nuevo  | limites
----------------------|---------------|-------------|------------------
2025-12-29 15:30:00  | pro           | enterprise  | {"max_tenants":50}
2025-11-15 10:00:00  | free          | pro         | {"max_tenants":5}
2025-10-01 09:00:00  | null          | free        | {"max_tenants":1}
```

**Ventaja:** Trazabilidad completa de facturación y compliance.

---

### **Detección de Intentos de Abuso**

```sql
-- Usuarios que exceden límites repetidamente
SELECT 
  identity_id,
  COUNT(*) as intentos_denegados,
  accion,
  motivo
FROM events_aup
WHERE entidad = 'policy'
  AND resultado = 'denegado'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY identity_id, accion, motivo
HAVING COUNT(*) > 10
ORDER BY intentos_denegados DESC;
```

**Uso:** Identificar usuarios que necesitan upgrade o están abusando del sistema.

---

## 🚀 IMPLEMENTACIÓN (SIN CAMBIAR CÓDIGO)

### **Paso 1: Seed de Planes**

```bash
# Después de seed_gov_bootstrap.py
python scripts/seed_planes_comerciales.py
```

**Resultado:**
- Usuario 1 → Plan FREE (5 políticas)
- Usuario 2 → Plan PRO (6 políticas)
- Admin → Plan ENTERPRISE (7 políticas)

---

### **Paso 2: Validación**

```bash
# Login como usuario FREE
TOKEN_FREE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "free@example.com", "password": "pass"}' \
  | jq -r '.access_token')

# Intentar crear QR con vigencia 5 días (límite FREE: 3 días)
curl -X POST http://localhost:8000/qr/generar/visita_123 \
  -H "Authorization: Bearer $TOKEN_FREE"

# Esperado: 403 Forbidden
# {
#   "detail": "Gobierno denegó operación: Vigencia excedida: máximo 3 días (solicitado: 7)"
# }
```

---

### **Paso 3: Upgrade Dinámico**

```python
from backend.core.gov.plans import upgrade_plan

# Usuario en Plan FREE solicita upgrade
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
#   "politicas_revocadas": 5,
#   "politicas_creadas": 6,
#   "efecto": "inmediato"
# }
```

**Efecto:** Próximo request de `usuario_free` usa límites PRO (sin cache, sin redeploy).

---

### **Paso 4: Downgrade Inmediato**

```python
from backend.core.gov.plans import downgrade_plan

# Empresa reduce presupuesto, downgrade a FREE
result = downgrade_plan(
    db=db,
    ejecutor=admin,
    session_token=admin_token,
    target_user=usuario_pro
)

# result:
# {
#   "status": "downgrade_inmediato",
#   "advertencia": "Límites reducidos. Operaciones en curso pueden fallar.",
#   "plan_anterior": "pro",
#   "plan_nuevo": "free",
#   "politicas_revocadas": 6,
#   "politicas_creadas": 5,
#   "efecto": "inmediato"
# }
```

---

## 💰 MONETIZACIÓN NATIVA

### **Modelo de Precios Automático**

| Plan | Precio Base | Por Tenant Adicional | Límites |
|------|-------------|----------------------|---------|
| FREE | $0 | No permitido | 1 tenant, 20 usuarios, QR 3 días |
| PRO | $49/mes | $49/tenant | 5 tenants, 100 usuarios, QR 7 días |
| ENTERPRISE | $499/mes | $99/tenant | 50 tenants, 1000 usuarios, QR 30 días |

**Facturación:**
```python
def calcular_factura(usuario_id: str, db: Session) -> dict:
    plan = obtener_plan_actual(db, usuario_id)
    tenants_activos = db.query(Tenant).filter(
        Tenant.owner_id == usuario_id
    ).count()
    
    if plan["plan_type"] == "free":
        return {"monto": 0, "plan": "FREE"}
    
    elif plan["plan_type"] == "pro":
        precio_base = 49
        precio_adicional = (tenants_activos - 1) * 49 if tenants_activos > 1 else 0
        return {
            "monto": precio_base + precio_adicional,
            "plan": "PRO",
            "tenants": tenants_activos
        }
    
    elif plan["plan_type"] == "enterprise":
        precio_base = 499
        precio_adicional = (tenants_activos - 10) * 99 if tenants_activos > 10 else 0
        return {
            "monto": precio_base + precio_adicional,
            "plan": "ENTERPRISE",
            "tenants": tenants_activos
        }
```

**Ventaja:** Facturación automática basada en políticas activas (no hardcoded).

---

## 🛡️ POR QUÉ ESTO ES DIFÍCIL DE COPIAR

### **1. Gobierno Estructural (No Feature Flags)**

**Competencia típica:**
```python
# Feature flags tradicionales
if user.plan == "free":
    if qr_dias > 3:
        raise Error("Upgrade to Pro")

# Problemas:
# - Lógica dispersa en controllers
# - No auditable
# - Difícil de testear
# - Cambiar límite = redeploy
```

**AUP_GOV:**
```python
# Gobierno centralizado
permitido, motivo = puede_ejecutar_accion(
    db, usuario, token,
    accion="generar_qr",
    metadata={"dias_vigencia": dias}
)

# Ventajas:
# ✓ Lógica centralizada (policy.py)
# ✓ Auditable (AUP_EVENT)
# ✓ Testeable (mockear políticas)
# ✓ Cambiar límite = UPDATE en BD
```

**Barrera de entrada:** Requiere arquitectura AUP desde cero (no se agrega después).

---

### **2. Trazabilidad Nativa (Compliance First-Class)**

**Competencia típica:**
```python
# Logging manual
logger.info(f"User {user.id} denied: plan limit")

# Problemas:
# - Inconsistente
# - No estructurado
# - No reconstruible
```

**AUP_GOV:**
```python
# Evento estructurado automático
registrar_evento(
    entidad="policy",
    accion="validar",
    resultado="denegado",
    motivo="Límite excedido: máximo 5",
    metadata={"plan": "pro", "valor_actual": 5}
)

# Ventajas:
# ✓ Siempre consistente
# ✓ Estructurado (queryable)
# ✓ Reconstruible (event sourcing parcial)
# ✓ Compliance automático
```

**Barrera de entrada:** Requiere AUP_EVENT implementado (PASO 3).

---

### **3. Separación de Planos (Gobierno vs Operación)**

**Competencia típica:**
```python
# Router decide límites
@app.post("/qr")
def generar_qr(...):
    if user.plan == "free" and dias > 3:
        raise Error(...)
    # Lógica de negocio mezclada con gobierno

# Problemas:
# - Acoplamiento alto
# - Testing complejo
# - Cambios riesgosos
```

**AUP_GOV:**
```python
# Router consulta, gobierno decide
@app.post("/qr")
def generar_qr(...):
    if not puede_ejecutar_accion(...):
        raise HTTPException(403)
    # Solo lógica de negocio

# Ventajas:
# ✓ Desacoplado
# ✓ Testing simple (mockear gobierno)
# ✓ Cambios seguros (gobierno aislado)
```

**Barrera de entrada:** Requiere disciplina arquitectónica (no solo código).

---

### **4. Efecto Inmediato (Sin Cache)**

**Competencia típica:**
```python
# Cache de plan en JWT/Redis
payload = {"user_id": 123, "plan": "pro"}

# Problemas:
# - Downgrade no inmediato (hasta refresh)
# - Inconsistencias (cache vs BD)
# - Seguridad débil (JWT falsificado)
```

**AUP_GOV:**
```python
# Políticas en BD, sin cache
politicas = db.query(Policy).filter(
    Policy.target_identity == user_id,
    Policy.estado == "activo"
).all()

# Ventajas:
# ✓ Downgrade inmediato (próximo request)
# ✓ Consistencia (source of truth = BD)
# ✓ Seguridad fuerte (no cacheable)
```

**Barrera de entrada:** Requiere diseño sin cache (contra-intuitivo para muchos).

---

### **5. Composición vs Jerarquía**

**Competencia típica:**
```python
# Jerarquía de roles
class FreePlan(BasePlan):
    max_tenants = 1
    
class ProPlan(BasePlan):
    max_tenants = 5

# Problemas:
# - Herencia rígida
# - Difícil personalizar (Enterprise custom)
# - Cambio = nuevo deploy
```

**AUP_GOV:**
```python
# Composición de políticas
plan_custom = [
    Policy(accion="crear_tenant", limites={"max_count": 15}),
    Policy(accion="generar_qr", limites={"max_dias": 14}),
    # Mezclar límites de Pro + Enterprise
]

# Ventajas:
# ✓ Composición flexible
# ✓ Personalización trivial (Enterprise custom)
# ✓ Cambio = INSERT en BD
```

**Barrera de entrada:** Requiere pensar en composición (no herencia).

---

## ✅ RESUMEN: VENTAJA COMPETITIVA

| Dimensión | Competencia Típica | AUP_GOV | Barrera de Copia |
|-----------|-------------------|---------|------------------|
| **Límites** | Hardcoded | Políticas en BD | Media |
| **Cambios** | Redeploy | UPDATE en BD | Media |
| **Auditoría** | Logging manual | AUP_EVENT automático | **Alta** |
| **Downgrade** | Diferido (cache) | Inmediato | Media |
| **Personalización** | Herencia | Composición | **Alta** |
| **Testing** | Complejo | Simple (mockear políticas) | Media |
| **Compliance** | Manual | Nativo | **Alta** |

**Dificultad total de copiar:** **ALTA**

**Razón:** No es un feature, es una arquitectura.  
Copiar feature flags es fácil.  
Copiar separación de planos + trazabilidad + composición = **rediseñar sistema completo**.

---

## 🎯 PRÓXIMOS PASOS

1. **Ejecutar seed:**
   ```bash
   python scripts/seed_planes_comerciales.py
   ```

2. **Validar restricciones por plan:**
   - Login como FREE → intentar QR 5 días → DENEGADO
   - Login como PRO → intentar QR 5 días → PERMITIDO

3. **Probar upgrade:**
   ```python
   upgrade_plan(db, admin, token, usuario_free)
   # Usuario FREE ahora tiene límites PRO
   ```

4. **Probar downgrade:**
   ```python
   downgrade_plan(db, admin, token, usuario_pro)
   # Usuario PRO ahora tiene límites FREE (inmediato)
   ```

5. **Auditar historial:**
   ```sql
   SELECT * FROM events_aup 
   WHERE entidad = 'policy' 
     AND accion = 'asignar'
   ORDER BY timestamp DESC;
   ```

═══════════════════════════════════════════════════════════════════════════

**Planes comerciales implementados como composiciones AUP_GOV.**  
**Cambiar plan = cambiar políticas (sin código).**  
**Difícil de copiar por diseño (no por complejidad).**
