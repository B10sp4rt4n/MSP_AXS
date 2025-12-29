# ═══════════════════════════════════════════════════════════════════════════
# VALIDACIÓN MANUAL: AUP_GOV INTEGRADO
# ═══════════════════════════════════════════════════════════════════════════

## 🎯 OBJETIVO

Verificar que AUP_GOV opera como plano de poder real en el sistema.

---

## 📋 PRE-REQUISITOS

1. **Ejecutar migración de BD:**
   ```bash
   # Desde repositorio raíz
   psql "${DATABASE_URL}" < database/migration_04_gov.sql
   ```

2. **Ejecutar seed de gobierno:**
   ```bash
   cd /workspaces/MSP_AXS
   python scripts/seed_gov_bootstrap.py
   ```

   Esperado:
   ```
   ✓ Authority GLOBAL creada para: admin@example.com
   ✓ Policy QR vigencia: máximo 7 días
   ✓ Policy tenants: máximo 5 por first tier
   ✓ Policy usuarios: máximo 100 por tenant
   ```

3. **Levantar servidor:**
   ```bash
   cd /workspaces/MSP_AXS
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## ✅ PRUEBA 1: POLÍTICA PERMITE OPERACIÓN

### Escenario: Generar QR con vigencia DENTRO del límite

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "residente@example.com", "password": "password123"}' \
  | jq -r '.access_token')

# 2. Crear visita
VISITA=$(curl -s -X POST http://localhost:8000/visitas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "condominio_id": "condo_a",
    "nombre_visitante": "Juan Pérez",
    "casa_unidad": "A-101",
    "fecha_hora_prevista": "2025-12-30T10:00:00"
  }' | jq -r '.visita_id')

# 3. Generar QR (vigencia default: 7 días)
curl -X POST http://localhost:8000/qr/generar/$VISITA \
  -H "Authorization: Bearer $TOKEN"
```

**Resultado esperado:**
```json
{
  "status": "ok",
  "visita_id": "v_...",
  "qr_base64": "iVBORw0KGgo...",
  "qr_vigencia": "2026-01-05T..."
}
```

**✓ Verificación:**
- Status 200 OK
- QR generado sin error
- Evento registrado con `resultado: "permitido"`

```sql
SELECT * FROM events_aup 
WHERE entidad = 'policy' 
  AND accion = 'validar'
ORDER BY timestamp DESC LIMIT 1;

-- Esperado: resultado = 'permitido', motivo = 'Acción permitida por políticas'
```

---

## ❌ PRUEBA 2: POLÍTICA DENIEGA OPERACIÓN

### Escenario: Exceder límite de tenants

```bash
# 1. Login como MSP_ADMIN
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@msp.com", "password": "admin123"}' \
  | jq -r '.access_token')

# 2. Crear 6 condominios (límite es 5)
for i in {1..6}; do
  curl -X POST http://localhost:8000/condominios \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"nombre\": \"Condominio $i\", \"direccion\": \"Calle $i\"}"
done
```

**Resultado esperado en el 6to:**
```json
{
  "detail": "Gobierno denegó creación: Límite excedido: máximo 5 (actual: 5)"
}
```

**✓ Verificación:**
- Status 403 Forbidden
- Operación NO ejecutada
- Evento registrado con `resultado: "denegado"`

```sql
SELECT * FROM events_aup 
WHERE entidad = 'policy' 
  AND resultado = 'denegado'
ORDER BY timestamp DESC LIMIT 1;

-- Esperado: motivo = 'Límite excedido: máximo 5 (actual: 5)'
```

---

## 🔄 PRUEBA 3: POLÍTICA DINÁMICA (SIN REDEPLOY)

### Escenario: Cambiar política y verificar efecto inmediato

```sql
-- 1. Verificar política actual
SELECT * FROM policies_gov 
WHERE accion_objetivo = 'generar_qr';

-- 2. Cambiar límite de vigencia QR (de 7 a 3 días)
UPDATE policies_gov 
SET limites = '{"max_dias_vigencia": 3}'::jsonb
WHERE accion_objetivo = 'generar_qr';

-- 3. NO hacer redeploy del servidor
```

```bash
# 4. Intentar crear preregistro (vigencia default: 7 días)
curl -X POST http://localhost:8000/preregistro/crear \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_visitante": "Carlos López",
    "condominio_id": "condo_a",
    "casa_unidad": "B-202",
    "fecha_hora_prevista": "2025-12-31T14:00:00"
  }'
```

**Resultado esperado:**
```json
{
  "detail": "Gobierno denegó preregistro: Vigencia excedida: máximo 3 días (solicitado: 7)"
}
```

