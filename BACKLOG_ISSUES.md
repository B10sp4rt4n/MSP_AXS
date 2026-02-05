# Backlog de Issues - MSP_AXS
## Issues priorizados y accionables para próximos 30 días

**Última actualización:** 30 Enero 2026  
**Sistema de priorización:** MoSCoW (Must/Should/Could/Won't)

---

## 🔴 MUST HAVE (Semana 1-2) - MVP Funcional

### Issue #1: Configurar Cloudinary en Producción
**Prioridad:** 🔴 P0 - CRÍTICO  
**Estimación:** 2 horas  
**Bloqueante:** SÍ (bloquea evidencias fotográficas)

**Descripción:**
Sistema de evidencias implementado pero no configurado. Necesitamos credenciales y variables de entorno.

**Tareas:**
- [ ] Crear cuenta Cloudinary (free tier)
- [ ] Obtener credenciales (cloud_name, api_key, api_secret)
- [ ] Agregar a `.env` local
- [ ] Agregar a Railway environment variables
- [ ] Testing: Subir foto de prueba via Postman
- [ ] Verificar foto en Cloudinary console

**Criterio de aceptación:**
- ✅ Foto subida exitosamente vía API
- ✅ URL generada accesible desde navegador
- ✅ Thumbnail de 200x200 generado automáticamente

**Referencias:**
- [CLOUDINARY_SETUP.md](/workspaces/MSP_AXS/docs/CLOUDINARY_SETUP.md)
- [CloudinaryService](/workspaces/MSP_AXS/backend/utils/cloudinary_service.py)

---

### Issue #2: Crear Modelo QRAcceso Persistente
**Prioridad:** 🔴 P0 - CRÍTICO  
**Estimación:** 4 horas  
**Bloqueante:** SÍ (bloquea flujo de autorizaciones)

**Descripción:**
Actualmente QR se genera on-demand sin persistencia. Necesitamos entidad con ciclo de vida completo.

**Tareas:**
- [ ] Crear modelo `QRAcceso` en `backend/db/core/models.py`
  ```python
  class QRAcceso(Base):
      __tablename__ = "qr_accesos"
      qr_id: str (PK)
      visitante_id: str (FK)
      residente_id: str (FK) # Quién autorizó
      vigencia_desde: datetime
      vigencia_hasta: datetime
      estado: str  # ACTIVO, EXPIRADO, REVOCADO, USADO
      uso_maximo: int  # Para visitas recurrentes
      tipo: str  # OCASIONAL, RECURRENTE, SERVICIO
  ```
- [ ] Crear migración `database/migration_05_qr_acceso.sql`
- [ ] Ejecutar migración en SQLite local
- [ ] Crear índices: `idx_qr_vigencia`, `idx_qr_visitante`
- [ ] Testing: CRUD básico (crear, leer, actualizar estado)

**Criterio de aceptación:**
- ✅ Tabla `qr_accesos` creada en BD
- ✅ Puedo crear QR con vigencia de 8 horas
- ✅ QR expira automáticamente después de vigencia_hasta
- ✅ Puedo revocar QR (cambiar estado a REVOCADO)

**Referencias:**
- [PLAN_30_DIAS.md#martes-31-enero](/workspaces/MSP_AXS/PLAN_30_DIAS.md)

---

### Issue #3: Crear Tabla RegistroEscaneo Normalizada
**Prioridad:** 🔴 P0 - CRÍTICO  
**Estimación:** 3 horas  
**Bloqueante:** NO (pero necesario para escalar)

**Descripción:**
Eventos actualmente en `events_aup.datos_json` (no escalable). Necesitamos tabla normalizada con índices.

**Tareas:**
- [ ] Crear modelo `RegistroEscaneo` en `backend/db/event/models.py`
- [ ] Crear migración con índices estratégicos:
  * `idx_qr_timestamp` (búsquedas por QR)
  * `idx_condominio_timestamp` (reportes)
  * `idx_guardia_fecha` (auditoría de guardia)
- [ ] Script de migración: eventos JSON → tabla normalizada
- [ ] Actualizar endpoint `/qr/escanear` para usar tabla
- [ ] Load testing: 100 inserts concurrentes

**Criterio de aceptación:**
- ✅ Tabla `registro_escaneo` creada
- ✅ Eventos históricos migrados (script Python)
- ✅ Query de último escaneo < 10ms (con índice)
- ✅ Reportes de escaneos del día < 50ms

**SQL Schema:**
```sql
CREATE TABLE registro_escaneo (
    escaneo_id VARCHAR(50) PRIMARY KEY,
    qr_id VARCHAR(50) NOT NULL,
    guardia_id VARCHAR(50) NOT NULL,
    condominio_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    resultado VARCHAR(20) NOT NULL,  -- PERMITIDO, DENEGADO
    ubicacion VARCHAR(100),
    dispositivo_id VARCHAR(100),
    FOREIGN KEY (qr_id) REFERENCES qr_accesos(qr_id)
);
```

---

### Issue #4: Endpoint POST /visitantes/autorizar
**Prioridad:** 🔴 P0 - CRÍTICO  
**Estimación:** 3 horas  
**Bloqueante:** SÍ (no hay forma de crear visitantes desde UI)

**Descripción:**
Residente necesita autorizar visitantes desde la app. Endpoint debe crear visitante + QR + enviar SMS.

**Tareas:**
- [ ] Crear endpoint en `backend/routers/visitas_router.py`:
  ```python
  @router.post("/visitantes/autorizar")
  async def autorizar_visitante(
      data: AutorizarVisitanteRequest,
      current_user: dict = Depends(require_role("RESIDENTE"))
  ):
      # 1. Crear visitante en BD
      # 2. Crear QRAcceso con vigencia
      # 3. Generar imagen QR (qrcode library)
      # 4. Subir imagen a Cloudinary
      # 5. Enviar SMS con QR (Twilio)
      # 6. Retornar QR + metadatos
  ```
- [ ] Crear schema `AutorizarVisitanteRequest` en `backend/schemas/visita.py`
- [ ] Testing con Postman
- [ ] Verificar SMS recibido

**Criterio de aceptación:**
- ✅ Residente puede autorizar visitante (nombre, vigencia, tipo)
- ✅ QR generado y guardado en Cloudinary
- ✅ SMS enviado al visitante con link al QR
- ✅ Response incluye `qr_id`, `qr_url`, `visitante_id`

**Payload ejemplo:**
```json
{
  "nombre": "Juan Pérez",
  "telefono": "+5215551234567",
  "ine": "JUPR850101ABC",
  "vigencia_horas": 8,
  "tipo": "OCASIONAL",
  "vehiculo": {
    "placas": "ABC-123",
    "modelo": "Toyota Corolla",
    "color": "Blanco"
  },
  "notas": "Proveedor de internet"
}
```

---

### Issue #5: Endpoint POST /qr/escanear
**Prioridad:** 🔴 P0 - CRÍTICO  
**Estimación:** 3 horas  
**Bloqueante:** SÍ (guardia no puede validar QRs)

**Descripción:**
Guardia necesita escanear QR y validar acceso en tiempo real.

**Tareas:**
- [ ] Crear `backend/routers/qr_router.py`
- [ ] Endpoint `POST /qr/escanear`:
  * Buscar QRAcceso en BD
  * Validar vigencia (now() between vigencia_desde and vigencia_hasta)
  * Validar estado (ACTIVO)
  * Crear RegistroEscaneo
  * Actualizar estado si uso_maximo alcanzado
  * Notificar residente (SMS: "Tu visitante acaba de ingresar")
  * Retornar resultado (PERMITIDO/DENEGADO + motivo)
- [ ] Testing: Casos edge (QR expirado, revocado, no existe)

**Criterio de aceptación:**
- ✅ QR válido → resultado PERMITIDO
- ✅ QR expirado → resultado DENEGADO (motivo: "QR expirado")
- ✅ QR revocado → resultado DENEGADO (motivo: "QR revocado por residente")
- ✅ QR no existe → resultado DENEGADO (motivo: "QR no encontrado")
- ✅ Residente recibe notificación SMS

**Request:**
```json
{
  "qr_id": "qr_abc123",
  "guardia_id": "guardia_001",
  "ubicacion": "Entrada principal"
}
```

**Response:**
```json
{
  "resultado": "PERMITIDO",
  "visitante": {
    "nombre": "Juan Pérez",
    "foto_url": "https://...",
    "vehiculo": "Toyota Corolla ABC-123"
  },
  "autorizado_por": "María García (Casa 15)",
  "vigencia_hasta": "2026-01-30T18:00:00Z"
}
```

---

### Issue #6: Portal HTML guardian.html
**Prioridad:** 🔴 P0 - CRÍTICO  
**Estimación:** 6 horas  
**Bloqueante:** SÍ (guardia necesita interfaz para trabajar)

**Descripción:**
Guardia necesita webapp simple para escanear QR y capturar evidencias. Debe funcionar en smartphone.

**Tareas:**
- [ ] Crear `backend/static/guardian.html`
- [ ] Sección 1: Scanner QR (input text + botón)
- [ ] Sección 2: Resultado validación (PERMITIDO/DENEGADO con colores)
- [ ] Sección 3: Captura evidencias (3 botones: entrada, INE, placas)
- [ ] Sección 4: Historial de escaneos del día (últimos 20)
- [ ] JavaScript:
  * Función `escanearQR()` → POST /qr/escanear
  * Función `subirEvidencia()` → POST /evidencias/entrada/{visita_id}
  * Auto-refresh historial cada 30 segundos
- [ ] CSS responsive (mobile-first)
- [ ] Testing en iPhone + Android

**Criterio de aceptación:**
- ✅ Puedo escanear QR manualmente (input text)
- ✅ Resultado PERMITIDO/DENEGADO visible en < 1 segundo
- ✅ Puedo subir 3 fotos (entrada, INE, placas)
- ✅ Fotos suben a Cloudinary exitosamente
- ✅ Historial muestra últimos 20 escaneos
- ✅ UI responsive (funciona en celular)

**Wireframe:**
```
┌─────────────────────────────┐
│   🔍 Escanear QR            │
│  [_______________] [Validar]│
│                             │
│   ✅ PERMITIDO              │
│   Juan Pérez - Casa 15      │
│   [📸 Foto Entrada]         │
│   [📸 Foto INE]             │
│   [📸 Foto Placas]          │
│                             │
│   Historial (hoy)           │
│   12:30 - Juan P. ✅        │
│   11:45 - María G. ✅       │
│   10:20 - Pedro S. ❌       │
└─────────────────────────────┘
```

---

### Issue #7: Portal HTML residente.html
**Prioridad:** 🔴 P0 - CRÍTICO  
**Estimación:** 5 horas  
**Bloqueante:** SÍ (residente no puede autorizar visitantes)

**Descripción:**
Residente necesita webapp para autorizar visitantes desde smartphone.

**Tareas:**
- [ ] Crear `backend/static/residente.html`
- [ ] Formulario "Autorizar Visitante":
  * Nombre (required)
  * Teléfono (required)
  * INE (optional)
  * Tipo (OCASIONAL/RECURRENTE/SERVICIO)
  * Vigencia desde/hasta (datetime-local)
  * Vehículo (placas, modelo, color)
  * Notas
- [ ] Modal mostrando QR generado:
  * Imagen QR grande
  * Botón "Compartir por WhatsApp"
  * Botón "Descargar QR"
  * Botón "Enviar SMS"
- [ ] Historial de visitantes autorizados
- [ ] Botón "Revocar Acceso" por visitante
- [ ] Testing end-to-end

**Criterio de aceptación:**
- ✅ Puedo autorizar visitante (formulario completo)
- ✅ QR generado visible en < 2 segundos
- ✅ Puedo compartir QR por WhatsApp
- ✅ Puedo descargar imagen QR
- ✅ Puedo revocar acceso (QR pasa a REVOCADO)
- ✅ Historial muestra mis visitantes autorizados

---

## 🟡 SHOULD HAVE (Semana 3) - Producción Robusta

### Issue #8: Migrar a PostgreSQL (NEON)
**Prioridad:** 🟡 P1 - ALTA  
**Estimación:** 8 horas  
**Bloqueante:** NO (SQLite funciona para MVP, pero no escala)

**Descripción:**
SQLite no aguantará 10K ops/día. Necesitamos PostgreSQL con particionamiento.

**Tareas:**
- [ ] Crear cuenta NEON
- [ ] Crear proyecto "MSP_AXS_Production"
- [ ] Obtener connection string
- [ ] Consolidar migraciones en `migration_consolidated.sql`
- [ ] Agregar particionamiento por mes:
  ```sql
  CREATE TABLE registro_escaneo (...)
  PARTITION BY RANGE (timestamp);
  
  CREATE TABLE registro_escaneo_2026_01 PARTITION OF registro_escaneo
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
  ```
- [ ] Migrar datos: SQLite → PostgreSQL
- [ ] Verificar conteos (usuarios, condominios, escaneos)
- [ ] Switchear app a PostgreSQL (cambiar DATABASE_URL)
- [ ] Load testing (100 inserts/segundo)

**Criterio de aceptación:**
- ✅ PostgreSQL conectado
- ✅ Todos los datos migrados (0 pérdidas)
- ✅ App funciona con PostgreSQL (0 errores)
- ✅ Particionamiento automático por mes
- ✅ Performance: INSERT < 10ms, SELECT < 20ms

---

### Issue #9: Redis Caché para Validación QR
**Prioridad:** 🟡 P1 - ALTA  
**Estimación:** 4 horas  
**Bloqueante:** NO (pero mejora latencia 10x)

**Descripción:**
Validación QR actualmente consulta BD cada vez (50ms). Con Redis bajamos a 5ms.

**Tareas:**
- [ ] Instalar Redis local (Docker)
- [ ] Crear `backend/utils/cache_service.py`
- [ ] Método `get_qr(qr_id)` → Buscar en cache primero
- [ ] Método `set_qr(qr_id, data, ttl)` → Guardar en cache
- [ ] Método `invalidate_qr(qr_id)` → Eliminar de cache
- [ ] Integrar en `/qr/escanear`:
  * Primero buscar en Redis
  * Si no existe, buscar en PostgreSQL
  * Guardar en Redis (TTL = vigencia_hasta)
- [ ] Integrar en `/qr/revocar`:
  * Invalidar cache cuando se revoca
- [ ] Load testing: Comparar latencia con/sin cache

**Criterio de aceptación:**
- ✅ Redis conectado
- ✅ QR en cache: latencia < 5ms
- ✅ QR no en cache: latencia < 50ms (BD + cache write)
- ✅ QR revocado: cache invalidado inmediatamente
- ✅ Load test: 1,000 req/s → p95 < 10ms

---

### Issue #10: Notificaciones SMS (Twilio)
**Prioridad:** 🟡 P1 - ALTA  
**Estimación:** 3 horas  
**Bloqueante:** NO (pero crítico para UX)

**Descripción:**
Visitante necesita recibir QR automáticamente por SMS. Residente necesita notificación de llegada.

**Tareas:**
- [ ] Crear cuenta Twilio (trial $15 gratis)
- [ ] Obtener credenciales (account_sid, auth_token, phone_number)
- [ ] Instalar SDK: `pip install twilio`
- [ ] Crear `backend/utils/sms_service.py`:
  * `enviar_qr_visitante(telefono, qr_url, condominio)`
  * `notificar_residente_llegada(telefono, visitante)`
- [ ] Integrar en `/visitantes/autorizar`:
  * Después de generar QR, enviar SMS
- [ ] Integrar en `/qr/escanear`:
  * Después de PERMITIDO, notificar residente
- [ ] Testing: Verificar SMS recibidos

**Criterio de aceptación:**
- ✅ Visitante recibe SMS con QR en < 5 segundos
- ✅ Residente recibe notificación de llegada
- ✅ SMS incluye link a portal visitante
- ✅ Manejo de errores (número inválido, sin saldo)

**Mensajes:**
```
Visitante:
"✅ Tienes acceso a Residencial Los Pinos.
Tu QR: https://res.cloudinary.com/...
Válido hasta: 30 Ene 18:00"

Residente:
"🔔 Juan Pérez acaba de ingresar al condominio.
Autorizado hasta: 18:00"
```

---

### Issue #11: Endpoint POST /qr/revocar
**Prioridad:** 🟡 P1 - ALTA  
**Estimación:** 2 horas  
**Bloqueante:** NO (pero importante para seguridad)

**Descripción:**
Residente necesita cancelar acceso a visitante (cambió de planes, seguridad).

**Tareas:**
- [ ] Endpoint en `qr_router.py`:
  ```python
  @router.post("/qr/revocar")
  async def revocar_qr(
      qr_id: str,
      motivo: Optional[str] = None,
      current_user: dict = Depends(require_role("RESIDENTE"))
  ):
      # 1. Buscar QRAcceso
      # 2. Verificar que current_user es el residente_id (seguridad)
      # 3. Cambiar estado a REVOCADO
      # 4. Invalidar cache (Redis)
      # 5. Notificar visitante por SMS (opcional)
      # 6. Registrar evento en AUP_EVENT
  ```
- [ ] Testing: Revocar QR, intentar escanear (debe fallar)

**Criterio de aceptación:**
- ✅ Solo el residente autorizador puede revocar
- ✅ QR pasa a estado REVOCADO
- ✅ Cache invalidado (Redis)
- ✅ Próximo escaneo retorna DENEGADO
- ✅ Evento registrado en auditoría

---

### Issue #12: Load Testing con Locust
**Prioridad:** 🟡 P1 - ALTA  
**Estimación:** 4 horas  
**Bloqueante:** NO (pero necesario antes de producción)

**Descripción:**
Antes de deploy, debemos validar que el sistema aguanta 100 req/s.

**Tareas:**
- [ ] Instalar Locust: `pip install locust`
- [ ] Crear `tests/load_test.py`:
  ```python
  class GuardiaUser(HttpUser):
      @task
      def escanear_qr(self):
          self.client.post("/api/qr/escanear", json={...})
      
      @task(2)
      def listar_escaneos(self):
          self.client.get("/api/escaneos/hoy")
  ```
- [ ] Ejecutar: `locust --users=100 --spawn-rate=10`
- [ ] Objetivos:
  * Throughput: > 100 req/s
  * Latencia p50: < 50ms
  * Latencia p95: < 100ms
  * Latencia p99: < 200ms
  * Error rate: < 0.1%
- [ ] Identificar bottlenecks (pgAdmin, Redis Monitor)
- [ ] Optimizar (índices, connection pool, cache)
- [ ] Re-ejecutar hasta cumplir objetivos

**Criterio de aceptación:**
- ✅ Sistema aguanta 100 req/s con error rate < 0.1%
- ✅ p95 < 100ms
- ✅ No hay memory leaks
- ✅ PostgreSQL connection pool < 80% capacidad

---

## 🟢 COULD HAVE (Semana 4) - Polish

### Issue #13: Portal HTML visitante.html
**Prioridad:** 🟢 P2 - MEDIA  
**Estimación:** 3 horas  
**Bloqueante:** NO (visitante puede recibir QR por SMS sin portal)

**Descripción:**
Vista simple para que visitante vea su QR y estado en tiempo real.

**Tareas:**
- [ ] Crear `backend/static/visitante.html`
- [ ] Mostrar:
  * QR grande (300x300px)
  * Código QR textual
  * Vigencia desde/hasta
  * Estado (ACTIVO/EXPIRADO/REVOCADO)
  * Info: Condominio, autorizado por, dirección
- [ ] Auto-refresh cada 30 segundos (verificar si sigue activo)
- [ ] Notificación si QR fue revocado
- [ ] Testing en móvil

**Criterio de aceptación:**
- ✅ Visitante puede ver su QR
- ✅ Si QR revocado, muestra mensaje "Acceso cancelado"
- ✅ UI responsive (mobile-first)

---

### Issue #14: Tests End-to-End con Pytest
**Prioridad:** 🟢 P2 - MEDIA  
**Estimación:** 6 horas  
**Bloqueante:** NO (pero recomendado antes de producción)

**Descripción:**
Suite de tests automatizados para validar flujo completo.

**Tareas:**
- [ ] Instalar: `pip install pytest pytest-asyncio httpx`
- [ ] Crear `tests/test_flujo_completo.py`
- [ ] Test 1: Login residente
- [ ] Test 2: Autorizar visitante
- [ ] Test 3: Guardia escanea QR (PERMITIDO)
- [ ] Test 4: Subir evidencia
- [ ] Test 5: Revocar QR
- [ ] Test 6: Escanear QR revocado (DENEGADO)
- [ ] Ejecutar: `pytest tests/ -v --cov=backend`
- [ ] Objetivo: > 80% coverage

**Criterio de aceptación:**
- ✅ Suite completa ejecuta en < 30 segundos
- ✅ Test coverage > 80%
- ✅ 0 tests fallando
- ✅ CI/CD integrado (GitHub Actions)

---

### Issue #15: Documentación Swagger (OpenAPI)
**Prioridad:** 🟢 P2 - MEDIA  
**Estimación:** 3 horas  
**Bloqueante:** NO (pero útil para integraciones)

**Descripción:**
Documentar todos los endpoints con ejemplos y schemas.

**Tareas:**
- [ ] Agregar docstrings a todos los endpoints
- [ ] Configurar OpenAPI en `main.py`
- [ ] Verificar Swagger UI: http://localhost:8000/docs
- [ ] Exportar spec: `curl http://localhost:8000/openapi.json`
- [ ] Crear Postman Collection desde OpenAPI
- [ ] Documentar en README.md

**Criterio de aceptación:**
- ✅ Swagger UI funcional
- ✅ Todos los endpoints documentados
- ✅ Ejemplos de request/response
- ✅ Postman Collection generada

---

### Issue #16: Dashboard Admin (admin.html mejorado)
**Prioridad:** 🟢 P2 - MEDIA  
**Estimación:** 4 horas  
**Bloqueante:** NO

**Descripción:**
Mejorar portal admin existente con métricas y reportes.

**Tareas:**
- [ ] Agregar sección "Métricas Hoy":
  * Total escaneos
  * Escaneos PERMITIDOS/DENEGADOS
  * Evidencias capturadas
  * QRs activos
- [ ] Gráfico de escaneos por hora (Chart.js)
- [ ] Lista de visitantes activos ahora
- [ ] Botón "Exportar CSV" (escaneos del día)

**Criterio de aceptación:**
- ✅ Métricas actualizadas en tiempo real
- ✅ Gráfico de escaneos por hora
- ✅ Exportar CSV funcional

---

## ⚪ WON'T HAVE (Post MVP) - Futuro

### Issue #17: Mobile App (React Native)
**Prioridad:** ⚪ P3 - BAJA (para próximos 60 días)  
**Estimación:** 40 horas  
**Bloqueante:** NO (webapp funciona en móvil)

**Descripción:**
App nativa con scanner QR optimizado y captura de fotos.

**Tareas futuras:**
- Setup React Native
- Autenticación
- Scanner QR nativo (react-native-camera)
- Captura evidencias optimizada
- Push notifications
- Deploy App Store + Play Store

---

### Issue #18: Dashboard Grafana
**Prioridad:** ⚪ P3 - BAJA  
**Estimación:** 16 horas  
**Bloqueante:** NO

**Descripción:**
Métricas avanzadas para MSP_ADMIN y DevOps.

**Tareas futuras:**
- Setup Grafana + Prometheus
- Dashboard de performance
- Dashboard por condominio
- Alertas automáticas

---

### Issue #19: API Pública + Webhooks
**Prioridad:** ⚪ P3 - BAJA  
**Estimación:** 20 horas  
**Bloqueante:** NO

**Descripción:**
Permitir integraciones de terceros.

**Tareas futuras:**
- API Keys por MSP
- Rate limiting
- Webhooks (escaneo.permitido, escaneo.denegado)
- Documentación pública

---

### Issue #20: Reconocimiento Facial
**Prioridad:** ⚪ P4 - MUY BAJA (2027+)  
**Estimación:** 80 horas  
**Bloqueante:** NO

**Descripción:**
Validación adicional biométrica.

**Tareas futuras:**
- Integrar AWS Rekognition
- Captura facial en entrada
- Comparación con foto autorizada
- Lista negra automática

---

## 📊 Resumen de Prioridades

| Prioridad | Cantidad | Estimación Total | Semana |
|-----------|----------|------------------|--------|
| 🔴 P0 (MUST) | 7 issues | 26 horas | 1-2 |
| 🟡 P1 (SHOULD) | 5 issues | 21 horas | 3 |
| 🟢 P2 (COULD) | 4 issues | 16 horas | 4 |
| ⚪ P3-P4 (WON'T) | 4 issues | 156 horas | Post MVP |
| **TOTAL MVP** | **16 issues** | **63 horas** | **30 días** |

---

## 🚀 Sprint Velocidad Recomendada

**Asumiendo 1 desarrollador full-time:**
- Semana 1: Issues #1-4 (13 horas) ✅ Factible
- Semana 2: Issues #5-7 (14 horas) ✅ Factible
- Semana 3: Issues #8-12 (21 horas) ⚠️ Intenso
- Semana 4: Issues #13-16 (16 horas) ✅ Factible + testing

**Asumiendo 2 desarrolladores:**
- Velocity: 80 horas/semana
- Semana 1-2: Completar todos los MUST (26h)
- Semana 3: Completar todos los SHOULD (21h)
- Semana 4: Completar todos los COULD (16h) + buffer

---

## 📝 Notas para Ejecución

### Priorización Diaria
1. Resolver issues P0 primero (bloqueantes)
2. Si estás bloqueado en P0, trabajar en P1
3. No empezar P2 hasta terminar todos P0 y P1

### Definition of Done
- [ ] Código implementado
- [ ] Tests pasando (si aplica)
- [ ] Documentación actualizada
- [ ] Code review (si hay equipo)
- [ ] Testing manual en local
- [ ] Git commit con mensaje descriptivo
- [ ] Issue cerrado en tracker

### Riesgos
- **Riesgo #1:** Cloudinary sin configurar → BLOQUEA evidencias
  * Mitigación: Hacer Issue #1 el PRIMER día
- **Riesgo #2:** PostgreSQL migración toma > 8h
  * Mitigación: Mantener SQLite funcionando en paralelo
- **Riesgo #3:** Twilio sin saldo
  * Mitigación: Monitorear balance diario, topup automático

---

**Última actualización:** 30 Enero 2026  
**Mantenedor:** Equipo MSP_AXS  
**Revisión:** Diaria durante Sprint 1-2, semanal después
