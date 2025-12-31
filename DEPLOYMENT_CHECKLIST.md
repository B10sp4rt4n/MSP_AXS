# 🚀 DEPLOYMENT CHECKLIST - MSP_AXS Piloto

## ✅ Preparación Completada

### Backend
- [x] FastAPI configurado para servir frontend estático
- [x] Endpoint `/health` para monitoring
- [x] Middleware AUP_SessionGuard activo
- [x] Bloqueos runtime AUP-01, AUP-02, AUP-03 implementados
- [x] Separación de dominios (CORE/EVENT/GOV)
- [x] railway.json configurado
- [x] Procfile creado

### Frontend
- [x] HTML estático con UI-AUP integrada
- [x] Formulario de preregistro funcional
- [x] Manejo de respuestas 401/403 (SESSION/GOV)
- [x] Evidencia de última acción visible
- [x] Responsive (viewport configurado)
- [x] Servido desde `/` por FastAPI

### Archivos Creados
- `backend/static/index.html` - Frontend completo
- `railway.json` - Configuración de deploy
- `Procfile` - Comando de inicio
- `docs/DEPLOYMENT_PILOTO.md` - Documentación completa

---

## 🎯 Próximos Pasos para Deploy

### 1. Variables de Entorno (Railway Dashboard)

```bash
# Base de datos (Neon)
DATABASE_URL_CORE=postgresql://user:pass@host/aup_core
DATABASE_URL_EVENT=postgresql://user:pass@host/aup_event
DATABASE_URL_GOV=postgresql://user:pass@host/aup_gov

# Seguridad
SECRET_KEY=<generar con: openssl rand -hex 32>

# Ambiente
ENVIRONMENT=production
```

### 2. Deploy en Railway

```bash
# Opción A: Desde GitHub (recomendado)
1. Push a GitHub: git push origin main
2. Conectar Railway a tu repo
3. Railway despliega automáticamente

# Opción B: Railway CLI
railway login
railway init
railway up
```

### 3. Verificación Post-Deploy

```bash
# Health check
curl https://tu-app.railway.app/health

# Respuesta esperada:
{
  "status": "healthy",
  "environment": "production",
  "aup_blocks_active": true,
  "version": "3.0.0-aup-gov"
}

# Frontend
curl https://tu-app.railway.app/
# Debe retornar HTML de index.html
```

### 4. Testing de UI-AUP

1. Abrir en navegador: `https://tu-app.railway.app`
2. Llenar formulario de preregistro
3. Click "Generar QR"
4. **Verificar:**
   - Si token mock falla → Mensaje 401 visible
   - Si política deniega → Mensaje 403 visible
   - Si éxito → QR se muestra + última acción registrada

---

## 📊 Monitoreo

### Railway Dashboard
- Logs en tiempo real
- Métricas de CPU/RAM
- Health checks automáticos

### SQL Queries
```sql
-- Ver últimos eventos AUP
SELECT * FROM events_aup 
ORDER BY timestamp DESC 
LIMIT 20;

-- Intentos denegados
SELECT accion, resultado, COUNT(*) 
FROM events_aup 
WHERE resultado = 'denegado' 
GROUP BY accion, resultado;
```

---

## 🚨 Troubleshooting

### Backend no levanta
```bash
# Ver logs
railway logs

# Verificar variables
railway variables

# Revisar health check
curl https://tu-app.railway.app/health
```

### Frontend no se ve
```bash
# Verificar que static/ existe
ls backend/static/

# Verificar montaje en main.py
grep "StaticFiles" backend/main.py
```

### Base de datos no conecta
```bash
# Verificar conexiones Neon
railway variables | grep DATABASE

# Test de conexión
psql $DATABASE_URL_CORE -c "SELECT 1"
```

---

## ✅ Sistema Listo para Piloto

**Estado actual:**
- ✅ Backend deployable
- ✅ Frontend funcional
- ✅ AUP operativo (bloqueos activos)
- ✅ Gobierno integrado
- ✅ Trazabilidad completa
- ✅ UI hace visible SESSION/GOV/EVENT

**Siguiente acción:** Hacer push y deploy a Railway

```bash
git add .
git commit -m "feat: frontend estático deployable con Railway config"
git push origin main
```

---

## 🎯 Después del Deploy

1. **Crear usuarios reales** (vigilantes, residentes)
2. **Configurar políticas** por condominio
3. **Compartir URL** con actores del piloto
4. **Monitorear eventos** en tiempo real
5. **Iterar** según feedback

**URL del piloto:** `https://tu-app.railway.app`
