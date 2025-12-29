# ═══════════════════════════════════════════════════════════════════════════
# ÍNDICE MAESTRO - DOCUMENTACIÓN AUP
# ═══════════════════════════════════════════════════════════════════════════

## 📚 ARQUITECTURA AUP (Architecture from Unified Principles)

Sistema MSP_AXS implementado siguiendo paradigma AUP:
**Declarar entidades y axiomas ANTES de implementar código.**

---

## 📖 DOCUMENTOS PRINCIPALES

### **1. Resumen Ejecutivo Completo**
📄 [AUP_COMPLETE_SUMMARY.md](AUP_COMPLETE_SUMMARY.md)

**Contenido:**
- Visión general de los 3 pasos AUP
- Arquitectura completa del sistema
- Comparación antes/después
- Testing rápido
- Próximos pasos

**Cuándo leerlo:** Primera lectura para entender todo el sistema.

---

### **2. PASO 1: AUP_SESSION (Autenticación JWT)**
📄 [AUP_AUTHENTICATION.md](AUP_AUTHENTICATION.md)

**Contenido:**
- Declaración de AUP_IDENTITY, AUP_CREDENTIAL, AUP_SESSION
- Axiomas de autenticación
- Flujo completo de login
- Mapeo concepto → código
- Migración de endpoints

**Archivos de código:**
- `backend/core/auth/password.py` - AUP_CREDENTIAL (bcrypt)
- `backend/core/auth/jwt.py` - AUP_SESSION (crear/validar JWT)
- `backend/core/auth/dependencies.py` - get_current_user()
- `backend/routers/auth_router.py` - POST /auth/login

**Cuándo leerlo:** Para entender autenticación JWT en modo AUP.

---

### **4. PASO 4: AUP_GOV (Gobierno de Plataforma)**
📄 [AUP_GOV.md](AUP_GOV.md)

**Contenido:**
- Declaración de AUP_AUTHORITY, AUP_POLICY, AUP_DELEGATION
- Axiomas de gobierno (poder explícito, acotado, revocable)
- Función central: evaluar_politica()
- Casos de uso (first tier, límites, revocación)
- Monetización nativa (planes comerciales)

**Documentos relacionados:**
- [AUP_GOV_INTEGRACION_SUMMARY.md](AUP_GOV_INTEGRACION_SUMMARY.md) - Integración con routers
- [AUP_GOV_PLANES_COMERCIALES.md](AUP_GOV_PLANES_COMERCIALES.md) - Planes como composiciones
- [AUP_GOV_PLANES_SUMMARY.md](AUP_GOV_PLANES_SUMMARY.md) - Resumen ejecutivo de planes
- [AUP_GOV_VENTAJA_COMPETITIVA.md](AUP_GOV_VENTAJA_COMPETITIVA.md) - Análisis de barrera de copia

**Archivos de código:**
- `backend/core/gov/__init__.py` - Declaración conceptual
- `backend/core/gov/authority.py` - Gestión de authorities
- `backend/core/gov/policy.py` - Evaluador central de políticas
- `backend/core/gov/delegation.py` - Gestión de delegaciones
- `backend/core/gov/integration.py` - Integración con AUP_EVENT
- `backend/core/gov/facade.py` - Interfaz única para routers
- `backend/core/gov/plans.py` - Planes comerciales (FREE/PRO/ENTERPRISE)
- `scripts/seed_gov_bootstrap.py` - Bootstrap inicial
- `scripts/seed_planes_comerciales.py` - Seed de planes

**Cuándo leerlo:** Para entender gobierno de poder y monetización.
📄 [AUP_SCOPE.md](AUP_SCOPE.md)

**Contenido:**
- Declaración de AUP_TENANT, AUP_SCOPE
- Axiomas de alcance (no-inferencia, frontera, dinamismo)
- Jerarquía de AccessLevel
- Casos de uso (first tier, revocación)
- Diferencia entre JWT (session) y Scope (alcance)

**Archivos de código:**
- `backend/core/scope/__init__.py` - Declaración conceptual
- `backend/core/scope/validator.py` - validar_scope()
- `backend/core/scope/dependencies.py` - FastAPI dependencies
- `backend/db/models.py` - UserTenantScope model
- `scripts/migrate_create_scopes.py` - Migración de scopes

**Cuándo leerlo:** Para entender validación de alcance multi-tenant.

---

### **4. PASO 3: AUP_EVENT (Declaración de Hechos)**
📄 [AUP_EVENT.md](AUP_EVENT.md)

**Contenido:**
- Declaración de AUP_EVENT como entidad de dominio
- Axiomas de eventos (inmutabilidad, universalidad, reconstrucción)
- Tipos estructurales (EventEntity, EventAction, EventResult)
- Hash de inmutabilidad (SHA-256)
- Casos de uso (auditoría, compliance, detección de anomalías)

**Archivos de código:**
- `backend/core/event/__init__.py` - Declaración + enums
- `backend/core/event/registry.py` - registrar_evento()
- `backend/db/models.py` - Event model
- `backend/routers/auth_router.py` - Eventos de login
- `backend/routers/visitas_router.py` - Eventos de visitas
- `backend/routers/qr_router.py` - Eventos de QR

