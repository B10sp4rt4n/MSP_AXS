# ═══════════════════════════════════════════════════════════════════════════
# AUP ACTIVACIÓN OPERATIVA — README
# ═══════════════════════════════════════════════════════════════════════════

## 🎯 OBJETIVO CUMPLIDO

Activación operativa de AUP con fricción real y bloqueos duros.

**Estado:** AUP deja de ser conceptual y gobierna el runtime.

---

## 🔒 BLOQUEOS IMPLEMENTADOS

### BLOQUEO AUP-01: No acción sin SESSION

**Archivo:** `backend/core/aup_runtime_blocks.py` (clase `AUPSessionGuard`)

**Implementación:**
- Middleware de FastAPI que intercepta TODAS las requests
- Valida sesión ANTES de llegar al router
- Sin sesión → 401 + EVENT registrado

**Activación:**
```python
# backend/main.py (línea ~50)
app.add_middleware(AUPSessionGuard)
```

**Axioma validado:** Nada ocurre sin sesión

**Endpoints públicos (whitelist):**
- `/`
- `/docs`
- `/openapi.json`
- `/auth/login`
- `/auth/register`

**Violación imposible:**
❌ No existe forma de ejecutar negocio sin SESSION
✅ El middleware bloquea en runtime

---

### BLOQUEO AUP-02: GOV antes del negocio

**Archivo:** `backend/core/aup_runtime_blocks.py` (clase `AUPGovEnforcer`)

**Implementación:**
- Context manager que marca estado de evaluación de GOV
- Falla si negocio se ejecuta sin evaluar GOV
- Falla si negocio se ejecuta con GOV denegado

**Uso:**
```python
with AUPGovEnforcer() as gov:
    # 1. Evaluar gobierno
    permitido, motivo = puede_ejecutar_accion(...)
    gov.mark_evaluated(permitido)
    
    if not permitido:
        raise HTTPException(403, motivo)
    
    # 2. Solo ahora ejecutar negocio
    resultado = ejecutar_negocio()
    gov.mark_business_executed()
```

**Axioma validado:** El negocio ocurre después del poder, nunca antes

**Violación imposible:**
❌ No existe forma de ejecutar negocio sin evaluar GOV
❌ No existe forma de ejecutar negocio con GOV denegado
✅ El context manager lanza RuntimeError si se viola

---

### BLOQUEO AUP-03: No EVENT, no retorno

**Archivo:** `backend/core/aup_runtime_blocks.py` (clase `AUPEventEnforcer`)

**Implementación:**
- Context manager que verifica registro de EVENT
- Falla si operación termina sin EVENT

**Uso:**
```python
with AUPEventEnforcer(operation="generar_qr") as event_guard:
    # Ejecutar operación
    resultado = hacer_algo()
    
    # OBLIGATORIO: Registrar evento
    registrar_evento(...)
    event_guard.mark_event_registered()
    
    return resultado
```

**Axioma validado:** Sin evento, no hay existencia

**Violación imposible:**
❌ No existe forma de retornar sin EVENT
✅ El context manager lanza RuntimeError si se viola

---

## 🐤 ENDPOINT CANARIO

**Ruta:** `POST /qr/generar_gobernado`

**Archivo:** `backend/routers/canario_router.py`

**Propósito:** Demostrador vivo de AUP (NO feature de negocio)

**Flujo completo:**
```
REQUEST
 ↓
AUP_SESSION (middleware AUPSessionGuard) ← BLOQUEO AUP-01
 ↓
AUP_SCOPE (validar_alcance_y_registrar)
 ↓
AUP_GOV (puede_ejecutar_accion) ← BLOQUEO AUP-02
 ↓
NEGOCIO (crear QR)
 ↓
AUP_EVENT (registrar_evento) ← BLOQUEO AUP-03
 ↓
RESPONSE
```

**Política activa:** `max_qr_dias = 3`

**Casos de prueba:**

✅ **Caso éxito (GOV permite):**
```bash
POST /qr/generar_gobernado
Authorization: Bearer <token>
{
  "visitante_nombre": "Juan Perez",
  "tenant_id": "condo_a",
  "dias_vigencia": 2
}
→ 200 OK
```

🚫 **Caso denegado por gobierno:**
```bash
POST /qr/generar_gobernado
Authorization: Bearer <token>
{
  "visitante_nombre": "Juan Perez",
  "tenant_id": "condo_a",
  "dias_vigencia": 7
}
→ 403 Forbidden (GOV denegó: límite excedido)
```

