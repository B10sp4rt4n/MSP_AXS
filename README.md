# MSP_AXS - Sistema de Gestión de Accesos

Backend FastAPI con **Arquitectura AUP** (Architecture from Unified Principles).

Sistema multi-tenant para gestión de accesos en condominios con:
- ✅ Autenticación JWT (AUP_SESSION)
- ✅ Alcance multi-tenant (AUP_SCOPE)
- ✅ Trazabilidad completa (AUP_EVENT)

## 📚 Documentación Completa

📖 **Leer primero:** [docs/README.md](docs/README.md) - Índice maestro de documentación AUP

---

## 🏗️ Arquitectura AUP

El sistema implementa 3 pasos fundamentales:

### **PASO 1: AUP_SESSION** (Autenticación)
- JWT con bcrypt para passwords
- Endpoint: `POST /auth/login`
- Documentación: [docs/AUP_AUTHENTICATION.md](docs/AUP_AUTHENTICATION.md)

### **PASO 2: AUP_SCOPE** (Alcance Multi-Tenant)
- Validación de alcance por tenant (condominio)
- Jerarquía de access levels (MSP_ADMIN → RESIDENTE)
- Documentación: [docs/AUP_SCOPE.md](docs/AUP_SCOPE.md)

### **PASO 3: AUP_EVENT** (Trazabilidad)
- Declaración inmutable de hechos
- Hash SHA-256 para integridad
- Base para auditoría y compliance
- Documentación: [docs/AUP_EVENT.md](docs/AUP_EVENT.md)

**Flujo completo:** [docs/AUP_FLOW_COMPLETE.txt](docs/AUP_FLOW_COMPLETE.txt)

---

## 🚀 Quick Start

### 1. Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env y cambiar SECRET_KEY
```

**⚠️ IMPORTANTE:** Generar SECRET_KEY segura para producción:
```bash
openssl rand -hex 32
```

### 3. Ejecutar migraciones de BD

```bash
# 1. Schema principal
psql -U postgres -d tu_bd < database/schema_axs.sql

# 2. Migración de eventos (PASO 3)
psql -U postgres -d tu_bd < database/migration_03_events_aup.sql

# 3. Crear scopes desde usuarios existentes
python scripts/migrate_create_scopes.py
```

### 4. Ejecutar servidor

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Probar autenticación

```bash
# Login (genera AUP_SESSION + AUP_EVENT)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "password123"}'

# Respuesta: { "access_token": "...", "token_type": "bearer" }

