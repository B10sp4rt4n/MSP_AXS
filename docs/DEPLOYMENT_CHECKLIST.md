# CHECKLIST DE DEPLOYMENT - FASE 2

**Fecha:** 2026-01-07  
**Versión:** 1.0.0  
**Estado:** Pre-Deploy

---

## ✅ PRE-REQUISITOS

### Cuentas y Servicios
- [ ] Cuenta Neon creada (https://neon.tech)
- [ ] Cuenta Railway/Render creada
- [ ] Cliente `psql` instalado localmente
- [ ] Git configurado con acceso al repo

### Configuración Local
- [ ] `.env` configurado con valores locales
- [ ] Base de datos local funcionando
- [ ] Tests smoke pasan localmente
- [ ] Health check responde correctamente

---

## 📦 PASO 1: CREAR BASES EN NEON (30 min)

### 1.1. Crear Proyecto
```
Nombre: msp-axs-production
Región: US East (o más cercana a usuarios)
PostgreSQL version: 15+
```

### 1.2. Crear 3 Databases

En el mismo proyecto Neon, crear:

1. **aup_core**
   - Descripción: Identidad y alcance (usuarios, condominios, scopes)
   - Permisos: Read/Write

2. **aup_event**
   - Descripción: Verdad histórica (eventos inmutables)
   - Permisos: Read/Write

3. **aup_gov**
   - Descripción: Poder explícito (autoridades, políticas)
   - Permisos: Read/Write

### 1.3. Obtener Connection Strings

Para cada base, copiar **Connection String** desde Neon dashboard:

```bash
# Formato:
postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require

# Ejemplo:
postgresql://neondb_owner:xxx@ep-xxx.us-east-2.aws.neon.tech/aup_core?sslmode=require
```

**Guardar en:** `docs/NEON_CREDENTIALS.txt` (NO commitear)

- [ ] DATABASE_URL_CORE copiado
- [ ] DATABASE_URL_EVENT copiado
- [ ] DATABASE_URL_GOV copiado

---

## 🗄️ PASO 2: EJECUTAR MIGRACIONES (20 min)

### 2.1. Preparar Migraciones

```bash
# Asegurar que existen los archivos:
ls database/schema_axs.sql
ls database/bootstrap_aup_sistema.sql
ls database/migration_event.sql
ls database/migration_04_gov.sql
```

### 2.2. Ejecutar en AUP_CORE

```bash
# Conectar a aup_core
psql "postgresql://USER:PASSWORD@HOST/aup_core?sslmode=require"

# Ejecutar schema
\i database/schema_axs.sql

# Ejecutar bootstrap
\i database/bootstrap_aup_sistema.sql

# Verificar tablas
\dt

# Salir
\q
```

**Verificación:**
- [ ] Tablas `usuarios_exo` creada
- [ ] Tabla `condominios_exo` creada
- [ ] Tabla `user_tenant_scope` creada

### 2.3. Ejecutar en AUP_EVENT

```bash
psql "postgresql://USER:PASSWORD@HOST/aup_event?sslmode=require"
\i database/migration_event.sql
\dt
\q
```

**Verificación:**
- [ ] Tabla `events` creada
- [ ] Índices de búsqueda creados

### 2.4. Ejecutar en AUP_GOV

```bash
psql "postgresql://USER:PASSWORD@HOST/aup_gov?sslmode=require"
\i database/migration_04_gov.sql
\dt
\q
```

**Verificación:**
- [ ] Tablas de gobierno creadas
- [ ] Políticas iniciales insertadas

---

## 🚀 PASO 3: DEPLOY A RAILWAY (30 min)

### 3.1. Crear Proyecto en Railway

1. Login en https://railway.app
2. New Project → Deploy from GitHub repo
3. Seleccionar: `B10sp4rt4n/MSP_AXS`
4. Branch: `main`

### 3.2. Configurar Variables de Entorno

En Railway → Variables:

```bash
# Entorno
ENVIRONMENT=production

# Bases de datos Neon
DATABASE_URL_CORE=postgresql://...aup_core?sslmode=require
DATABASE_URL_EVENT=postgresql://...aup_event?sslmode=require
DATABASE_URL_GOV=postgresql://...aup_gov?sslmode=require

# JWT (generar nuevo secreto)
SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_urlsafe(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Configuración
ECHO_SQL=false
LOG_LEVEL=INFO

# Features AUP
AUP_TENANT_CONTEXT_ENABLED=true
AUP_RLS_ENABLED=true
AUP_GOV_ENABLED=true
```

### 3.3. Verificar Procfile

Railway detecta automáticamente `Procfile`:

```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

- [ ] Procfile existe en root
- [ ] Comando correcto

### 3.4. Deploy

Railway inicia deploy automáticamente.

**Esperar log:**
```
✅ AUP_CORE: Tablas verificadas/creadas
✅ AUP_EVENT: Tablas verificadas/creadas
✅ AUP_GOV: Tablas verificadas/creadas
🔒 AUP-01 ACTIVADO: Middleware de SESSION activo
```

- [ ] Build exitoso
- [ ] Deploy exitoso
- [ ] URL pública generada

---

## ✅ PASO 4: VALIDACIÓN POST-DEPLOY (15 min)

### 4.1. Health Check

```bash
curl https://tu-app.railway.app/health
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "environment": "production",
  "aup_blocks_active": true,
  "version": "3.0.0-aup-gov"
}
```

- [ ] Status: healthy
- [ ] Environment: production
- [ ] Version correcta

### 4.2. Endpoint Raíz

```bash
curl https://tu-app.railway.app/
```

**Respuesta esperada:**
```json
{
  "ok": true,
  "service": "AX-S MSP API",
  "version": "3.0.0-aup-gov",
  "architecture": "AUP (SESSION + SCOPE + EVENT + GOV)"
}
```

- [ ] Responde correctamente
- [ ] Arquitectura AUP presente

### 4.3. Test de Autenticación

```bash
# Crear usuario de prueba primero (desde psql o endpoint)
curl -X POST https://tu-app.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "test123"
  }'