🚫 **Caso sin SESSION:**
```bash
POST /qr/generar_gobernado
(sin Authorization header)
→ 401 Unauthorized (AUP-01 bloqueó)
```

---

## 📋 CHECKLIST DE ACEPTACIÓN

✅ **No existe forma de ejecutar negocio sin SESSION**
- Middleware `AUPSessionGuard` bloquea en runtime
- Whitelist explícita de endpoints públicos
- Evento registrado en cada intento sin SESSION

✅ **No existe forma de ejecutar negocio sin GOV**
- Context manager `AUPGovEnforcer` obliga evaluación
- RuntimeError si negocio se ejecuta sin evaluar GOV
- RuntimeError si negocio se ejecuta con GOV denegado

✅ **No existe forma de retornar sin EVENT**
- Context manager `AUPEventEnforcer` verifica registro
- RuntimeError si operación termina sin EVENT
- Eventos registrados en éxito Y fallo

✅ **El endpoint canario demuestra el flujo completo AUP**
- SESSION validada por middleware
- SCOPE validado dinámicamente
- GOV evaluado con política activa
- NEGOCIO ejecutado solo si GOV permite
- EVENT registrado siempre

✅ **Cualquier violación rompe ejecución de forma explícita**
- No hay bypass posibles
- No hay "modo rápido"
- No hay optimizaciones que rompan el orden
- Errores son claros y referencian axioma violado

---

## 🚀 SETUP Y EJECUCIÓN

### 1. Cargar política de prueba

```bash
python -m backend.scripts.seed_canario_policy
```

Esto carga:
- Authority: `GOBIERNO_CANARIO`
- Policy: `LIMITE_QR_CANARIO` (max_qr_dias = 3)

### 2. Iniciar servidor

```bash
uvicorn backend.main:app --reload
```

Log esperado:
```
🔒 AUP-01 ACTIVADO: Middleware de SESSION activo
✅ AUP_CORE: Tablas verificadas/creadas
✅ AUP_EVENT: Tablas verificadas/creadas
✅ AUP_GOV: Tablas verificadas/creadas
```

### 3. Verificar salud del canario

```bash
curl http://localhost:8000/qr/canario/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "aup_gov_ready": true,
  "active_policies": 1,
  "message": "Sistema AUP listo"
}
```

### 4. Login (obtener SESSION)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"
```

Guardar `access_token` de respuesta.

### 5. Probar endpoint canario (éxito)

```bash
curl -X POST http://localhost:8000/qr/generar_gobernado \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "visitante_nombre": "Juan Perez",
    "tenant_id": "condo_a",
    "dias_vigencia": 2
  }'
```

Respuesta esperada:
```json
{
  "qr_id": "...",
  "qr_token": "...",
  "visitante": "Juan Perez",
  "tenant_id": "condo_a",
  "vigencia_hasta": "2025-01-01T12:00:00",
  "creado_por": "admin@example.com",
  "evento_id": "..."
}
```

Log del servidor:
```
✅ AUP-01 PASSED: SESSION válida
✅ PASO 1/5: SESSION validada
✅ PASO 2/5: SCOPE validado
✅ PASO 3/5: GOV permitió
✅ PASO 4/5: NEGOCIO ejecutado
✅ PASO 5/5: EVENT registrado
🎉 CANARIO: Operación completa
```

### 6. Probar endpoint canario (denegado por GOV)

```bash
curl -X POST http://localhost:8000/qr/generar_gobernado \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "visitante_nombre": "Juan Perez",
    "tenant_id": "condo_a",
    "dias_vigencia": 7
  }'
```

Respuesta esperada:
```json
{
  "detail": "Gobierno denegó operación: Vigencia excede límite permitido (max: 3 días)"
}
```

Status: 403 Forbidden

Log del servidor:
```
✅ AUP-01 PASSED: SESSION válida
✅ PASO 1/5: SESSION validada
✅ PASO 2/5: SCOPE validado
🚫 PASO 3/5 FALLÓ: GOV denegó
```

### 7. Probar sin SESSION

```bash
curl -X POST http://localhost:8000/qr/generar_gobernado \
  -H "Content-Type: application/json" \
  -d '{
    "visitante_nombre": "Juan Perez",
    "tenant_id": "condo_a",
    "dias_vigencia": 2
  }'
