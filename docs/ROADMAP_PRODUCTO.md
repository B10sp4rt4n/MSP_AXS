# Roadmap del Producto MSP_AXS
## Sistema de Gestión de Accesos - Versión 2.0

**Última actualización:** Enero 2026  
**Objetivo:** Escalar de 10K a 5M escaneos diarios en 3 años

---

## 🎯 Visión General

MSP_AXS es una plataforma multi-tenant de gestión de accesos para condominios residenciales, operada por empresas de seguridad (MSPs). El sistema gestiona el ciclo completo de visitantes mediante QR codes, con evidencias fotográficas y gobernanza automatizada.

### Arquitectura Multi-Tenant
```
MSP (Empresa de Seguridad)
  └─ Condominio (cliente del MSP)
      └─ Casa (unidad habitacional)
          └─ Habitante (Residente)
```

### Roles del Sistema
- **MSP_ADMIN**: Administrador de la empresa de seguridad
- **ADMIN_CONDOMINIO**: Administrador del condominio
- **GUARDIA**: Personal de seguridad (punto de entrada)
- **RESIDENTE**: Habitante que autoriza visitantes
- **VISITANTE**: Usuario temporal con QR de acceso

---

## 📊 Proyecciones de Escala

| Fase | Timeline | MSPs | Condominios | Escaneos/Día | Usuarios Concurrentes |
|------|----------|------|-------------|--------------|----------------------|
| **MVP** | Q1 2026 | 1-2 | 5-10 | 100-500 | 10-20 |
| **Año 1** | Q2-Q4 2026 | 5-10 | 100 | 10K | 500-1K |
| **Año 2** | 2027 | 50 | 500 | 500K | 10K-20K |
| **Año 3+** | 2028+ | 200+ | 2K+ | 2-5M | 50K-100K |

---

## 🚀 Fase 1: MVP Consolidado (Q1 2026)
### Prioridad: CRÍTICA ⚠️

### ✅ Completado

#### 1. Autenticación y Sesiones
- [x] JWT con tokens de 8 horas
- [x] Middleware AUP_SESSION (validación en todos los endpoints)
- [x] Roles y permisos básicos
- [x] CORS configurado

#### 2. Gobernanza (AUP_GOV)
- [x] Políticas de límites por tenant
- [x] Validación de cuotas (max_count, max_por_mes)
- [x] Registro de decisiones en `gov_decisiones`

#### 3. CRUD Básico
- [x] MSPs, Condominios, Casas, Habitantes
- [x] Endpoint `/condominios/crear` funcional
- [x] Panel admin.html con formularios
- [x] Validación de campos

#### 4. Base de Datos
- [x] SQLite (desarrollo)
- [x] Esquema normalizado con foreign keys
- [x] Migración a PostgreSQL (NEON) planificada

### 🔄 En Progreso

#### 5. **Sistema de Evidencias con Cloudinary** ⭐ **NUEVO**
**Estado:** Implementación completa, pendiente configuración

**Archivos creados:**
- [`backend/utils/cloudinary_service.py`](/workspaces/MSP_AXS/backend/utils/cloudinary_service.py) - Servicio de Cloudinary
- [`backend/routers/evidencias_router_cloudinary.py`](/workspaces/MSP_AXS/backend/routers/evidencias_router_cloudinary.py) - Router mejorado
- [`docs/CLOUDINARY_SETUP.md`](/workspaces/MSP_AXS/docs/CLOUDINARY_SETUP.md) - Guía de configuración
- [`docs/CLOUDINARY_MIGRATION.md`](/workspaces/MSP_AXS/docs/CLOUDINARY_MIGRATION.md) - Plan de migración

**Beneficios:**
- ☁️ Almacenamiento escalable (sin límites de storage en servidor)
- 🌐 CDN global (fotos rápidas desde cualquier ubicación)
- 🖼️ Transformaciones on-the-fly (thumbnails automáticos)
- 💰 Plan gratuito hasta 25 GB/mes
- 📊 Métricas de uso integradas