```

**Respuesta esperada:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

- [ ] Login funciona
- [ ] Token JWT generado

### 4.4. Test de RLS (con token)

```bash
TOKEN="<token del login>"

curl https://tu-app.railway.app/visitas/mis-visitas/condo-test-001 \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta esperada:**
- 403 si usuario no tiene scope en tenant
- 200 con array de visitas si tiene scope

- [ ] RLS activo (rechaza sin scope)
- [ ] Acepta con scope válido

---

## 📊 CHECKLIST FINAL

### Infraestructura
- [ ] 3 bases en Neon operativas
- [ ] Railway deployado exitosamente
- [ ] URL pública accesible
- [ ] Variables de entorno configuradas

### Funcionalidad
- [ ] Health check responde
- [ ] Login funciona
- [ ] RLS multi-tenant activo
- [ ] Logs claros en Railway

### Seguridad
- [ ] SECRET_KEY único generado
- [ ] Passwords no en logs
- [ ] HTTPS habilitado
- [ ] CORS configurado (si aplica)

---

## 🚨 TROUBLESHOOTING

### Error: "Database connection failed"
```bash
# Verificar connection string
echo $DATABASE_URL_CORE

# Probar conexión desde local
psql "$DATABASE_URL_CORE"
```

### Error: "Module not found"
```bash
# Verificar requirements.txt actualizado
pip freeze > requirements.txt
git add requirements.txt
git commit -m "fix: actualizar dependencies"
git push
```

### Error: "Port already in use"
```bash
# Railway asigna PORT automáticamente
# Verificar que Procfile usa $PORT
```

### Logs no aparecen
```bash
# En Railway → Deployments → Ver logs
# Buscar:
grep "AUP_CORE" logs
grep "ERROR" logs
```

---

## 📞 SOPORTE

| Problema | Acción |
|----------|--------|
| Neon no conecta | Verificar IP whitelist en Neon |
| Railway build falla | Revisar requirements.txt |
| RLS no funciona | Verificar migraciones ejecutadas |
| 500 errors | Revisar logs en Railway |

---

**Última actualización:** 2026-01-07  
**Responsable:** @B10sp4rt4n  
**Estado:** Pendiente de ejecución