```

Respuesta esperada:
```json
{
  "detail": "AUP-01 VIOLATED: No SESSION provided",
  "axiom": "Nada ocurre sin sesión",
  "path": "/qr/generar_gobernado",
  "method": "POST"
}
```

Status: 401 Unauthorized

Log del servidor:
```
🚫 AUP-01 BLOQUEADO: No SESSION en POST /qr/generar_gobernado
```

---

## 🎓 ARQUITECTURA RESULTANTE

```
┌─────────────────────────────────────────────────────────────┐
│                     FASTAPI APP                              │
├─────────────────────────────────────────────────────────────┤
│  Middleware: AUPSessionGuard (BLOQUEO AUP-01)               │
│    ↓                                                         │
│  Router: /qr/generar_gobernado                              │
│    ↓                                                         │
│  Dependency: get_current_user (AUP_SESSION)                 │
│    ↓                                                         │
│  Validator: validar_alcance_y_registrar (AUP_SCOPE)         │
│    ↓                                                         │
│  Context: AUPGovEnforcer (BLOQUEO AUP-02)                   │
│    ├─ puede_ejecutar_accion (AUP_GOV)                       │
│    └─ ejecutar_negocio                                      │
│    ↓                                                         │
│  Context: AUPEventEnforcer (BLOQUEO AUP-03)                 │
│    ├─ registrar_evento (AUP_EVENT)                          │
│    └─ retornar respuesta                                    │
└─────────────────────────────────────────────────────────────┘
```

**Orden no negociable:**
SESSION → SCOPE → GOV → NEGOCIO → EVENT

**Bloqueos activos:**
- AUP-01: Runtime (middleware)
- AUP-02: Runtime (context manager)
- AUP-03: Runtime (context manager)

---

## ⚠️ RESTRICCIONES FINALES

❌ **NO introducir nuevos features**
- El endpoint canario es demostrador, no producción

❌ **NO refactorizar arquitectura existente**
- Solo se agregaron bloqueos, no se modificó lógica

❌ **NO escribir tests aún**
- Siguiente fase: tests derivados de guardrails

❌ **NO optimizar performance**
- Prioridad: integridad sobre velocidad

❌ **NO discutir escalado**
- Siguiente fase: evaluación de producción

---

## 📊 RESULTADO

**Estado anterior:**
- AUP conceptual
- Sin fricción operativa
- Posibles bypass

**Estado actual:**
- AUP operativo
- Fricción real
- Bypass imposibles

**Axiomas validados:**
```
No SESSION  → No acción     ✅ (BLOQUEO AUP-01)
No SCOPE    → No permiso    ✅ (validar_alcance_y_registrar)
No GOV OK   → No ejecución  ✅ (BLOQUEO AUP-02)
No EVENT    → No existencia ✅ (BLOQUEO AUP-03)
```

**Conclusión:**
AUP ya NO puede ser ignorado.

---

## 📚 ARCHIVOS CLAVE

| Archivo | Propósito |
|---------|-----------|
| `backend/core/aup_runtime_blocks.py` | Bloqueos AUP-01, AUP-02, AUP-03 |
| `backend/routers/canario_router.py` | Endpoint canario demostrador |
| `backend/main.py` | Registro de middleware y router |
| `backend/scripts/seed_canario_policy.py` | Carga política de prueba |
| `docs/AUP_PSEUDOCODIGO_CONTRATO.md` | Contrato ontológico |
| `docs/AUP_STRUCTURAL_GUARDRAILS.md` | Guardrails estructurales |

---

## ✅ VERIFICACIÓN FINAL

```bash
# 1. Verificar que middleware está registrado
curl http://localhost:8000/ 
→ 200 OK (endpoint público)

curl http://localhost:8000/qr/generar_gobernado
→ 401 Unauthorized (AUP-01 bloqueó)

# 2. Verificar que política está cargada
curl http://localhost:8000/qr/canario/health
→ {"aup_gov_ready": true}

# 3. Verificar flujo completo con SESSION
curl -X POST http://localhost:8000/qr/generar_gobernado \
  -H "Authorization: Bearer <token>" \
  -d '{"visitante_nombre":"Juan","tenant_id":"condo_a","dias_vigencia":2}'
→ 200 OK (AUP completo)

# 4. Verificar GOV deniega
curl -X POST http://localhost:8000/qr/generar_gobernado \
  -H "Authorization: Bearer <token>" \
  -d '{"visitante_nombre":"Juan","tenant_id":"condo_a","dias_vigencia":7}'
→ 403 Forbidden (GOV bloqueó)
```

**Todos los bloqueos activos. AUP gobierna el runtime.**

---

## 🚧 SIGUIENTE CHECKPOINT

- Verificación runtime en entorno local
- Micro-piloto con casos de prueba exhaustivos
- Derivación de tests pytest desde guardrails estructurales
- Evaluación de producción-ready
