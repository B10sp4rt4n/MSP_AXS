# DEPLOYMENT GUIDE — MEMORIA AUP DECLARADA

**Para:** Operadores, DevOps, Fundadores  
**Versión:** 3.0.0-aup-gov  
**Tiempo estimado:** 90 minutos

---

## PREREQUISITOS

- Cuenta Neon (https://neon.tech)
- Cliente `psql` instalado
- Variables de entorno configuradas

---

## PASO 1: CREAR 3 BASES EN NEON

### 1.1. Crear proyecto Neon
```
Nombre: msp-axs-production
Región: US East (o más cercana)
PostgreSQL version: 15+
```

### 1.2. Crear bases de datos

En el dashboard de Neon, crear **3 databases** en el mismo proyecto:

1. **aup_core** → Identidad y alcance
2. **aup_event** → Verdad histórica
3. **aup_gov** → Poder explícito

### 1.3. Obtener connection strings

Para cada base, copiar la **Connection String**:

```
postgresql://user:password@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/aup_core?sslmode=require
postgresql://user:password@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/aup_event?sslmode=require
postgresql://user:password@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/aup_gov?sslmode=require
```

---

## PASO 2: CONFIGURAR VARIABLES DE ENTORNO

### 2.1. Crear archivo `.env`

```bash
cp .env.example .env
```

### 2.2. Editar `.env` con las 3 URLs reales

```bash
# AUP_CORE
DATABASE_CORE_URL=postgresql://user:pass@ep-xxxxx.neon.tech/aup_core?sslmode=require

# AUP_EVENT
DATABASE_EVENT_URL=postgresql://user:pass@ep-xxxxx.neon.tech/aup_event?sslmode=require

# AUP_GOV
DATABASE_GOV_URL=postgresql://user:pass@ep-xxxxx.neon.tech/aup_gov?sslmode=require

# AUTH
SECRET_KEY=<generar-con-openssl-rand-hex-32>
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 2.3. Generar SECRET_KEY

```bash
openssl rand -hex 32
```

Copiar el output a `.env`.

---

## PASO 3: EJECUTAR MIGRACIONES

### 3.1. Migración CORE

**Archivo:** `database/migration_core.sql` (crear si no existe con tablas CORE)

```bash
psql $DATABASE_CORE_URL < database/migration_core.sql
```

**Verifica:**
```bash
psql $DATABASE_CORE_URL -c "\dt"
```

Deberías ver:
- usuarios
- condominios_exo
- msps_exo
- user_tenant_scope
- visitas
- evidencias
- casetas

### 3.2. Migración EVENT

**Archivo:** `database/migration_03_events_aup.sql` (ya existe)

```bash
psql $DATABASE_EVENT_URL < database/migration_03_events_aup.sql
```

**Verifica:**
```bash
psql $DATABASE_EVENT_URL -c "\dt"
```

Deberías ver:
- events_aup

### 3.3. Migración GOV

**Archivo:** `database/migration_04_gov.sql` (ya existe)

```bash
psql $DATABASE_GOV_URL < database/migration_04_gov.sql
```

**Verifica:**
```bash
psql $DATABASE_GOV_URL -c "\dt"
```

Deberías ver:
- authorities_gov
- policies_gov
- delegations_gov

---

## PASO 4: BOOTSTRAP (DATOS INICIALES)

### 4.1. Bootstrap GOV

**Script:** `scripts/seed_gov_bootstrap.py`

```bash
python scripts/seed_gov_bootstrap.py
```

**Crea:**
- Autoridad GLOBAL
- Políticas base (qr_vigencia_dias: 7, max_tenants: 5, max_usuarios: 100)

### 4.2. Bootstrap Planes Comerciales

**Script:** `scripts/seed_planes_comerciales.py`

```bash
python scripts/seed_planes_comerciales.py
```

**Crea:**
- Plan FREE
- Plan PRO
- Plan ENTERPRISE

---

## PASO 5: SMOKE TEST (CRÍTICO)

### 5.1. Iniciar servidor

```bash
uvicorn backend.main:app --reload
```

### 5.2. Test 1: Login (→ CORE)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "test123"}'
```

**Esperado:** Token JWT

**Valida que:** Usuario leído desde `aup_core`

### 5.3. Test 2: Generar QR (→ CORE + EVENT + GOV)

```bash
TOKEN="<token_del_test_anterior>"

curl -X POST http://localhost:8000/qr/generar \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visita_id": "vis_001", "dias_vigencia": 5}'
```

**Esperado:** QR generado (200 OK)

**Valida que:**
- Política leída desde `aup_gov.policies_gov`
- QR escrito en `aup_core.visitas`
- Evento escrito en `aup_event.events_aup`

**Verificar evento:**
```bash
psql $DATABASE_EVENT_URL -c "SELECT tipo_evento, resultado, accion FROM events_aup ORDER BY timestamp DESC LIMIT 5;"
```

### 5.4. Test 3: Exceder política (→ EVENT con DENIED)

```bash
curl -X POST http://localhost:8000/qr/generar \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"visita_id": "vis_001", "dias_vigencia": 30}'
```

**Esperado:** 403 Forbidden

**Verificar evento:**
```bash
psql $DATABASE_EVENT_URL -c "SELECT tipo_evento, resultado, motivo FROM events_aup WHERE resultado = 'denegado' ORDER BY timestamp DESC LIMIT 1;"
```

Deberías ver evento con `resultado = denegado` y motivo explicando exceso de política.

### 5.5. Test 4: Cambiar política (→ Efecto inmediato)

**Cambiar límite a 10 días:**
```bash
psql $DATABASE_GOV_URL -c "UPDATE policies_gov SET limites = '{\"max_dias_vigencia\": 10}'::jsonb WHERE nombre = 'qr_vigencia_dias';"
```

**Probar QR con 8 días:**
```bash
curl -X POST http://localhost:8000/qr/generar \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"visita_id": "vis_002", "dias_vigencia": 8}'
```

**Esperado:** 200 OK (ahora 8 días es válido)

**Axioma validado:** Sin cache, sin reinicio → efecto inmediato

---

## PASO 6: HEALTH CHECK (PRODUCTION)

### 6.1. Verificar 3 conexiones

```bash
curl http://localhost:8000/health
```

**Esperado:**
```json
{
  "status": "healthy",
  "databases": {
    "core": "connected",
    "event": "connected",
    "gov": "connected"
  }
}
```

---

## PASO 7: MONITOREO

### 7.1. Queries críticas

**Eventos recientes:**
```sql
SELECT tipo_evento, resultado, COUNT(*) 
FROM events_aup 
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY tipo_evento, resultado;
```

**Políticas activas:**
```sql
SELECT nombre, ambito, estado, limites 
FROM policies_gov 
WHERE estado = 'activo';
```

**Usuarios con scope:**
```sql
SELECT u.email, c.nombre, s.access_level, s.estado
FROM usuarios u
JOIN user_tenant_scope s ON u.usuario_id = s.usuario_id
JOIN condominios_exo c ON s.tenant_id = c.condominio_id
WHERE s.estado = 'activo';
```

---

## TROUBLESHOOTING

### Error: "No module named 'backend'"

```bash
export PYTHONPATH="${PYTHONPATH}:/workspaces/MSP_AXS"
```

### Error: "Could not connect to database"

Verificar que URLs tienen `?sslmode=require` al final.

### Error: "Policy not found"

Ejecutar bootstrap scripts (Step 4).

### Error: "Events not being recorded"

Verificar que `DATABASE_EVENT_URL` está correctamente configurada y que la tabla `events_aup` existe.

---

## CRITERIO DE ÉXITO

✅ **MSP_AXS está listo para piloto cuando:**

- [ ] 3 bases responden en Neon
- [ ] Smoke test pasa 4/4
- [ ] Eventos se registran en `aup_event`
- [ ] Políticas gobiernan QR
- [ ] Health check retorna `healthy`

**Tiempo estimado desde cero:** 90 minutos  
**Tiempo si bases ya existen:** 30 minutos

---

**Versión:** 3.0.0-aup-gov  
**Última actualización:** Diciembre 29, 2024
