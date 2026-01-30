# 🔐 GUÍA: Verificar Autenticación y Admin Panel

## Pasos para probar el flujo completo:

### 1. Asegurar que el servidor está corriendo
```bash
# Verificar que uvicorn está en ejecución
ps aux | grep uvicorn | grep -v grep

# Debería mostrar:
# python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Abrir el navegador y navegar a la aplicación
```
http://localhost:8000/
```

O desde GitHub Codespaces:
```
https://verbose-xylophone-7v5p45gj7q79hx4vv-8000.app.github.dev/
```

### 3. Verificar en la consola del navegador (F12)

#### Login:
- Buscar logs que digan:
  - `📱 API_URL: http://...`
  - `🔐 Token en localStorage: ...`
  - `📨 Respuesta login: 200 {...}`
  - `✅ Token recibido y guardado: eyJ...`
  - `✅ Token verificado en localStorage: eyJ...`

#### Admin Panel:
- Buscar logs que digan:
  - `🔐 API_URL: http://...`
  - `🔐 Token obtenido de localStorage: eyJ...`
  - `🔍 JWT Partes: 3 ✅ Válido` (Si es inválido, verificar el localStorage)
  - `📡 Iniciando petición a GET /msps/`
  - `📡 Respuesta recibida: 200 OK` (Si es 401, leer el error)

### 4. Credenciales de prueba
```
Email: test@example.com
Password: test123
```

### 5. Qué esperar

#### Si TODO está OK:
1. Login exitoso
2. Redirigido a admin.html
3. Panel muestra:
   - **Tab "📦 MSPs"**: Lista de MSPs existentes
   - **Tab "🏘️ Estructura"**: Estructura jeráquica (MSP → Condominio → Casa)
   - **Logs en consola**: Todos con ✅

#### Si hay error 401:
1. **Síntoma**: Error HTTP 401 en admin.html
2. **Revisar**:
   - ¿Token en localStorage?: `localStorage.getItem('auth_token')`
   - ¿Token es JWT válido? (3 partes separadas por .)
   - ¿Servidor recibe el token?: Ver logs en terminal
3. **Logs esperados en servidor**:
   - `AUP_SESSION creada: identity=...` (login exitoso)
   - `🌍 CORS ACTIVADO` (CORS configurado)
   - Si hay 401: `🚫 AUP-01 BLOQUEADO: SESSION inválida en GET /msps/: [error específico]`

### 6. Prueba desde línea de comandos

#### Generar token:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}' | python3 -m json.tool
```

#### Usar token para acceder a /msps/:
```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."  # Token generado arriba

curl -X GET "http://localhost:8000/msps/" \
  -H "Authorization: Bearer $TOKEN"
```

#### Crear un MSP:
```bash
curl -X POST "http://localhost:8000/msps/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Test MSP", "email": "test@test.com", "telefono": "555-1234"}'
```

### 7. Logs esperados en servidor

Al hacer login:
```
AUP_SESSION creada: identity=user_test_001 role=ADMIN method=local email=test@example.com
```

Al acceder a /msps/:
```
🔐 Middleware AUP-01: TOKEN válido para identity_id=user_test_001
✅ Acceso permitido a GET /msps/
```

Si hay error:
```
🚫 AUP-01 BLOQUEADO: SESSION inválida en GET /msps/: JWTError: ...
```

---

## Checklist de Verificación

- [ ] Servidor corriendo en puerto 8000
- [ ] CORS habilitado (debería ver: `🌍 CORS ACTIVADO`)
- [ ] Token se genera correctamente (GET /auth/login → access_token)
- [ ] Token se guarda en localStorage (admin.html muestra token en console)
- [ ] Token JWT es válido (3 partes separadas por .)
- [ ] GET /msps/ responde 200 con token válido
- [ ] Admin panel carga correctamente
- [ ] MSPs se muestran en la tabla

## Si todo falla:

1. **Restart el servidor**:
   ```bash
   pkill -f uvicorn
   cd /workspaces/MSP_AXS
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Limpiar localStorage**:
   En consola del navegador:
   ```javascript
   localStorage.clear()
   location.reload()
   ```

3. **Revisar logs del servidor**:
   Buscar líneas que digan `AUP-01` o `🚫 BLOQUEADO`