**Pendiente:**
- [ ] Configurar cuenta Cloudinary (cloud_name, api_key, api_secret)
- [ ] Agregar variables de entorno en Railway
- [ ] Instalar dependencia: `pip install cloudinary`
- [ ] Integrar router en `main.py`
- [ ] Crear formulario en `guardian.html`
- [ ] Testing end-to-end

**Documentación completa:** Ver [CLOUDINARY_MIGRATION.md](CLOUDINARY_MIGRATION.md)

---

### ❌ Pendiente (Crítico para MVP)

#### 6. QRAcceso como Entidad Persistente
**Problema:** Actualmente QR se genera on-demand, no tiene ciclo de vida.

**Solución:**
```python
class QRAcceso:
    qr_id: str (PK)
    visitante_id: str
    residente_id: str (autorizador)
    vigencia_desde: datetime
    vigencia_hasta: datetime
    estado: str  # ACTIVO, EXPIRADO, REVOCADO, USADO
    uso_maximo: int  # Visitas recurrentes
    scans: List[RegistroEscaneo]  # Auditoría completa
```

**Endpoints:**
- `POST /qr/generar` → Crea QRAcceso con vigencia
- `POST /qr/escanear` → Registra uso en RegistroEscaneo
- `POST /qr/revocar` → Cambia estado a REVOCADO
- `GET /qr/{qr_id}/status` → Estado actual + historial de scans

#### 7. RegistroEscaneo Normalizado
**Problema:** Eventos en JSON (columna `datos_json`), no escalable.

**Solución:** Tabla normalizada con índices estratégicos
```sql
CREATE TABLE registro_escaneo (
    escaneo_id VARCHAR(50) PRIMARY KEY,
    qr_id VARCHAR(50) NOT NULL,
    guardia_id VARCHAR(50) NOT NULL,
    condominio_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    resultado VARCHAR(20) NOT NULL,  -- PERMITIDO, DENEGADO, EXPIRADO
    ubicacion VARCHAR(100),
    dispositivo_id VARCHAR(100),
    INDEX idx_qr_timestamp (qr_id, timestamp),
    INDEX idx_condominio_timestamp (condominio_id, timestamp),
    INDEX idx_guardia_fecha (guardia_id, DATE(timestamp))
);
```

#### 8. Portales por Rol
**Problema:** Solo existe `admin.html`, no hay UI para guardias ni residentes.

**Solución:** 5 portales especializados
- [ ] `msp-admin.html` → Dashboard de MSP (gestión de condominios)
- [ ] `admin-condominio.html` → Dashboard de condominio (gestión de casas)
- [ ] `guardian.html` → Panel de guardia (escaneo QR + evidencias)
- [ ] `residente.html` → Portal de residente (autorizar visitantes)
- [ ] `visitante.html` → Vista simple (mostrar QR + estado)

#### 9. Flujo Completo Residente → Visitante
**Problema:** No hay endpoint para que el residente autorice visitantes.

**Solución:**
```javascript
// Residente autoriza visitante
POST /visitantes/autorizar
{
    "nombre": "Juan Pérez",
    "ine": "JUPR850101ABC",
    "vigencia_desde": "2026-01-30T10:00:00Z",
    "vigencia_hasta": "2026-01-30T18:00:00Z",
    "tipo": "OCASIONAL",  // OCASIONAL, RECURRENTE, SERVICIO
    "vehiculo": { "placas": "ABC-123", "modelo": "Toyota Corolla" },
    "notas": "Proveedor de internet"
}

// Response: QR generado + SMS enviado al visitante
{
    "qr_id": "qr_abc123",
    "qr_image_base64": "...",
    "qr_url": "https://res.cloudinary.com/.../qr_abc123.png",
    "visitante": {
        "visitante_id": "vis_xyz789",
        "nombre": "Juan Pérez"
    }
}
```

