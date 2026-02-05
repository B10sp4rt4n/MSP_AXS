# 🚀 PRUEBA RÁPIDA - Admin Panel

## URL y Credenciales

### 1. Abrir la aplicación
```
http://localhost:8000/
```

O desde GitHub Codespaces (reemplazar con tu URL real):
```
https://verbose-xylophone-7v5p45gj7q79hx4vv-8000.app.github.dev/
```

### 2. Credenciales de Login
```
Email: test@example.com
Password: test123
```

### 3. Después de login, hacer click en:
```
🏢 Panel de Administración
```

---

## ✅ Qué debería ver

### En la consola del navegador (F12 → Console):

**Después de login:**
```
🔐 Token en localStorage: eyJhbGc...
✅ Token recibido y guardado: eyJhbGc...
```

**En admin.html:**
```
🔐 Token obtenido de localStorage: eyJhbGc...
🔍 JWT Partes: 3 ✅ Válido
📡 Iniciando petición a GET /msps/
📡 Respuesta recibida: 200 OK
```

### En el navegador:

Panel con dos tabs:
- **📦 MSPs**: Tabla con MSPs existentes
- **🏘️ Estructura**: Vista jeráquica de Condominios y Casas

---

## ❌ Si hay error 401

### En consola, busca:
```
❌ Error HTTP 401
```

### En logs del servidor (terminal), busca:
```
🚫 AUP-01 BLOQUEADO: SESSION inválida
```

### Soluciones rápidas:

1. **Limpiar localStorage**:
   En consola del navegador:
   ```javascript
   localStorage.clear()
   location.reload()
   ```

2. **Volver a hacer login**:
   Ir a http://localhost:8000/ y hacer login de nuevo

3. **Restart servidor**:
   ```bash
   pkill -f uvicorn
   cd /workspaces/MSP_AXS
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 🧪 Prueba desde línea de comandos

Si prefieres probar desde curl primero:

```bash
# 1. Login y obtener token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"

# 2. Obtener lista de MSPs
curl -X GET "http://localhost:8000/msps/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 3. Crear nuevo MSP
curl -X POST "http://localhost:8000/msps/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Test MSP", "email": "test@test.com", "telefono": "555-1234"}' | python3 -m json.tool
```

---

## 📈 Flujo Esperado

```
1. Login (/auth/login)
   ↓
2. Token generado y guardado en localStorage
   ↓
3. Click en "Panel de Administración"
   ↓
4. admin.html carga token desde localStorage
   ↓
5. Petición GET /msps/ con Authorization header
   ↓
6. Servidor valida token (AUP-01)
   ↓
7. ✅ MSPs se muestran en tabla
   ↓
8. ✅ Admin panel funciona correctamente
```

---

## ⚠️ Posibles Problemas

| Síntoma | Causa | Solución |
|---------|-------|----------|
| Error 401 en admin.html | Token inválido o no enviado | Ver logs en console |
| "Acceso Restringido" al abrir admin.html | No hay token en localStorage | Hacer login primero |
| Error de CORS | Servidor sin CORS habilitado | CORS ya está habilitado ✅ |
| Token con saltos de línea | Problema de formato | Se corrigió en index.html |
| Servidor no responde | Servidor no está corriendo | Verificar con `ps aux \| grep uvicorn` |

---

**Cualquier duda, revisar `GUIA_VERIFICACION_AUTH.md` para más detalles**
