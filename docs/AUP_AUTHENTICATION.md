# Autenticación AUP - Sistema MSP_AXS

## 🎯 Filosofía AUP (Architecture from Unified Principles)

Este sistema de autenticación fue diseñado siguiendo el paradigma AUP: **primero se declaran entidades, relaciones y axiomas; luego se traduce a código**.

---

## 📐 Declaración de Entidades AUP

### **AUP_IDENTITY**
**Qué es:** Representa a un usuario del sistema (entidad persistente)

**Atributos:**
- `identity_id`: Identificador único (usuario_id)
- `rol_base`: Rol del usuario (RESIDENTE, GUARDIA, ADMIN_CONDOMINIO, MSP_ADMIN)
- `email`: Correo electrónico
- `estado`: Activo/inactivo (futuro)

**Mapeo en código:**
- Tabla: `usuarios`
- Modelo: `Usuario` (SQLAlchemy)

---

### **AUP_CREDENTIAL**
**Qué es:** Entidad que valida identidad (NO es la identidad, la VALIDA)

**Tipos soportados:**
- `password_local`: Hash bcrypt almacenado
- (futuro) `oauth_assertion`: Token de OAuth provider
- (futuro) `cert`: Certificado x509

**Mapeo en código:**
- Campo: `usuario.password_hash`
- Módulo: `backend/core/auth/password.py`

---

### **AUP_SESSION**
**Qué es:** Cápsula temporal de contexto autenticado

**Estructura:**
```json
{
  "sub": "identity_id",      // Quién es
  "role": "rol_base",        // Qué puede hacer (base)
  "method": "local",         // Cómo se autenticó
  "iat": timestamp,          // Cuándo se creó
  "exp": timestamp           // Cuándo expira
}
```

**Mapeo en código:**
- JWT (JSON Web Token)
- Módulo: `backend/core/auth/jwt.py`
- Algoritmo: HS256 (simétrico, migrable a RS256)

---

## 🔗 Relaciones AUP

```
AUP_IDENTITY
   ├── validada_por → AUP_CREDENTIAL
   └── genera → AUP_SESSION
```

**En código:**
1. Usuario presenta credenciales → `POST /auth/login`
2. Sistema valida `AUP_CREDENTIAL` → `verify_password()`
3. Sistema genera `AUP_SESSION` → `create_access_token()`
4. Cliente recibe JWT serializado
5. Cliente envía JWT en cada request → `Authorization: Bearer <token>`
6. Sistema reconstruye `AUP_IDENTITY` → `get_current_user()`

---

## ⚖️ Axiomas

### **Axioma 1: Sin AUP_SESSION válida, no hay acción**
Ningún endpoint protegido puede ejecutarse sin pasar por `get_current_user()`.

### **Axioma 2: AUP_SESSION es temporal**
Toda sesión tiene expiración explícita (default: 60 minutos).

### **Axioma 3: No hay identidad implícita**
El sistema NO confía en headers manuales (`X-User-Id`). Solo valida JWT.

---

## 🗂️ Estructura de Archivos

```
backend/core/auth/
├── __init__.py              # Exporta get_current_user (punto de entrada)
├── password.py              # AUP_CREDENTIAL (bcrypt)
├── jwt.py                   # AUP_SESSION (create/decode JWT)
├── dependencies.py          # Validador: get_current_user() [GUARDIÁN]
└── schemas.py               # Contratos Pydantic (LoginRequest, TokenResponse)

backend/routers/
└── auth_router.py           # POST /auth/login (crear AUP_SESSION)
```

---

## 🚀 Uso en Endpoints

### **Endpoint PÚBLICO (no requiere autenticación):**
```python
@router.post("/auth/login")
def login(credentials: LoginRequest):
    # No usa Depends(get_current_user)
    pass
```

### **Endpoint PROTEGIDO (requiere AUP_SESSION):**
```python
from backend.core.auth.dependencies import get_current_user
from backend.db.models import Usuario

@router.get("/protected")
def protected_endpoint(
    current_user: Usuario = Depends(get_current_user)  # ← Guardián AUP
):
    # current_user es AUP_IDENTITY reconstruida desde AUP_SESSION
    # Aquí va la lógica de negocio
    pass
```

---

## 🔄 Flujo Completo