#### 10. Notificaciones Básicas
**Problema:** Sin comunicación automática con visitantes/residentes.

**Solución (Fase 1 - SMS):**
- [ ] Integrar Twilio para SMS
- [ ] Enviar QR al visitante por SMS
- [ ] Notificar al residente cuando el visitante llega
- [ ] Alertas de seguridad (intentos de acceso denegado)

**Variables de entorno:**
```bash
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+52...
```

---

## 🏗️ Fase 2: Producción Estable (Q2-Q4 2026)
### Prioridad: ALTA 🔥

### 1. Migración a PostgreSQL (NEON)
**Objetivo:** Escalar a 10K escaneos/día con performance < 100ms.

**Plan:**
- [ ] Crear instancia NEON (primary + read replica)
- [ ] Migrar esquema con particionamiento:
  ```sql
  -- Particionar por MSP + mes
  CREATE TABLE registro_escaneo_2026_01 PARTITION OF registro_escaneo
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
  ```
- [ ] Configurar connection pooling (pgBouncer)
- [ ] Índices estratégicos:
  - `idx_qr_timestamp` (búsquedas por QR)
  - `idx_condominio_timestamp` (reportes por condominio)
  - `idx_guardia_fecha` (auditoría de guardia)
- [ ] Backup diario automático

**Herramientas:**
- NEON (PostgreSQL serverless)
- pgBouncer (connection pooling)
- pgAdmin (gestión visual)

### 2. Redis para Caching
**Objetivo:** Reducir latencia de validación QR de 50ms → 5ms.

**Caché:**
- QR activos (key: `qr:{qr_id}`, TTL: vigencia_hasta)
- Usuario sesiones (key: `session:{token}`, TTL: 8h)
- GOV policies (key: `gov:pol_{policy_id}`, TTL: 1h)
- Estructura de condominio (key: `condo:{id}`, TTL: 5min)

**Configuración:**
```python
import redis
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=6379,
    db=0,
    decode_responses=True
)

# Validar QR con cache
def validar_qr_cached(qr_id: str) -> dict:
    # Intentar cache
    cached = redis_client.get(f"qr:{qr_id}")
    if cached:
        return json.loads(cached)
    
    # Si no está en cache, buscar en BD
    qr_data = db.query(QRAcceso).filter_by(qr_id=qr_id).first()
    
    # Guardar en cache
    redis_client.setex(
        f"qr:{qr_id}",
        ttl=3600,  # 1 hora
        value=json.dumps(qr_data)
    )
    
    return qr_data
```

### 3. Mobile App para Guardias
**Objetivo:** Scanner nativo con cámara optimizada.

**Tecnología:** React Native / Flutter

**Features:**
- 📷 Escaneo QR con cámara nativa
- 📸 Captura de evidencias (foto visitante, INE, placas)
- 📶 Modo offline (queue de escaneos cuando no hay red)
- 🔔 Notificaciones push (alertas de seguridad)
- 📊 Dashboard de actividad diaria

**Pantallas:**
1. Login
2. Scanner QR (pantalla principal)
3. Detalle de visita (foto, nombre, autorizado por)
4. Captura de evidencias
5. Historial de escaneos del día
6. Alertas/Incidentes

### 4. Mobile App para Residentes
**Objetivo:** Autorizar visitantes desde smartphone.

**Tecnología:** React Native / Flutter (mismo codebase que Guardias)

**Features:**
- ✅ Autorizar visitante (formulario simple)
- 📱 Compartir QR por WhatsApp/SMS
- 🔔 Notificaciones de llegada
- 📋 Historial de visitas autorizadas
- ❌ Revocar acceso (cancelar QR)
- 👨‍👩‍👧 Gestión de habitantes de la casa

### 5. Dashboard de Métricas
**Objetivo:** Visibilidad de operación para MSP_ADMIN y ADMIN_CONDOMINIO.

**Tecnología:** Grafana + PostgreSQL

