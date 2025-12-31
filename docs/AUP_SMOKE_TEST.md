# SMOKE TEST AUP — Validación Manual Pre-Piloto

**Fecha:** 2025-12-29  
**Objetivo:** Validar que el sistema AUP funciona end-to-end antes de salir a piloto.

---

## PRERREQUISITOS

```bash
✅ Modelos separados por dominio (backend/db/{core,event,gov})
✅ Bases creadas en Neon (aup_core, aup_event, aup_gov)
✅ Migraciones ejecutadas (tablas creadas)
✅ Seeds ejecutados (authorities, policies, scopes)
✅ Backend corriendo (uvicorn backend.main:app --reload)
```

---

## TEST 1: IDENTIDAD (AUP_SESSION)

**Pregunta:** ¿El sistema sabe quién soy?

### Pasos:

```bash
# 1. Login con credenciales válidas
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@msp.com",
    "password": "admin123"
  }'

# Respuesta esperada:
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer"
}
```

### Validación:

```bash
✅ Recibí un token JWT válido
✅ AUP_EVENT registró: sesion_iniciada, resultado=exito
✅ Puedo decodificar el JWT y ver identity_id + role
```

### Query de validación:

```sql
-- En aup_event:
SELECT * FROM events_aup 
WHERE accion = 'login' 
AND resultado = 'exito'
ORDER BY timestamp DESC 
LIMIT 1;
```

---

## TEST 2: ALCANCE (AUP_SCOPE)

**Pregunta:** ¿El sistema sabe dónde puedo actuar?

### Pasos:

```bash
# 1. Consultar mis scopes activos
curl -X GET http://localhost:8000/mis-scopes \
  -H "Authorization: Bearer <TOKEN>"

# Respuesta esperada:
{
  "scopes": [
    {
      "scope_id": "123",
      "tenant_id": "condo_abc",
      "tenant_nombre": "Condominio Demo",
      "access_level": "admin_condominio",
      "estado": "activo"
    }
  ]
}
```

### Validación:

```bash
✅ Tengo al menos 1 scope activo
✅ El scope tiene tenant_id válido
✅ El access_level es correcto según mi rol
```

### Query de validación:

```sql
-- En aup_core:
SELECT u.email, s.tenant_id, s.access_level, s.estado
FROM user_tenant_scope s
JOIN usuarios_exo u ON u.usuario_id = s.usuario_id
WHERE u.email = 'admin@msp.com'
AND s.estado = 'activo';
```

---

## TEST 3: EVENTO PERMITIDO (QR Generado)

**Pregunta:** ¿El sistema registra verdad cuando permito algo?

### Pasos:

```bash
# 1. Generar QR para visita
curl -X POST http://localhost:8000/qr/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "visita_id": "vis_demo123",
    "vigencia_dias": 3
  }'

# Respuesta esperada:
{
  "qr_token": "qr_abc123def",
  "vigencia": "2025-12-31T23:59:59",
  "estado": "generado"
}
```

### Validación:

```bash
✅ Recibí un qr_token válido
✅ AUP_EVENT registró: qr_generado, resultado=permitido
✅ La vigencia es menor o igual a política (max_dias_vigencia)
```

### Query de validación:

```sql
-- En aup_event:
SELECT tipo_evento, entidad, entidad_id, accion, resultado, timestamp
FROM events_aup 
WHERE accion = 'generar_qr'
AND resultado = 'permitido'
ORDER BY timestamp DESC 
LIMIT 1;
```

---

## TEST 4: EVENTO DENEGADO (QR con vigencia excesiva)

**Pregunta:** ¿El sistema niega y registra cuando violo una política?

### Pasos:

```bash
# 1. Intentar generar QR con vigencia > política
curl -X POST http://localhost:8000/qr/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "visita_id": "vis_demo123",
    "vigencia_dias": 30  # Si política dice max 7
  }'

# Respuesta esperada:
{
  "detail": "Vigencia solicitada excede límite de política (max: 7 días)"
}
```

### Validación:

```bash
✅ Recibí HTTP 403 Forbidden
✅ AUP_EVENT registró: qr_generado, resultado=denegado
✅ El motivo explica claramente por qué fue denegado
```

### Query de validación:

```sql
-- En aup_event:
SELECT tipo_evento, accion, resultado, motivo, timestamp
FROM events_aup 
WHERE accion = 'generar_qr'
AND resultado = 'denegado'
ORDER BY timestamp DESC 
LIMIT 1;
```

---

