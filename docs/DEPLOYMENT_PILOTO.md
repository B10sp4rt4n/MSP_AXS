# 🚀 DEPLOYMENT PILOTO — MSP_AXS

**Fecha:** 31 de diciembre de 2025  
**Objetivo:** Poner el sistema en producción para piloto real con vigilantes y residentes

---

## 📍 DÓNDE VA A RADICAR

### **Infraestructura Seleccionada: Railway + Neon**

**Backend:** Railway (FastAPI)  
**Base de Datos:** Neon PostgreSQL (ya configurada)  
**Frontend:** Servido por FastAPI (HTML estático)  
**SSL/HTTPS:** Automático (Railway)  

**URL del piloto:** `https://msp-axs-production.up.railway.app`

---

## 🎯 ACTORES DEL PILOTO

| Actor | Dispositivo | Uso |
|-------|------------|-----|
| **Vigilante** | Tablet en caseta | Validar QR de visitas, registrar accesos |
| **Residente** | Móvil (navegador) | Preregistrar visitas, generar QR |
| **Admin Condominio** | Desktop/tablet | Ver logs, gestionar usuarios |
| **MSP Admin (tú)** | Desktop | Monitoreo, políticas, soporte |

---

## 🔧 PASOS DE DEPLOYMENT

### **PASO 1: Preparar Frontend Mínimo (Sin Build)**

**Objetivo:** UI que funcione sin Vite/npm por ahora

```bash
# 1. Crear frontend servible por FastAPI
mkdir -p backend/static
```