# Usar token en requests protegidos
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:8000/visitas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"condominio_id": "condo_a", "nombre_visitante": "Juan", ...}'
```

---

## 🔐 Seguridad

### Autenticación (AUP_SESSION)
- JWT con algoritmo HS256 (simétrico)
- Tokens expiran en 60 minutos
- Passwords hasheados con bcrypt

### Autorización (AUP_SCOPE)
- Validación explícita de alcance en tenant
- Jerarquía de niveles: MSP_ADMIN (100) → LECTURA (20)
- Revocación inmediata (no espera expiración de JWT)

### Auditoría (AUP_EVENT)
- Todos los accesos registrados con hash SHA-256
- Inmutabilidad verificable
- Trazabilidad completa (quién/qué/dónde/cuándo/cómo/resultado)

---

## 🔑 Entidades Principales

| Concepto AUP | Implementación | Descripción |
|--------------|----------------|-------------|
| AUP_IDENTITY | Usuario | Quién actúa |
| AUP_SESSION | JWT | Contexto temporal válido |
| AUP_TENANT | Condominio | Contenedor de datos |
| AUP_SCOPE | UserTenantScope | Alcance sobre tenant |
| AUP_EVENT | Event | Hecho declarado con hash |

---

## 📂 Estructura del Proyecto

```
MSP_AXS/
├── backend/
│   ├── core/
│   │   ├── auth/          # PASO 1: JWT + password
│   │   ├── scope/         # PASO 2: Validación alcance
│   │   └── event/         # PASO 3: Registro de hechos
│   ├── db/
│   │   ├── models.py      # SQLAlchemy models
│   │   └── connection.py
│   ├── routers/           # Endpoints FastAPI
│   ├── services/          # Lógica de negocio
│   └── main.py            # App principal
├── database/
│   ├── schema_axs.sql                # Schema base
│   └── migration_03_events_aup.sql   # Migración eventos
├── docs/
│   ├── README.md                     # Índice maestro
│   ├── AUP_COMPLETE_SUMMARY.md       # Resumen ejecutivo
│   ├── AUP_AUTHENTICATION.md         # PASO 1
│   ├── AUP_SCOPE.md                  # PASO 2
│   ├── AUP_EVENT.md                  # PASO 3
│   └── AUP_FLOW_COMPLETE.txt         # Diagramas de flujo
├── scripts/
│   └── migrate_create_scopes.py      # Migración de scopes
└── requirements.txt
```

---

## 🔐 Endpoints Principales

### **Autenticación**
- `POST /auth/login` - Login con email/password (genera JWT + evento)

### **Visitas** (requiere JWT + scope)
- `POST /visitas` - Crear visita (valida SESSION + SCOPE + registra EVENT)
- `GET /visitas/mis-visitas` - Listar mis visitas
- `GET /visitas/condominio` - Listar visitas del condominio

### **QR Codes** (requiere JWT + scope)
- `POST /qr/generar/{visita_id}` - Generar QR (registra evento)
- `GET /qr/validar/{visita_id}/{token}` - Validar QR (registra evento con múltiples caminos)

### **Evidencias**
- `POST /evidencias/upload` - Subir evidencia
- `GET /evidencias/visita/{visita_id}` - Listar evidencias de visita

**Todos los endpoints protegidos validan:**
1. AUP_SESSION (JWT válido)
2. AUP_SCOPE (alcance en tenant)
3. AUP_EVENT (registra el hecho)

---

## 🧪 Testing de Eventos

```python
from backend.core.event.registry import (
    registrar_evento,
    verificar_integridad_evento,
    obtener_eventos_entidad
)
from backend.core.event import EventEntity, EventAction, EventResult

# Consultar eventos de una visita
eventos = obtener_eventos_entidad(db, "visita", "v123")
for e in eventos:
    print(f"{e.timestamp} | {e.accion} | {e.resultado}")

# Verificar integridad de evento
es_integro = verificar_integridad_evento(evento)
if not es_integro:
    print("⚠️ ALERTA: Evento fue alterado")
```

**Queries SQL útiles:**
```sql
-- ¿Qué eventos denegados hubo hoy?
SELECT identity_id, accion, entidad, motivo, timestamp
FROM events_aup
WHERE resultado = 'denegado'
  AND timestamp >= CURRENT_DATE
ORDER BY timestamp DESC;