**Cuándo leerlo:** Para entender trazabilidad y auditoría.

---

### **5. Resumen PASO 2 (AUP_SCOPE)**
📄 [AUP_SCOPE_SUMMARY.md](AUP_SCOPE_SUMMARY.md)

**Contenido:**
- Resumen ejecutivo de AUP_SCOPE
- Validación rápida
- Archivos creados
- Preparado para PASO 3

**Cuándo leerlo:** Referencia rápida de AUP_SCOPE.

---

### **6. Diagramas de Flujo Completos**
📄 [AUP_FLOW_COMPLETE.txt](AUP_FLOW_COMPLETE.txt)

**Contenido:**
- Flujo completo: Request → AUP_SESSION → AUP_SCOPE → Negocio → AUP_EVENT → Response
- Diagrama de relaciones entre entidades AUP
- Flujo de login detallado
- Flujo de validación QR (caso complejo con múltiples caminos)
- Queries comunes de eventos

**Cuándo leerlo:** Para visualizar cómo fluyen los datos en el sistema.

---

### **7. Migración Summary (Histórico)**
📄 [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)

**Contenido:**
- Resumen de migración de X-User-Id a JWT
- Endpoints migrados en PASO 1
- Problemas encontrados y soluciones

**Cuándo leerlo:** Para entender el contexto histórico de la migración inicial.

---

## 🗄️ SCRIPTS DE BASE DE DATOS

### **Schema Principal**
📄 `database/schema_axs.sql`

Tablas base del sistema (MSP, Condominio, Usuario, Visita, etc.)

### **Migración PASO 2: AUP_SCOPE**
📄 `database/migration_02_user_tenant_scope.sql` (no existe aún, crear si es necesario)

Crea tabla `user_tenant_scope` con enums ScopeStatus, AccessLevel.

### **Migración PASO 3: AUP_EVENT**
📄 `database/migration_03_events_aup.sql`

**Contenido:**
- Crea tabla `events_aup`
- 7 índices para consultas frecuentes
- Comentarios de documentación en columnas
- Foreign keys a usuarios_exo, condominios_exo, user_tenant_scope

**Ejecutar después de:** schema_axs.sql + migración de scopes

---

## 🧪 SCRIPTS DE UTILIDAD

### **Crear Scopes desde Usuarios Existentes**
📄 `scripts/migrate_create_scopes.py`

**Propósito:** Migrar usuarios existentes (con condominio_id) a sistema de scopes.

**Uso:**
```bash
cd /workspaces/MSP_AXS
python scripts/migrate_create_scopes.py
```

---

## 📂 ESTRUCTURA DE CÓDIGO

### **Módulos Core**

```
backend/core/
├── auth/                    # PASO 1: AUP_SESSION
│   ├── __init__.py
│   ├── password.py          # AUP_CREDENTIAL (bcrypt)
│   ├── jwt.py               # AUP_SESSION (JWT)
│   ├── dependencies.py      # get_current_user()
│   └── schemas.py           # LoginRequest, TokenResponse
│
├── scope/                   # PASO 2: AUP_SCOPE
│   ├── __init__.py          # Declaración conceptual
│   ├── validator.py         # validar_scope()
│   └── dependencies.py      # FastAPI dependencies
│
└── event/                   # PASO 3: AUP_EVENT
    ├── __init__.py          # Declaración + enums
    └── registry.py          # registrar_evento()
```

### **Modelos de BD**

```
backend/db/models.py
├── Usuario                  # AUP_IDENTITY
├── Condominio               # AUP_TENANT
├── UserTenantScope          # AUP_SCOPE
├── Event                    # AUP_EVENT
├── Visita
├── Evidencia
└── ...
```

### **Routers (Endpoints)**

```
backend/routers/
├── auth_router.py           # POST /auth/login (crea AUP_SESSION + EVENT)
├── visitas_router.py        # Validación SESSION + SCOPE + EVENT
├── qr_router.py             # Generar/validar QR + EVENT
├── evidencias_router.py
├── preregistro_router.py
└── ...
```

---

## 🎯 GUÍAS DE LECTURA POR OBJETIVO

### **Entender el Sistema Completo**
1. [AUP_COMPLETE_SUMMARY.md](AUP_COMPLETE_SUMMARY.md) - Visión general
2. [AUP_FLOW_COMPLETE.txt](AUP_FLOW_COMPLETE.txt) - Diagramas visuales
3. Leer cada paso en orden (PASO 1 → PASO 2 → PASO 3)

### **Implementar Nuevos Endpoints**
1. [AUP_AUTHENTICATION.md](AUP_AUTHENTICATION.md) - Cómo validar identidad
2. [AUP_SCOPE.md](AUP_SCOPE.md) - Cómo validar alcance
3. [AUP_EVENT.md](AUP_EVENT.md) - Cómo registrar eventos
4. Ver ejemplos en `backend/routers/visitas_router.py`