**✓ Verificación:**
- Status 403 Forbidden
- Política nueva aplicada SIN redeploy
- Sistema responde a cambios dinámicos

---

## 🔐 PRUEBA 4: AUTHORITY REVOCADA

### Escenario: Revocar authority y verificar pérdida de poder

```sql
-- 1. Ver authorities activas
SELECT authority_id, identity_id, tipo, estado 
FROM authorities_gov 
WHERE estado = 'activo';

-- 2. Revocar authority de un first tier
UPDATE authorities_gov 
SET estado = 'revocado', revoked_at = NOW()
WHERE authority_id = 'auth_xxx';
```

```bash
# 3. Usuario revocado intenta crear tenant
curl -X POST http://localhost:8000/condominios \
  -H "Authorization: Bearer $TOKEN_REVOCADO" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Condominio Prohibido", "direccion": "Calle X"}'
```

**Resultado esperado:**
```json
{
  "detail": "Gobierno denegó creación: No hay política definida para acción 'crear_tenant'"
}
```

**✓ Verificación:**
- Authority revocada = sin poder
- Operación denegada
- Efecto inmediato (sin cache)

---

## 📊 VERIFICACIÓN DE AXIOMAS

### Axioma 1: Gobierno precede a operación
```bash
# ✓ Todas las operaciones críticas consultan AUP_GOV ANTES de ejecutar
# ✓ Si gobierno falla, operación se aborta (no se intenta)
```

### Axioma 2: Toda decisión genera AUP_EVENT
```sql
-- Ver eventos de gobierno (últimos 10)
SELECT 
  timestamp,
  entidad,
  accion,
  resultado,
  motivo
FROM events_aup 
WHERE entidad = 'policy'
ORDER BY timestamp DESC 
LIMIT 10;

-- Esperado: Eventos de PERMITIDO y DENEGADO registrados
```

### Axioma 3: Políticas bloquean sin cambiar código
```bash
# ✓ PRUEBA 3 demuestra esto (cambio de límite sin redeploy)
```

### Axioma 4: Poder es explícito, acotado y revocable
```sql
-- Ver authorities con fechas
SELECT 
  authority_id,
  tipo,
  tenant_id,
  estado,
  created_at,
  revoked_at
FROM authorities_gov
ORDER BY created_at DESC;

-- ✓ Cada authority tiene tipo explícito
-- ✓ FIRST_TIER está acotado a tenant_id
-- ✓ Estado puede ser 'revocado' (axioma cumplido)
```

### Axioma 5: Si AUP_GOV falla, operación se deniega
```bash
# Simular fallo de BD (desconectar)
# ✓ Sistema debe denegar operación (safe by default)
# ✓ No debe propagar excepción al usuario
```

---

## 🎯 CHECKLIST DE INTEGRACIÓN

- [ ] Migración `migration_04_gov.sql` ejecutada
- [ ] Seed `seed_gov_bootstrap.py` ejecutado
- [ ] Authority GLOBAL existe
- [ ] 3 políticas base creadas
- [ ] Generación de QR consulta AUP_GOV
- [ ] Preregistro consulta AUP_GOV
- [ ] Creación de tenant consulta AUP_GOV
- [ ] Política PERMITE → operación exitosa + evento
- [ ] Política DENIEGA → operación bloqueada + evento
- [ ] Cambio dinámico de política (sin redeploy) funciona
- [ ] Authority revocada pierde poder inmediatamente

---

## 📈 PRÓXIMOS PASOS (OPCIONALES)

1. **Monetización:**
   - Crear políticas por plan (Free/Pro/Enterprise)
   - Vincular usuario a plan
   - Aplicar límites según plan

2. **Delegaciones:**
   - Crear delegación temporal
   - Verificar expiración automática
   - Revocar delegación antes de expirar

3. **Dashboard de gobierno:**
   - Ver políticas activas
   - Ver authorities por tenant
   - Ver eventos denegados (alertas)

4. **Testing automatizado:**
   - Tests unitarios de `evaluar_politica()`
   - Tests de integración con routers
   - Tests de revocación

---

## ✅ RESULTADO ESPERADO

**Sistema con arquitectura AUP completa:**
```
✅ AUP_SESSION   → Identidad validada (JWT)
✅ AUP_SCOPE     → Alcance validado (multi-tenant)
✅ AUP_EVENT     → Hechos declarados (trazabilidad)
✅ AUP_GOV       → Poder controlado (gobierno) ← INTEGRADO Y OPERATIVO
```

**Gobierno operativo:**
- Decisiones de poder tomadas por AUP_GOV (no por routers)
- Límites configurables dinámicamente (sin redeploy)
- Trazabilidad completa (cada decisión registrada)
- Base para escalado y monetización

═══════════════════════════════════════════════════════════════════════════