**Métricas:**
- 📊 Escaneos por día/semana/mes
- 👥 Visitantes únicos por condominio
- ⏱️ Horarios pico de acceso
- 🚨 Intentos denegados (% y causas)
- 📸 Evidencias capturadas (% de visitas con foto)
- ⚡ Performance (latencia promedio de validación)
- 💰 Uso por tenant (facturación)

**Dashboards:**
1. Overview general (MSP_ADMIN)
2. Performance técnico (DevOps)
3. Condominio específico (ADMIN_CONDOMINIO)
4. Guardia individual (supervisión)

---

## 🌟 Fase 3: Diferenciación Competitiva (2027)
### Prioridad: MEDIA 📈

### 1. Integración con Hardware
**Objetivo:** Sistema completo con barreras/torniquetes automáticos.

**Hardware compatible:**
- Lectores QR industriales (Zebra, Honeywell)
- Barreras vehiculares (FAAC, BFT)
- Torniquetes peatonales (Turnstile)
- Cámaras IP (reconocimiento facial futuro)

**Protocolo:** REST API + WebSockets para control en tiempo real

### 2. Reconocimiento Facial (Opcional)
**Objetivo:** Validación adicional sin contacto.

**Tecnología:** AWS Rekognition / Azure Face API

**Casos de uso:**
- Verificar que la persona del QR es quien ingresa
- Lista negra de personas no autorizadas
- Alertas automáticas (persona no reconocida)

### 3. Smart Home Integration
**Objetivo:** Abrir puerta de casa automáticamente cuando visitante llega.

**Integraciones:**
- Google Home
- Amazon Alexa
- Apple HomeKit

**Flujo:**
1. Guardia escanea QR → Acceso PERMITIDO
2. Webhook a casa del residente
3. Cerradura inteligente se desbloquea por 30 segundos
4. Residente recibe notificación push

### 4. Sistema de Facturación
**Objetivo:** Cobro automatizado a MSPs por uso.

**Modelo de pricing:**
```
Plan Básico: $99/mes
- Hasta 5 condominios
- 1,000 escaneos/mes
- Soporte email

Plan Profesional: $299/mes
- Hasta 20 condominios
- 10,000 escaneos/mes
- Soporte prioritario
- Dashboard avanzado

Plan Enterprise: Custom
- Condominios ilimitados
- Escaneos ilimitados
- SLA 99.9%
- Integración personalizada
```

**Integración:** Stripe / PayPal

### 5. API Pública + Webhooks
**Objetivo:** Permitir integraciones de terceros.

**Endpoints públicos:**
- `POST /api/v1/visitante/crear` → Registrar visitante desde ERP
- `GET /api/v1/visitas/condominio/{id}` → Obtener visitas del día
- `POST /webhooks/escaneo` → Notificar cuando hay escaneo

**Autenticación:** API Keys por MSP

**Webhooks:**
```json
POST https://cliente.com/webhook/axs
{
    "event": "escaneo.permitido",
    "timestamp": "2026-01-30T15:30:00Z",
    "data": {
        "qr_id": "qr_abc123",
        "visitante": "Juan Pérez",
        "condominio": "Residencial Los Pinos",
        "guardia": "Carlos Martínez"
    }
}
```

---

## 🔒 Seguridad y Compliance (Transversal)
### Prioridad: CRÍTICA ⚠️

### 1. Auditoría Completa
- [ ] Logging estructurado (JSON) en todos los eventos críticos
- [ ] Registro inmutable de escaneos (no se pueden eliminar)
- [ ] Tracking de acciones de administradores
- [ ] Retención de logs: 2 años mínimo

### 2. GDPR / Protección de Datos
- [ ] Consentimiento explícito para captura de fotos
- [ ] Derecho al olvido (eliminar datos de visitante)
- [ ] Encriptación de datos sensibles (INE, fotos)
- [ ] Policy de retención: 90 días por defecto