### **Debugging de Problemas**
1. Problema de autenticación → [AUP_AUTHENTICATION.md](AUP_AUTHENTICATION.md)
2. Problema de permisos → [AUP_SCOPE.md](AUP_SCOPE.md)
3. Problema de auditoría → [AUP_EVENT.md](AUP_EVENT.md)
4. Revisar eventos en BD: `SELECT * FROM events_aup WHERE resultado = 'denegado'`

### **Preparar Deployment**
1. Ejecutar `database/schema_axs.sql`
2. Ejecutar `database/migration_03_events_aup.sql`
3. Ejecutar `python scripts/migrate_create_scopes.py`
4. Verificar que no hay errores en endpoints
5. Probar login → crear visita → generar QR → validar QR
6. Consultar eventos: `SELECT COUNT(*) FROM events_aup`

### **Auditoría y Compliance**
1. [AUP_EVENT.md](AUP_EVENT.md) - Casos de uso de auditoría
2. Queries en sección "QUERIES COMUNES" de [AUP_FLOW_COMPLETE.txt](AUP_FLOW_COMPLETE.txt)
3. Verificar integridad: `verificar_integridad_evento(evento)`

---

## 🔑 CONCEPTOS CLAVE

### **AUP vs Desarrollo Tradicional**

| Tradicional | AUP |
|-------------|-----|
| "Agregar JWT" | "Declarar AUP_SESSION" |
| "Implementar multi-tenant" | "Declarar AUP_SCOPE" |
| "Agregar logging" | "Declarar AUP_EVENT" |
| Enfoque técnico | Enfoque conceptual |
| Ambiguo | Estructural |
| Difícil validar | Fácil validar |

### **Entidades Centrales**

- **AUP_IDENTITY:** Quién actúa (Usuario)
- **AUP_CREDENTIAL:** Cómo autentica (password_hash)
- **AUP_SESSION:** Contexto temporal (JWT)
- **AUP_TENANT:** Contenedor de datos (Condominio)
- **AUP_SCOPE:** Alcance sobre tenant (UserTenantScope)
- **AUP_EVENT:** Hecho declarado (Event)

### **Axiomas Universales**

1. Sin AUP_SESSION válida → No hay acción
2. Sin AUP_SCOPE válido → No existe operativamente en tenant
3. Sistema NO infiere contexto, lo VALIDA explícitamente
4. Toda acción relevante genera AUP_EVENT
5. AUP_EVENT es inmutable (hash SHA-256)

---

## 📊 MÉTRICAS DEL SISTEMA

### **Archivos Creados:**
- Documentación: 7 archivos (md + txt)
- Código core: 11 archivos Python
- Scripts: 1 migración Python + 1 migración SQL
- **Total:** ~3000 líneas de código + documentación

### **Endpoints Migrados a AUP:**
- ✅ POST /auth/login (SESSION + EVENT)
- ✅ POST /visitas (SESSION + SCOPE + EVENT)
- ✅ POST /qr/generar/{visita_id} (SESSION + EVENT)
- ✅ GET /qr/validar/{visita_id}/{token} (SESSION + EVENT con múltiples caminos)

### **Eventos Implementados:**
- Login exitoso/fallido
- Crear visita (exitoso/denegado)
- Generar QR
- Validar QR (exitoso/denegado: expirado, ya usado, token inválido)

**Total:** 8+ tipos de eventos distintos

---

## 🚀 PRÓXIMOS PASOS SUGERIDOS

1. **Migración de endpoints restantes:**
   - evidencias_router.py
   - preregistro_router.py
   - Agregar validación SCOPE + EVENT

2. **Testing:**
   - Tests unitarios de `registrar_evento()`
   - Tests de integridad de eventos (hash)
   - Tests de validación de scope
   - Tests de integración completos

3. **Monitoreo:**
   - Dashboard de eventos denegados
   - Alertas automáticas ante anomalías (ej: 10 QR inválidos en 5 minutos)
   - Gráficas de uso por tenant

4. **Expansión de eventos:**
   - Evento de revocación de scope
   - Evento de modificación de usuario
   - Evento de carga de evidencia
   - Evento de logout

5. **Optimización:**
   - Índices adicionales según queries frecuentes
   - Archivado de eventos antiguos (>1 año)
   - Caché de scopes activos

---

## 📞 SOPORTE

Para preguntas sobre la arquitectura AUP:
- Revisar [AUP_COMPLETE_SUMMARY.md](AUP_COMPLETE_SUMMARY.md)
- Consultar diagramas en [AUP_FLOW_COMPLETE.txt](AUP_FLOW_COMPLETE.txt)
- Verificar eventos en BD para debugging

Para problemas técnicos:
- Revisar logs: `backend/*.log`
- Consultar eventos denegados: `SELECT * FROM events_aup WHERE resultado = 'denegado'`
- Verificar scopes: `SELECT * FROM user_tenant_scope WHERE usuario_id = 'X'`

---

**Sistema MSP_AXS con Arquitectura AUP Completa**  
**Versión:** 3.0 (3 pasos completados)  
**Última actualización:** 2024-12-29

═══════════════════════════════════════════════════════════════════════════