**Crear:** `backend/static/index.html`

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MSP AXS - Preregistro</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #f5f5f5;
      padding: 20px;
    }
    .container {
      max-width: 500px;
      margin: 0 auto;
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    h1 {
      margin-bottom: 20px;
      color: #333;
    }
    input, select, textarea {
      width: 100%;
      padding: 12px;
      margin-bottom: 15px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 16px;
    }
    button {
      width: 100%;
      padding: 15px;
      background: #2196F3;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 18px;
      font-weight: bold;
      cursor: pointer;
    }
    button:hover {
      background: #1976D2;
    }
    .error {
      margin-top: 15px;
      padding: 15px;
      background: #ffebee;
      border: 1px solid #c62828;
      border-radius: 6px;
      color: #c62828;
    }
    .success {
      margin-top: 15px;
      padding: 15px;
      background: #e8f5e9;
      border: 1px solid #4caf50;
      border-radius: 6px;
      color: #2e7d32;
    }
    .ultima-accion {
      margin-top: 15px;
      padding: 10px;
      background: #fff3e0;
      border: 1px solid #ff9800;
      border-radius: 6px;
      font-size: 14px;
    }
    .qr-container {
      margin-top: 20px;
      text-align: center;
    }
    .qr-container img {
      max-width: 300px;
      border: 2px solid #333;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🏢 Preregistro de Visitas</h1>
    
    <input type="text" id="nombre" placeholder="Nombre del visitante" required>
    <input type="datetime-local" id="fecha" required>
    
    <select id="tipo">
      <option value="Visita">Visita</option>
      <option value="Servicio">Servicio</option>
    </select>
    
    <input type="text" id="placa" placeholder="Placas (opcional)">
    <textarea id="notas" rows="3" placeholder="Notas adicionales"></textarea>
    
    <button onclick="generarQR()">Generar QR</button>
    
    <div id="error" class="error" style="display:none;"></div>
    <div id="success" class="success" style="display:none;"></div>
    <div id="ultimaAccion" class="ultima-accion" style="display:none;"></div>
    
    <div id="qrContainer" class="qr-container" style="display:none;">
      <h3>QR Generado:</h3>
      <img id="qrImg" alt="Código QR">
    </div>
  </div>

  <script>
    // UI-AUP-01: Token mock (en producción viene de login real)
    const TOKEN_MOCK = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ1c2VyMSJ9.MOCK";
    
    async function generarQR() {
      // Limpiar mensajes previos
      document.getElementById('error').style.display = 'none';
      document.getElementById('success').style.display = 'none';
      document.getElementById('ultimaAccion').style.display = 'none';
      document.getElementById('qrContainer').style.display = 'none';
      
      const nombre = document.getElementById('nombre').value;
      const fecha = document.getElementById('fecha').value;
      const tipo = document.getElementById('tipo').value;
      const placa = document.getElementById('placa').value || null;
      const notas = document.getElementById('notas').value || null;
      
      if (!nombre || !fecha) {
        mostrarError('Por favor completa nombre y fecha');
        return;
      }
      
      try {
        const payload = {
          nombre_visitante: nombre,
          fecha_visita: new Date(fecha).toISOString(),
          tipo_visita: tipo,
          placa: placa,
          notas: notas
        };
        
        // UI-AUP-01: Endpoint gobernado por AUP
        const res = await fetch('/qr/generar_gobernado', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${TOKEN_MOCK}`
          },
          body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        // UI-AUP-02: Manejo de respuestas AUP
        if (res.status === 401) {
          mostrarError('⚠️ Sesión no válida o expirada. Acceso no autorizado.');
          registrarAccion('Generación de QR', 'DENEGADA');
          return;
        }
        
        if (res.status === 403) {
          mostrarError('⚠️ Acceso denegado por política del condominio. Este intento fue registrado.');
          registrarAccion('Generación de QR', 'DENEGADA');
          return;
        }
        
        // UI-AUP-03: Mostrar éxito
        if (data.qr_base64) {
          document.getElementById('qrImg').src = `data:image/png;base64,${data.qr_base64}`;
          document.getElementById('qrContainer').style.display = 'block';
          mostrarExito('✅ QR generado exitosamente');
          registrarAccion('Generación de QR', 'AUTORIZADA');
        }
      } catch (err) {
        console.error('Error:', err);
        mostrarError('Error de conexión con el servidor');
      }
    }
    
    function mostrarError(mensaje) {
      const el = document.getElementById('error');
      el.textContent = mensaje;
      el.style.display = 'block';
    }
    
    function mostrarExito(mensaje) {
      const el = document.getElementById('success');
      el.textContent = mensaje;
      el.style.display = 'block';
    }
    
    function registrarAccion(accion, resultado) {
      const el = document.getElementById('ultimaAccion');
      const timestamp = new Date().toLocaleTimeString('es-MX');
      el.innerHTML = `<strong>Última acción registrada:</strong><br>🕒 ${timestamp} — ${accion} (${resultado})`;
      el.style.display = 'block';
    }
  </script>
</body>
</html>
```

---

### **PASO 2: Configurar FastAPI para Servir Frontend**

**Modificar:** `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="MSP_AXS")

# ... (resto de configuración de routers, middleware, etc.)

# DEPLOYMENT: Servir frontend estático
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def root():
        return FileResponse(os.path.join(static_dir, "index.html"))
```

---

### **PASO 3: Configurar Variables de Entorno para Railway**

**Crear:** `railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

**Variables en Railway (Dashboard):**

```bash
DATABASE_URL_CORE=postgresql://user:pass@host/aup_core
DATABASE_URL_EVENT=postgresql://user:pass@host/aup_event
DATABASE_URL_GOV=postgresql://user:pass@host/aup_gov
SECRET_KEY=<tu_secret_key_generada>
ENVIRONMENT=production
```

---

### **PASO 4: Crear Endpoint de Health Check**

**En:** `backend/main.py`

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "aup_blocks_active": True
    }
```

---

### **PASO 5: Deploy a Railway**

```bash
# 1. Instalar Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# 2. Login
railway login

# 3. Crear proyecto nuevo
railway init

# 4. Vincular a GitHub
railway link

# 5. Deploy
git push origin main
# Railway detecta el push y despliega automáticamente
```

**Verificación:**
```bash
curl https://msp-axs-production.up.railway.app/health
# Respuesta: {"status":"healthy","aup_blocks_active":true}
```

---

## 🎯 CONFIGURACIÓN PARA ACTORES

### **1. Vigilante (Tablet en Caseta)**

**URL:** `https://msp-axs-production.up.railway.app`

**Flujo:**
1. Abrir navegador en tablet
2. Login con credenciales de vigilante
3. Validar QR de visitantes
4. Registrar entrada/salida

**Crear página dedicada:** `backend/static/vigilante.html`

---

### **2. Residente (Móvil)**

**URL:** `https://msp-axs-production.up.railway.app`

**Flujo:**
1. Login con credenciales de residente
2. Preregistrar visita
3. Generar QR
4. Compartir QR con visitante (WhatsApp/SMS)

**Responsive:** Ya tiene viewport configurado

---

### **3. Admin Condominio**

**URL:** `https://msp-axs-production.up.railway.app/admin`

**Flujo:**
1. Dashboard con logs de eventos
2. Gestión de usuarios
3. Configuración de políticas

**Crear:** `backend/static/admin.html`

---

## 📊 MONITOREO DEL PILOTO

### **Logs de Railway**

```bash
# Ver logs en tiempo real
railway logs
```

### **Queries de Auditoría**

```sql
-- Eventos del día
SELECT accion, resultado, COUNT(*) 
FROM events_aup 
WHERE DATE(timestamp) = CURRENT_DATE 
GROUP BY accion, resultado;

-- Intentos denegados
SELECT * FROM events_aup 
WHERE resultado = 'denegado' 
ORDER BY timestamp DESC 
LIMIT 20;

-- Usuarios más activos
SELECT identity_id, COUNT(*) as acciones 
FROM events_aup 
GROUP BY identity_id 
ORDER BY acciones DESC 
LIMIT 10;
```

---

## 🚨 PLAN DE CONTINGENCIA

### **Si Railway falla:**

**Opción A:** Render.com (similar a Railway)  
**Opción B:** Fly.io (más técnico pero robusto)  
**Opción C:** DigitalOcean App Platform

### **Si base de datos falla:**

- Neon tiene backups automáticos
- Railway puede agregar PostgreSQL propio
- Descargar dump: `pg_dump > backup.sql`

---

## ✅ CHECKLIST PRE-LANZAMIENTO

```bash
□ Backend desplegado en Railway
□ SSL/HTTPS activo
□ Variables de entorno configuradas
□ Health check respondiendo
□ Frontend accesible desde URL pública
□ Base de datos conectada (3 dominios)
□ Seeds ejecutados (authorities, policies, users)
□ Login funcionando end-to-end
□ Generación de QR funcionando
□ Logs capturando eventos
□ Documentación compartida con vigilantes
```

---

## 📱 SIGUIENTE FASE: App Nativa (Post-Piloto)

**Si el piloto valida el modelo:**

1. **Residente:** React Native (iOS + Android)
2. **Vigilante:** PWA instalable en tablet
3. **Admin:** Dashboard React con analytics

**Por ahora:** Web responsiva suficiente para validar AUP.

---

## 🎯 RESUMEN EJECUTIVO

| Aspecto | Decisión |
|---------|----------|
| **Backend** | Railway (FastAPI) |
| **Base de Datos** | Neon PostgreSQL (ya configurada) |
| **Frontend** | HTML estático servido por FastAPI |
| **SSL/HTTPS** | Automático (Railway) |
| **Costo Piloto** | $0-5/mes (Railway free tier) |
| **Tiempo de Deploy** | 1-2 horas |
| **Escalado** | Vertical (Railway slider) |
| **Monitoreo** | Railway Logs + SQL queries |

**URL del piloto:** `https://msp-axs-production.up.railway.app`

---

**Siguiente paso:** ¿Implemento el frontend estático ahora o prefieres otro approach?