### 3. Certificaciones
- [ ] ISO 27001 (seguridad de información)
- [ ] SOC 2 Type II (controles de seguridad)
- [ ] Pentest anual por terceros

### 4. Rate Limiting y Anti-Abuse
- [ ] Max 100 requests/minuto por usuario
- [ ] Max 10 intentos de login fallidos → Bloqueo 15 min
- [ ] Detección de patrones anómalos (ML)

---

## 📈 Innovación Futura (2028+)
### Prioridad: BAJA 🔮

### 1. Análisis Predictivo con IA
- Predecir horarios pico de visitas
- Detectar patrones anómalos de acceso
- Optimizar distribución de guardias

### 2. Blockchain para Auditoría
- Registro inmutable en blockchain pública
- Proof of timestamp para evidencias
- Smart contracts para gobernanza

### 3. IoT Sensores
- Conteo de personas en tiempo real
- Detección de aglomeraciones
- Alertas de capacidad máxima

---

## ✅ Checklist de Prioridades (Próximos 30 días)

### Semana 1: Cloudinary + QRAcceso
- [ ] Configurar Cloudinary (cloud_name, api_key, api_secret)
- [ ] Instalar dependencia: `pip install cloudinary`
- [ ] Integrar router en `main.py`
- [ ] Testing: Subir foto de prueba
- [ ] Crear modelo `QRAcceso` en BD
- [ ] Endpoints: `/qr/generar`, `/qr/escanear`, `/qr/revocar`

### Semana 2: Portales + RegistroEscaneo
- [ ] Crear `guardian.html` (scanner + evidencias)
- [ ] Crear `residente.html` (autorizar visitantes)
- [ ] Migrar eventos a tabla `registro_escaneo`
- [ ] Índices estratégicos en PostgreSQL
- [ ] Testing de performance (100 escaneos concurrentes)

### Semana 3: Notificaciones + PostgreSQL
- [ ] Integrar Twilio para SMS
- [ ] Enviar QR al visitante por SMS
- [ ] Notificar residente cuando visitante llega
- [ ] Configurar NEON PostgreSQL
- [ ] Migrar BD SQLite → PostgreSQL

### Semana 4: Testing + Documentación
- [ ] Test end-to-end de flujo completo
- [ ] Load test: 1,000 requests/segundo
- [ ] Documentar APIs (Swagger/OpenAPI)
- [ ] Capacitación a equipo de soporte
- [ ] Deploy a Railway (staging)

---

## 🎯 Métricas de Éxito

| KPI | Q1 2026 | Q2 2026 | Q4 2026 | 2027 |
|-----|---------|---------|---------|------|
| **MSPs activos** | 2 | 5 | 10 | 50 |
| **Condominios** | 10 | 50 | 100 | 500 |
| **Escaneos/día** | 500 | 2K | 10K | 500K |
| **Uptime** | 99% | 99.5% | 99.9% | 99.95% |
| **Latencia (p95)** | < 200ms | < 100ms | < 50ms | < 20ms |
| **Costo/escaneo** | $0.01 | $0.005 | $0.001 | $0.0005 |
| **NPS** | - | 50+ | 60+ | 70+ |

---

## 📚 Documentación Relacionada

- [CLOUDINARY_SETUP.md](CLOUDINARY_SETUP.md) - Guía de configuración de Cloudinary
- [CLOUDINARY_MIGRATION.md](CLOUDINARY_MIGRATION.md) - Plan de migración de evidencias
- [AUP_COMPLETE_SUMMARY.md](AUP_COMPLETE_SUMMARY.md) - Arquitectura AUP completa
- [AUP_GOV_SUMMARY.md](AUP_GOV_SUMMARY.md) - Sistema de gobernanza
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Guía de deployment a Railway

---

**Mantenedor:** Equipo MSP_AXS  
**Última revisión:** 30 Enero 2026  
**Próxima revisión:** 15 Febrero 2026
