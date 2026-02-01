# 🏢 CONFIGURACIÓN TENANT DEMO - MSP

**Fecha:** Febrero 1, 2026  
**Estado:** Activo y Configurado

---

## 📋 Resumen de Configuración

### MSP (Managed Service Provider)
- **MSP ID:** `MSP-001`
- **Nombre:** Demo MSP
- **Estado:** ✅ Activo

### Condominio (Tenant)
- **Condominio ID:** `COND-001`
- **MSP Asociado:** MSP-001
- **Nombre:** Condominio Oriente
- **Estado:** ✅ Activo

---

## 👥 Usuarios Configurados

### Guardia Demo
- **Email:** guardia@condoriente.com
- **Rol:** GUARDIA
- **Condominio:** COND-001
- **Contraseña:** *(ver script de creación)*

---

## 🔗 URLs de Base de Datos

### PostgreSQL (Neon)
```bash
# URL Principal
DATABASE_URL=postgresql://neondb_owner:npg_MlG3nwcI1gfr@ep-curly-voice-ahvnh82x-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# URLs por Módulo AUP (todas apuntan a la misma BD)
DATABASE_CORE_URL=postgresql://...
DATABASE_EVENT_URL=postgresql://...
DATABASE_GOV_URL=postgresql://...
```

---

## 🚀 Scripts de Configuración

### 1. Crear MSP y Condominio Demo
```bash
cd /workspaces/MSP_AXS
python3 scripts/create_condominio_demo.py
```

**Resultado:**
- ✅ MSP-001 creado
- ✅ COND-001 creado

### 2. Crear Guardia Demo
```bash
python3 scripts/create_guardia_demo.py
```

### 3. Verificar Configuración
```bash
python3 -c "
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
db_url = os.getenv('DATABASE_CORE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Verificar MSP
cur.execute('SELECT * FROM msps_exo WHERE msp_id = %s', ('MSP-001',))
print('MSP:', cur.fetchone())

# Verificar Condominio
cur.execute('SELECT * FROM condominios_exo WHERE condominio_id = %s', ('COND-001',))
print('Condominio:', cur.fetchone())

cur.close()
conn.close()
"
```

---

## 🔐 Sistema Multi-Tenant (AUP_SCOPE)

### Arquitectura
```
MSP-001 (Demo MSP)
  └── COND-001 (Condominio Oriente)
       └── Guardia Demo (guardia@condoriente.com)
            └── user_tenant_scope
                 └── tenant_id: COND-001
                 └── access_level: guardia
```

### Validación de Alcance
Cada operación valida que el usuario tenga un `user_tenant_scope` válido para el tenant:

```python
# Ejemplo de validación
validate_user_owns_resource_in_tenant(
    usuario=current_user,
    tenant_id="COND-001",
    db=db,
    required_level=AccessLevel.GUARDIA
)
```

---

## 📊 Datos de Prueba

### Estructura de Datos
```sql
-- MSP
INSERT INTO msps_exo (msp_id, nombre)
VALUES ('MSP-001', 'Demo MSP');

-- Condominio
INSERT INTO condominios_exo (condominio_id, msp_id, nombre)
VALUES ('COND-001', 'MSP-001', 'Condominio Oriente');

-- Usuario Guardia
INSERT INTO usuarios (email, rol, condominio_id, ...)
VALUES ('guardia@condoriente.com', 'GUARDIA', 'COND-001', ...);
```

---

## 🧪 Testing

### 1. Login de Guardia
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "guardia@condoriente.com",
    "password": "guardia123"
  }'
```

### 2. Verificar Token
```bash
# El token JWT debe incluir:
# - usuario_id
# - condominio_id: COND-001
# - rol: GUARDIA
# - tenant_id: COND-001
```

### 3. Operaciones en Tenant
```bash
# Todas las operaciones validan el scope del tenant
GET /visitas?tenant_id=COND-001
POST /visitas
# etc...
```

---

## ✅ Checklist de Configuración

- [x] MSP-001 creado en `msps_exo`
- [x] COND-001 creado en `condominios_exo`
- [x] Usuario Guardia creado
- [ ] User Tenant Scopes configurados (pendiente si es necesario)
- [x] Base de datos Neon conectada
- [x] Variables de entorno configuradas

---

## 🔄 Próximos Pasos

1. **Crear más usuarios de prueba** (residentes, admins)
2. **Configurar scopes adicionales** si es necesario
3. **Poblar datos de prueba** (visitas, eventos, etc.)
4. **Testing de flujos completos** en el tenant demo

---

## 📚 Referencias

- [README.md](README.md) - Arquitectura Multi-Tenant
- [AUP_SCOPE.md](docs/AUP_SCOPE.md) - Sistema de alcance
- [SEPARACION_COMPLETADA.md](SEPARACION_COMPLETADA.md) - Estructura de bases de datos