### **1. Login (Crear AUP_SESSION)**
```bash
POST /auth/login
Content-Type: application/json

{
  "email": "residente@condominio.com",
  "password": "password123"
}
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### **2. Usar Token en Requests**
```bash
GET /visitas/mis-visitas
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Internamente:**
1. `OAuth2PasswordBearer` extrae token del header
2. `decode_access_token()` valida JWT
3. `get_current_user()` reconstruye `Usuario` desde BD
4. Endpoint recibe `AUP_IDENTITY` completa

---

## 🔐 Seguridad

### **Implementado:**
- ✅ JWT con expiración
- ✅ Password hash con bcrypt
- ✅ Validación en cada request
- ✅ No se confía en headers manuales

### **Pendiente (migración futura):**
- ⏳ Refresh tokens
- ⏳ Revocación activa (Redis/BD)
- ⏳ Scopes/permisos granulares (AUP_SCOPE)
- ⏳ Multitenant (tenant en JWT)
- ⏳ OAuth/SSO (cambiar a RS256)

---

## 🔧 Variables de Entorno

```bash
# Generar SECRET_KEY segura:
openssl rand -hex 32

# .env
SECRET_KEY=your-generated-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## 🧪 Testing

### **Test manual con curl:**

```bash
# 1. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'

# Respuesta: { "access_token": "...", "token_type": "bearer" }

# 2. Usar token
TOKEN="eyJhbG..."

curl http://localhost:8000/visitas/mis-visitas \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔄 Migración desde Sistema Anterior

### **Antes (INSEGURO):**
```python
@router.get("/endpoint")
def endpoint(usuario = Depends(get_usuario_actual)):  # X-User-Id header
    pass
```

### **Ahora (SEGURO con AUP):**
```python
from backend.core.auth.dependencies import get_current_user
from backend.db.models import Usuario

@router.get("/endpoint")
def endpoint(usuario: Usuario = Depends(get_current_user)):  # JWT validado
    pass
```

**Cambios necesarios:**
1. Importar `get_current_user` desde `backend.core.auth.dependencies`
2. Reemplazar `Depends(get_usuario_actual)` por `Depends(get_current_user)`
3. Tipar como `Usuario` explícitamente
4. La lógica de negocio NO cambia

---

## 📊 Mapeo Conceptual

| Concepto AUP | Implementación | Archivo |
|--------------|----------------|---------|
| AUP_IDENTITY | Modelo `Usuario` | `db/models.py` |
| AUP_CREDENTIAL | `password_hash` + bcrypt | `auth/password.py` |
| AUP_SESSION | JWT (HS256) | `auth/jwt.py` |
| Validador | `get_current_user()` | `auth/dependencies.py` |
| Crear sesión | `POST /auth/login` | `routers/auth_router.py` |

---

## 🎯 Siguiente Paso: AUP_SCOPE

El sistema actual tiene **alcance base** (`role`). El siguiente paso AUP es:

**AUP_SCOPE:** Permisos granulares y multitenant

```json
{
  "sub": "user123",
  "role": "RESIDENTE",
  "tenant": "condominio_abc",         // ← NUEVO
  "scopes": [                          // ← NUEVO
    "visitas:read:own",
    "visitas:create:own"
  ]
}
```

Esto se integra sin romper el sistema actual, solo extendiendo `create_access_token()` y `get_current_user()`.

---

## 📝 Notas de Diseño

### **¿Por qué HS256 y no RS256?**
- HS256 (simétrico): Más simple para MVP, suficiente para single-tenant
- RS256 (asimétrico): Necesario para OAuth/SSO (múltiples consumers)
- Migración: Cambiar algoritmo en `jwt.py` sin tocar routers

### **¿Por qué no hay refresh tokens?**
- Scope: MVP mínimo funcional
- Migración: Agregar endpoint `/auth/refresh` sin romper `/auth/login`

### **¿Por qué stateless?**
- Escalabilidad horizontal (sin Redis/BD en cada request)
- Migración: Agregar revocación activa cuando sea necesario

---

## ✅ Checklist de Implementación

- [x] Declarar entidades AUP
- [x] Implementar AUP_CREDENTIAL (password.py)
- [x] Implementar AUP_SESSION (jwt.py)
- [x] Implementar validador (dependencies.py)
- [x] Crear contratos (schemas.py)
- [x] Endpoint /auth/login
- [x] Migrar routers a get_current_user
- [x] Actualizar requirements.txt
- [x] Integrar en main.py
- [x] Documentación

---

**Sistema listo para producción MVP. Base sólida para AUP_SCOPE y multitenant.**