## TEST 5: GOBIERNO (Modificar Política)

**Pregunta:** ¿Puedo cambiar una regla y ver efecto inmediato?

### Pasos:

```bash
# 1. Consultar política actual
curl -X GET http://localhost:8000/gov/policies/qr_vigencia \
  -H "Authorization: Bearer <TOKEN>"

# Respuesta esperada:
{
  "policy_id": "pol_qr_vig_001",
  "nombre": "Límite Vigencia QR",
  "limites": {
    "max_dias_vigencia": 7
  },
  "estado": "activo"
}

# 2. Modificar política (si tengo authority)
curl -X PATCH http://localhost:8000/gov/policies/qr_vigencia \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "limites": {
      "max_dias_vigencia": 14
    }
  }'

# 3. Intentar de nuevo generar QR con 10 días
curl -X POST http://localhost:8000/qr/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "visita_id": "vis_demo456",
    "vigencia_dias": 10
  }'

# Respuesta esperada: AHORA DEBE PERMITIR
{
  "qr_token": "qr_xyz789",
  "vigencia": "2026-01-08T23:59:59",
  "estado": "generado"
}
```

### Validación:

```bash
✅ La política cambió correctamente en GOV
✅ El sistema aplicó la nueva política INMEDIATAMENTE
✅ AUP_EVENT registró: policy_modificada
✅ AUP_EVENT registró: qr_generado con resultado=permitido
```

### Query de validación:

```sql
-- En aup_gov:
SELECT nombre, limites, estado, updated_at
FROM policies_gov
WHERE policy_id = 'pol_qr_vig_001';

-- En aup_event:
SELECT accion, resultado, motivo
FROM events_aup 
WHERE entidad = 'policy'
AND accion = 'modificar'
ORDER BY timestamp DESC 
LIMIT 1;
```

---

## RESUMEN DE VALIDACIÓN

| Test | Componente | Validación | Debe pasar |
|------|-----------|-----------|-----------|
| 1 | AUP_SESSION | Login exitoso + JWT válido | ✅ |
| 2 | AUP_SCOPE | Scopes activos + tenant válido | ✅ |
| 3 | AUP_EVENT | Acción permitida registrada | ✅ |
| 4 | AUP_EVENT | Acción denegada registrada | ✅ |
| 5 | AUP_GOV | Política modificada + efecto inmediato | ✅ |

---

## CHECKLIST FINAL PRE-PILOTO

```bash
□ Test 1 (Login) → Pasa
□ Test 2 (Scope) → Pasa
□ Test 3 (Permitido) → Pasa
□ Test 4 (Denegado) → Pasa
□ Test 5 (Gobierno) → Pasa
□ Eventos en aup_event → Todos registrados
□ Políticas en aup_gov → Aplicadas correctamente
□ Backend sin errores → Log limpio
```

---

## CRITERIO DE ÉXITO

**Si esto pasa:**
- ✅ El sistema **sabe quién soy** (SESSION)
- ✅ El sistema **sabe dónde puedo actuar** (SCOPE)
- ✅ El sistema **registra la verdad** de lo que ocurre (EVENT)
- ✅ El sistema **respeta las reglas** declaradas (GOV)
- ✅ Las reglas **se pueden cambiar** y aplican de inmediato

**Entonces:**
> El sistema existe de verdad.  
> No es diseño, es realidad operativa.  
> Está listo para piloto.

---

## NOTAS IMPORTANTES

### Qué NO es este smoke test:
- ❌ NO es un test automatizado (eso viene después)
- ❌ NO es prueba de carga (eso es otro tema)
- ❌ NO es validación de UI (esto es backend puro)

### Qué SÍ es este smoke test:
- ✅ ES validación manual del flujo completo AUP
- ✅ ES verificación de que cada capa existe y funciona
- ✅ ES confirmación de que el sistema es ontológicamente correcto

---

## TIEMPO ESTIMADO

**Ejecución completa:** 10-15 minutos  
**Si algo falla:** 20-30 minutos adicionales de debug

---

## PRÓXIMO PASO DESPUÉS DE SMOKE TEST

Si todo pasa:
1. Documentar resultado en este archivo
2. Agregar timestamp de validación
3. Pasar a preparación de piloto

Si algo falla:
1. Identificar qué componente falló
2. Revisar logs del backend
3. Consultar queries de validación
4. Corregir y repetir

---

**Declaración AUP:**  
Un sistema que pasa este smoke test  
no es un prototipo,  
es un sistema que declara existencia verificable.