-- ¿Qué le pasó a esta visita?
SELECT accion, resultado, motivo, timestamp
FROM events_aup
WHERE entidad = 'visita' AND entidad_id = 'v123'
ORDER BY timestamp ASC;
```

---

## 📊 Axiomas AUP Implementados

1. **Sin AUP_SESSION válida → No hay acción**
   - Todos los endpoints protegidos requieren JWT

2. **Sin AUP_SCOPE válido → No existe operativamente en tenant**
   - Sistema valida alcance explícitamente, no infiere

3. **Toda acción relevante genera AUP_EVENT**
   - Login, crear visita, validar QR, etc.

4. **AUP_EVENT es inmutable**
   - Hash SHA-256 permite verificar alteraciones

5. **Estado se puede reconstruir desde eventos**
   - Histórico completo de qué pasó con cada entidad

---

## 💎 Ventajas de la Arquitectura AUP

### **vs Autenticación Tradicional:**
- Declarativo (qué es una sesión) vs imperativo (cómo autenticar)
- Axiomas claros vs reglas implícitas
- Fácil validar vs difícil auditar

### **vs Multi-Tenant Tradicional:**
- Scope dinámico (BD) vs roles estáticos (JWT)
- Revocación inmediata vs esperar expiración
- First tier nativo (usuario en múltiples tenants)

### **vs Logging Tradicional:**
- Eventos = entidad de dominio vs texto plano
- Hash de inmutabilidad vs logs mutables
- Queries SQL estructuradas vs grep en archivos

---

## 🚨 Troubleshooting

### **Error: 401 Unauthorized**
- Verificar que el token JWT sea válido
- Verificar que no haya expirado (60 minutos)
- Revisar eventos: `SELECT * FROM events_aup WHERE accion = 'login' AND resultado = 'fallo'`

### **Error: 403 Forbidden**
- Usuario no tiene scope en el tenant solicitado
- Verificar scopes: `SELECT * FROM user_tenant_scope WHERE usuario_id = 'X'`
- Revisar eventos: `SELECT * FROM events_aup WHERE resultado = 'denegado'`

### **Eventos No Se Registran**
- Verificar que tabla `events_aup` exista
- Ejecutar migración: `psql < database/migration_03_events_aup.sql`
- Verificar foreign keys (usuarios_exo, condominios_exo)

---

## 📋 Próximos Pasos Sugeridos

1. **Migrar endpoints restantes** a validación SCOPE + EVENT
2. **Implementar tests** unitarios e integración
3. **Dashboard de eventos** denegados para seguridad
4. **Archivado de eventos** antiguos (>1 año)
5. **Alertas automáticas** ante anomalías

---

## 📚 Recursos

- **Documentación completa:** [docs/README.md](docs/README.md)
- **Resumen ejecutivo:** [docs/AUP_COMPLETE_SUMMARY.md](docs/AUP_COMPLETE_SUMMARY.md)
- **Diagramas de flujo:** [docs/AUP_FLOW_COMPLETE.txt](docs/AUP_FLOW_COMPLETE.txt)

---

## 🤝 Contribuir

Al agregar nuevos endpoints, seguir el flujo AUP:

```python
@router.post("/nuevo-recurso")
def crear_recurso(
    data: Schema,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)  # PASO 1: SESSION
):
    # PASO 2: SCOPE
    validate_user_owns_resource_in_tenant(
        usuario, data.tenant_id, db, AccessLevel.ADMIN
    )
    
    # Lógica de negocio
    recurso = service.crear(db, data)
    
    # PASO 3: EVENT
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    registrar_evento(
        db, usuario, token, data.tenant_id,
        EventEntity.RECURSO.value, recurso.id,
        EventAction.CREAR.value, EventResult.EXITO.value
    )
    
    return recurso
```

---

**Sistema MSP_AXS - Arquitectura AUP Completa**  
**Versión:** 3.0 (SESSION + SCOPE + EVENT)  
**Última actualización:** 2024-12-29

### Endpoints protegidos (requieren JWT):
Enviar token en header:
```
Authorization: Bearer <access_token>
```

**Ejemplos:**
- `GET /visitas/mis-visitas` - Ver mis visitas
- `POST /preregistro/crear` - Crear preregistro
- `GET /qr/validar/{visita_id}/{token}` - Validar QR

---

## 📐 Arquitectura AUP

El sistema sigue **AUP (Architecture from Unified Principles)**:

### Entidades:
- **AUP_IDENTITY**: Usuario del sistema (`Usuario` en BD)
- **AUP_CREDENTIAL**: Validador de identidad (password hash)
- **AUP_SESSION**: Contexto temporal autenticado (JWT)

### Axiomas:
1. Sin AUP_SESSION válida → No hay acción
2. AUP_SESSION es temporal (expira)
3. No se confía en identidad implícita

📚 **Documentación completa:** [docs/AUP_AUTHENTICATION.md](docs/AUP_AUTHENTICATION.md)
