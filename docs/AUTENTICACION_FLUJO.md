# 🔐 FLUJO DE AUTENTICACIÓN - AXS MSP

**Fecha:** Febrero 1, 2026  
**Sistema:** Multi-Tenant JWT Authentication

---

## 🎯 Cómo Funciona el Sistema de Tokens

### 1. Login (Obtener Token)

**Endpoint:** `POST /auth/login`

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 🔄 Ciclo de Vida del Token

### Configuración Actual (.env)
```bash
ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8 horas
SECRET_KEY=CHANGE_ME_IN_PRODUCTION
```

### Estructura del Token (JWT)
```json
{
  "sub": "user_0ff0e637",      // Usuario ID
  "role": "MSP_ADMIN",          // Rol del usuario
  "method": "local",            // Método de autenticación
  "iat": 1769928319,            // Emitido en (timestamp)
  "exp": 1769957119             // Expira en (timestamp)
}
```

---

## 🚀 Uso del Token en el Cliente

### Almacenamiento
```javascript
// Guardar después del login
localStorage.setItem('auth_token', response.access_token);
localStorage.setItem('token_expires', response.exp);
```

### Envío en Requests
```javascript
const token = localStorage.getItem('auth_token');

fetch('http://localhost:8000/api/endpoint', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### Axios (React)
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000'
});

// Interceptor para agregar token automáticamente
api.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Uso
await api.get('/msps/');
await api.post('/visitas/', data);
```

---

## ⚠️ Manejo de Expiración

### Detectar Token Expirado

**Respuesta del servidor (401):**
```json
{
  "detail": "Token inválido o expirado"
}
```

### Estrategia de Renovación

#### Opción 1: Re-login Manual (Implementado Actualmente)
```javascript
// En el interceptor de respuestas
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expirado - redirigir al login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

#### Opción 2: Verificar Expiración Antes de Cada Request
```javascript
function isTokenExpired() {
  const expires = localStorage.getItem('token_expires');
  if (!expires) return true;
  
  const now = Math.floor(Date.now() / 1000);
  return now >= expires;
}

// Antes de cada request
if (isTokenExpired()) {
  // Redirigir al login
  window.location.href = '/login';
}
```

#### Opción 3: Refresh Token (No Implementado Aún)
```bash
# Futuro endpoint a implementar
POST /auth/refresh
Authorization: Bearer <refresh_token>

# Respuesta
{
  "access_token": "nuevo_token...",
  "token_type": "bearer"
}
```

---

## 🛠️ Implementación en Frontend (React)

### Hook Personalizado
```javascript
// hooks/useAuth.js
import { useState, useEffect } from 'react';
import axios from 'axios';

export function useAuth() {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
      // Verificar si está expirado
      if (!isTokenExpired()) {
        setToken(storedToken);
        // Opcionalmente decodificar para obtener info del usuario
        const payload = decodeToken(storedToken);
        setUser(payload);
      } else {
        logout();
      }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await axios.post('/auth/login', {
        email,
        password
      });
      
      const { access_token } = response.data;
      localStorage.setItem('auth_token', access_token);
      
      // Decodificar para obtener expiración
      const payload = decodeToken(access_token);
      localStorage.setItem('token_expires', payload.exp);
      
      setToken(access_token);
      setUser(payload);
      
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('token_expires');
    setToken(null);
    setUser(null);
  };

  return { token, user, loading, login, logout };
}

// Función helper para decodificar JWT
function decodeToken(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

function isTokenExpired() {
  const expires = localStorage.getItem('token_expires');
  if (!expires) return true;
  const now = Math.floor(Date.now() / 1000);
  return now >= expires;
}
```

### Componente de Login
```javascript
// components/Login.jsx
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    const success = await login(email, password);
    if (success) {
      navigate('/dashboard');
    } else {
      setError('Email o contraseña incorrectos');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={e => setPassword(e.target.value)}
        placeholder="Contraseña"
        required
      />
      {error && <p className="error">{error}</p>}
      <button type="submit">Iniciar Sesión</button>
    </form>
  );
}
```

### Ruta Protegida
```javascript
// components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function ProtectedRoute({ children }) {
  const { token, loading } = useAuth();

  if (loading) {
    return <div>Cargando...</div>;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
```

---

## 📋 Usuarios Demo Disponibles

### 1. Admin MSP
```json
{
  "email": "test@example.com",
  "password": "test123",
  "rol": "MSP_ADMIN"
}
```

### 2. Guardia (Próximamente)
```json
{
  "email": "guardia@condoriente.com",
  "password": "guardia123",
  "rol": "GUARDIA"
}
```

---

## 🔍 Debugging de Tokens

### Ver Token en Navegador
```javascript
// En la consola del navegador
console.log(localStorage.getItem('auth_token'));
```

### Decodificar Token Online
Visita: https://jwt.io
Pega tu token para ver su contenido

### Ver Logs del Servidor
```bash
tail -f /tmp/server.log | grep -E "(JWT|TOKEN|LOGIN)"
```

---

## 🚨 Manejo de Errores Comunes

### Error: "Token inválido o expirado"
**Causa:** Token expiró (> 8 horas desde login)  
**Solución:** Hacer login nuevamente

### Error: "Email o contraseña incorrectos"
**Causa:** Credenciales inválidas  
**Solución:** Verificar email/password o crear usuario

### Error: "Authorization header faltante"
**Causa:** No se envió el token en el header  
**Solución:** Agregar `Authorization: Bearer <token>`

---

## 🔒 Mejores Prácticas

### ✅ DO
- Almacenar token en `localStorage` o `sessionStorage`
- Incluir token en TODOS los requests autenticados
- Limpiar token al hacer logout
- Manejar expiración automáticamente
- Usar HTTPS en producción

### ❌ DON'T
- No hardcodear tokens en el código
- No compartir tokens entre usuarios
- No guardar contraseñas en localStorage
- No ignorar errores 401
- No usar HTTP en producción

---

## 🔮 Futuras Mejoras

### 1. Refresh Token
```javascript
// Renovar token antes de que expire
if (tokenExpiresInLessThan(5, 'minutes')) {
  await refreshToken();
}
```

### 2. Token en httpOnly Cookie
```javascript
// Más seguro que localStorage
Set-Cookie: auth_token=...; HttpOnly; Secure; SameSite=Strict
```

### 3. Logout Remoto
```javascript
// Invalidar token en el servidor
POST /auth/logout
```

### 4. Multi-device Tracking
```javascript
// Ver sesiones activas y cerrarlas
GET /auth/sessions
DELETE /auth/sessions/:id
```

---

## 📚 Referencias

- **Código Backend:** [backend/routers/auth_router.py](../backend/routers/auth_router.py)
- **JWT Utils:** [backend/core/auth/jwt.py](../backend/core/auth/jwt.py)
- **Configuración:** [.env](../.env)
- **Documentación API:** http://localhost:8000/docs

---

## ✅ Quick Start

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' \
  | jq -r '.access_token')

# 2. Usar token
curl http://localhost:8000/msps/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Verificar expiración (después de 8 horas, volverá a fallar)
```

**El token dura 8 horas. Después de eso, debes hacer login de nuevo.**
