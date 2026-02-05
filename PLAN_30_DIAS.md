# Plan de Acción: Próximos 30 Días
## MSP_AXS - De MVP a Producción

**Fecha inicio:** 30 Enero 2026  
**Fecha fin:** 28 Febrero 2026  
**Objetivo:** Completar MVP funcional end-to-end listo para 10 clientes piloto

---

## 📅 SEMANA 1: Cloudinary + QRAcceso (30 Ene - 5 Feb)

### **Lunes 30 Enero** - Cloudinary Setup
- [ ] 9:00 AM - Crear cuenta Cloudinary (https://cloudinary.com/users/register/free)
- [ ] 9:30 AM - Obtener credenciales (Dashboard → Settings → Access Keys)
- [ ] 10:00 AM - Agregar variables de entorno:
  ```bash
  # .env
  CLOUDINARY_CLOUD_NAME=tu_cloud_name
  CLOUDINARY_API_KEY=123456789012345
  CLOUDINARY_API_SECRET=tu_api_secret_aqui
  ```
- [ ] 10:30 AM - Instalar dependencia:
  ```bash
  pip install cloudinary
  pip freeze > requirements.txt
  ```
- [ ] 11:00 AM - Integrar router en `backend/main.py`:
  ```python
  from .routers import evidencias_router_cloudinary
  app.include_router(evidencias_router_cloudinary.router, prefix="/api", tags=["Evidencias"])
  ```
- [ ] 11:30 AM - Testing: Subir foto de prueba con Postman
- [ ] 12:00 PM - Verificar foto en Cloudinary console

### **Martes 31 Enero** - Modelo QRAcceso
- [ ] 9:00 AM - Crear `backend/db/models/qr_acceso.py`:
  ```python
  class QRAcceso(Base):
      __tablename__ = "qr_accesos"
      qr_id = Column(String(50), primary_key=True)
      visitante_id = Column(String(50), ForeignKey("visitantes.visitante_id"))
      residente_id = Column(String(50), ForeignKey("habitantes.habitante_id"))
      vigencia_desde = Column(DateTime, nullable=False)
      vigencia_hasta = Column(DateTime, nullable=False)
      estado = Column(String(20), default="ACTIVO")  # ACTIVO, EXPIRADO, REVOCADO, USADO
      uso_maximo = Column(Integer, default=1)
      tipo = Column(String(20))  # OCASIONAL, RECURRENTE, SERVICIO
      created_at = Column(DateTime, default=datetime.utcnow)
  ```
- [ ] 10:00 AM - Crear migración:
  ```bash
  cd database
  cat > migration_05_qr_acceso.sql << 'EOF'
  CREATE TABLE qr_accesos (
      qr_id VARCHAR(50) PRIMARY KEY,
      visitante_id VARCHAR(50) NOT NULL,
      residente_id VARCHAR(50) NOT NULL,
      vigencia_desde TIMESTAMP NOT NULL,
      vigencia_hasta TIMESTAMP NOT NULL,
      estado VARCHAR(20) DEFAULT 'ACTIVO',
      uso_maximo INTEGER DEFAULT 1,
      tipo VARCHAR(20),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (visitante_id) REFERENCES visitantes(visitante_id),
      FOREIGN KEY (residente_id) REFERENCES habitantes(habitante_id)
  );
  CREATE INDEX idx_qr_vigencia ON qr_accesos(vigencia_hasta);
  CREATE INDEX idx_qr_visitante ON qr_accesos(visitante_id);
  EOF
  sqlite3 ../axs_event.db < migration_05_qr_acceso.sql
  ```
- [ ] 11:00 AM - Crear `backend/services/qr_service.py`
- [ ] 12:00 PM - Testing: Crear QR con vigencia de 8 horas

### **Miércoles 1 Febrero** - Endpoints QR
- [ ] 9:00 AM - Crear `backend/routers/qr_router.py`
- [ ] 9:30 AM - Endpoint `POST /qr/generar`:
  ```python
  @router.post("/generar")
  async def generar_qr(
      visitante_id: str,
      vigencia_horas: int = 8,
      tipo: str = "OCASIONAL",
      current_user: dict = Depends(get_current_user)
  ):
      # 1. Validar que current_user es RESIDENTE
      # 2. Crear QRAcceso en BD
      # 3. Generar imagen QR con qrcode library
      # 4. Subir imagen a Cloudinary
      # 5. Retornar URL + metadatos
  ```
- [ ] 11:00 AM - Endpoint `POST /qr/escanear`:
  ```python
  @router.post("/escanear")
  async def escanear_qr(
      qr_id: str,
      guardia_id: str,
      ubicacion: Optional[str] = None
  ):
      # 1. Buscar QRAcceso en BD
      # 2. Validar vigencia (vigencia_hasta > now)
      # 3. Validar estado (ACTIVO)
      # 4. Crear RegistroEscaneo
      # 5. Actualizar estado si uso_maximo alcanzado
      # 6. Retornar resultado (PERMITIDO/DENEGADO)
  ```
- [ ] 2:00 PM - Endpoint `POST /qr/revocar`
- [ ] 3:00 PM - Endpoint `GET /qr/{qr_id}/status`
- [ ] 4:00 PM - Testing end-to-end: Generar → Escanear → Revocar

### **Jueves 2 Febrero** - RegistroEscaneo Normalizado
- [ ] 9:00 AM - Crear `backend/db/models/registro_escaneo.py`:
  ```python
  class RegistroEscaneo(Base):
      __tablename__ = "registro_escaneo"
      escaneo_id = Column(String(50), primary_key=True)
      qr_id = Column(String(50), ForeignKey("qr_accesos.qr_id"))
      guardia_id = Column(String(50), ForeignKey("usuarios.usuario_id"))
      condominio_id = Column(String(50), ForeignKey("condominios.condominio_id"))
      timestamp = Column(DateTime, default=datetime.utcnow, index=True)
      resultado = Column(String(20), nullable=False)  # PERMITIDO, DENEGADO, EXPIRADO
      ubicacion = Column(String(100))
      dispositivo_id = Column(String(100))
  ```
- [ ] 10:00 AM - Crear migración con índices estratégicos:
  ```sql
  CREATE TABLE registro_escaneo (
      escaneo_id VARCHAR(50) PRIMARY KEY,
      qr_id VARCHAR(50) NOT NULL,
      guardia_id VARCHAR(50) NOT NULL,
      condominio_id VARCHAR(50) NOT NULL,
      timestamp TIMESTAMP NOT NULL,
      resultado VARCHAR(20) NOT NULL,
      ubicacion VARCHAR(100),
      dispositivo_id VARCHAR(100),
      FOREIGN KEY (qr_id) REFERENCES qr_accesos(qr_id),
      FOREIGN KEY (guardia_id) REFERENCES usuarios(usuario_id),
      FOREIGN KEY (condominio_id) REFERENCES condominios(condominio_id)
  );
  CREATE INDEX idx_qr_timestamp ON registro_escaneo(qr_id, timestamp);
  CREATE INDEX idx_condominio_timestamp ON registro_escaneo(condominio_id, timestamp);
  CREATE INDEX idx_guardia_fecha ON registro_escaneo(guardia_id, date(timestamp));
  ```
- [ ] 11:00 AM - Migrar eventos de `events_aup` a `registro_escaneo` (script)
- [ ] 2:00 PM - Actualizar `/qr/escanear` para usar RegistroEscaneo
- [ ] 3:00 PM - Testing: 100 escaneos concurrentes con `locust`
- [ ] 4:00 PM - Verificar índices: `EXPLAIN QUERY PLAN SELECT ...`

### **Viernes 3 Febrero** - Revisión Semana 1
- [ ] 9:00 AM - Testing end-to-end completo:
  * Crear visitante
  * Generar QR con vigencia 8 horas
  * Subir foto de entrada a Cloudinary
  * Escanear QR (PERMITIDO)
  * Verificar RegistroEscaneo en BD
  * Subir foto de salida
  * Revocar QR
  * Intentar escanear (DENEGADO)
- [ ] 11:00 AM - Documentar APIs en Swagger
- [ ] 2:00 PM - Code review (si hay equipo) o self-review
- [ ] 3:00 PM - Git commit: "feat: QRAcceso + RegistroEscaneo + Cloudinary complete"
- [ ] 4:00 PM - Deploy a Railway staging
- [ ] 5:00 PM - Smoke test en staging

---

## 📅 SEMANA 2: Portales HTML + Flujo Completo (6-12 Feb)

### **Lunes 6 Febrero** - Portal Guardia (guardian.html)
- [ ] 9:00 AM - Crear `backend/static/guardian.html`
- [ ] 9:30 AM - UI: Scanner QR (input manual o lector)
  ```html
  <div class="scanner-section">
      <h2>Escanear QR de Visitante</h2>
      <input type="text" id="qr_id" placeholder="Escanea o escribe el código QR" />
      <button onclick="escanearQR()">Validar Acceso</button>
      <div id="resultado"></div>
  </div>
  ```
- [ ] 10:30 AM - Función JavaScript para escanear:
  ```javascript
  async function escanearQR() {
      const qr_id = document.getElementById('qr_id').value;
      const guardia_id = localStorage.getItem('usuario_id');
      
      const response = await fetch('/api/qr/escanear', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ qr_id, guardia_id })
      });
      
      const result = await response.json();
      
      if (result.resultado === 'PERMITIDO') {
          mostrarExito(result.visitante);
          mostrarFormularioEvidencia();
      } else {
          mostrarError(result.motivo);
      }
  }
  ```
- [ ] 11:30 AM - Sección de captura de evidencias:
  ```html
  <div class="evidencia-section" style="display:none" id="evidencia-form">
      <h3>Capturar Evidencia Fotográfica</h3>
      <input type="file" id="foto_entrada" accept="image/*" capture="environment" />
      <button onclick="subirEvidencia('entrada')">Subir Foto Entrada</button>
      <input type="file" id="foto_ine" accept="image/*" />
      <button onclick="subirEvidencia('ine')">Subir INE</button>
      <input type="file" id="foto_placas" accept="image/*" />
      <button onclick="subirEvidencia('placas')">Subir Placas</button>
  </div>
  ```
- [ ] 2:00 PM - Integrar con `/api/evidencias/entrada/{visita_id}` (Cloudinary)
- [ ] 3:00 PM - Historial de escaneos del día (últimos 20)
- [ ] 4:00 PM - Testing: Flujo completo desde guardian.html

### **Martes 7 Febrero** - Portal Residente (residente.html)
- [ ] 9:00 AM - Crear `backend/static/residente.html`
- [ ] 9:30 AM - Formulario "Autorizar Visitante":
  ```html
  <form id="form-autorizar">
      <h2>Autorizar Nuevo Visitante</h2>
      <input type="text" name="nombre" placeholder="Nombre completo" required />
      <input type="text" name="ine" placeholder="INE (opcional)" />
      <select name="tipo">
          <option value="OCASIONAL">Ocasional</option>
          <option value="RECURRENTE">Recurrente</option>
          <option value="SERVICIO">Servicio</option>
      </select>
      <input type="datetime-local" name="vigencia_desde" />
      <input type="datetime-local" name="vigencia_hasta" />
      <textarea name="notas" placeholder="Notas adicionales"></textarea>
      <fieldset>
          <legend>Vehículo (opcional)</legend>
          <input type="text" name="placas" placeholder="Placas" />
          <input type="text" name="modelo" placeholder="Modelo" />
          <input type="text" name="color" placeholder="Color" />
      </fieldset>
      <button type="submit">Generar QR de Acceso</button>
  </form>
  ```
- [ ] 11:00 AM - Endpoint `POST /visitantes/autorizar`:
  ```python
  @router.post("/autorizar")
  async def autorizar_visitante(
      data: dict,
      current_user: dict = Depends(require_role("RESIDENTE"))
  ):
      # 1. Crear visitante en BD
      # 2. Crear QRAcceso con vigencia
      # 3. Generar imagen QR
      # 4. Subir a Cloudinary
      # 5. Enviar SMS con QR (Twilio)
      # 6. Retornar QR + metadatos
  ```
- [ ] 2:00 PM - Modal mostrando QR generado:
  ```html
  <div id="qr-modal" class="modal">
      <h3>✅ Visitante Autorizado</h3>
      <img id="qr-image" src="" alt="QR Code" />
      <p>QR enviado por SMS a: <span id="telefono"></span></p>
      <button onclick="compartirWhatsApp()">Compartir por WhatsApp</button>
      <button onclick="descargarQR()">Descargar QR</button>
  </div>
  ```
- [ ] 3:00 PM - Historial de visitantes autorizados
- [ ] 4:00 PM - Botón "Revocar Acceso" (llamar a `/qr/revocar`)

### **Miércoles 8 Febrero** - Portal Visitante (visitante.html)
- [ ] 9:00 AM - Crear `backend/static/visitante.html`
- [ ] 9:30 AM - Vista simple con QR grande:
  ```html
  <div class="visitante-view">
      <h2>Tu Código de Acceso</h2>
      <img id="qr-code" src="" style="width: 300px; height: 300px;" />
      <p class="qr-id">Código: <strong id="qr-id"></strong></p>
      <div class="vigencia">
          <p>Válido desde: <span id="vigencia-desde"></span></p>
          <p>Válido hasta: <span id="vigencia-hasta"></span></p>
      </div>
      <div class="estado">
          <span class="badge" id="estado-badge">ACTIVO</span>
      </div>
      <div class="info">
          <p>Condominio: <span id="condominio-nombre"></span></p>
          <p>Autorizado por: <span id="residente-nombre"></span></p>
          <p>Dirección: <span id="direccion"></span></p>
      </div>
  </div>
  ```
- [ ] 10:30 AM - Endpoint `GET /visitantes/mi-qr`:
  ```python
  @router.get("/mi-qr")
  async def obtener_mi_qr(
      current_user: dict = Depends(require_role("VISITANTE"))
  ):
      # 1. Buscar QRAcceso activo del visitante
      # 2. Retornar datos + URL de imagen Cloudinary
  ```
- [ ] 11:30 AM - Auto-refresh cada 30 segundos (verificar si QR sigue activo)
- [ ] 12:00 PM - Notificación si QR fue revocado
- [ ] 2:00 PM - Testing: Flujo completo end-to-end
  * Residente autoriza visitante
  * Visitante recibe SMS con link
  * Visitante abre link → ve su QR
  * Guardia escanea QR → PERMITIDO
  * Guardia sube foto entrada
  * Visitante sale, guardia escanea → PERMITIDO
  * Guardia sube foto salida

### **Jueves 9 Febrero** - Notificaciones SMS (Twilio)
- [ ] 9:00 AM - Crear cuenta Twilio (https://www.twilio.com/try-twilio)
- [ ] 9:30 AM - Obtener credenciales:
  ```bash
  # .env
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_PHONE_NUMBER=+521234567890
  ```
- [ ] 10:00 AM - Instalar SDK:
  ```bash
  pip install twilio
  ```
- [ ] 10:30 AM - Crear `backend/utils/sms_service.py`:
  ```python
  from twilio.rest import Client
  
  class SMSService:
      def __init__(self):
          self.client = Client(
              os.getenv("TWILIO_ACCOUNT_SID"),
              os.getenv("TWILIO_AUTH_TOKEN")
          )
          self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
      
      def enviar_qr_visitante(self, telefono: str, qr_url: str, condominio: str):
          mensaje = f"""
          ✅ Tienes acceso autorizado a {condominio}
          
          Tu código QR: {qr_url}
          
          Muestra este código al guardia en la entrada.
          """
          
          self.client.messages.create(
              body=mensaje,
              from_=self.from_number,
              to=telefono
          )
      
      def notificar_residente_llegada(self, telefono: str, visitante: str):
          mensaje = f"🔔 {visitante} acaba de ingresar al condominio."
          
          self.client.messages.create(
              body=mensaje,
              from_=self.from_number,
              to=telefono
          )
  ```
- [ ] 11:30 AM - Integrar en `/visitantes/autorizar`:
  * Después de generar QR, enviar SMS al visitante
- [ ] 12:00 PM - Integrar en `/qr/escanear`:
  * Después de PERMITIDO, notificar al residente
- [ ] 2:00 PM - Testing: Verificar SMS recibidos
- [ ] 3:00 PM - Manejar errores (número inválido, cuenta sin saldo)
- [ ] 4:00 PM - Dashboard de mensajes enviados (histórico)

### **Viernes 10 Febrero** - Integración en main.py
- [ ] 9:00 AM - Actualizar `backend/main.py`:
  ```python
  from .routers import (
      auth_router,
      condominios_router,
      visitas_router,
      evidencias_router_cloudinary,
      qr_router  # NUEVO
  )
  
  app.include_router(auth_router.router, prefix="/api/auth", tags=["Autenticación"])
  app.include_router(condominios_router.router, prefix="/api", tags=["Condominios"])
  app.include_router(evidencias_router_cloudinary.router, prefix="/api/evidencias", tags=["Evidencias"])
  app.include_router(qr_router.router, prefix="/api/qr", tags=["QR"])
  ```
- [ ] 9:30 AM - Agregar rutas estáticas para portales:
  ```python
  @app.get("/guardian")
  async def portal_guardia():
      return FileResponse("backend/static/guardian.html")
  
  @app.get("/residente")
  async def portal_residente():
      return FileResponse("backend/static/residente.html")
  
  @app.get("/visitante")
  async def portal_visitante():
      return FileResponse("backend/static/visitante.html")
  ```
- [ ] 10:00 AM - Testing local: http://localhost:8000/guardian
- [ ] 10:30 AM - Git commit: "feat: Portales HTML + Flujo completo Residente→Visitante→Guardia"
- [ ] 11:00 AM - Deploy a Railway staging
- [ ] 11:30 AM - Smoke test en staging
- [ ] 12:00 PM - Documentar flujo en README.md

### **Fin de Semana (11-12 Feb)** - Buffer / Refactoring
- [ ] Refactorizar código duplicado
- [ ] Mejorar manejo de errores
- [ ] Agregar logging estructurado
- [ ] Actualizar documentación

---

## 📅 SEMANA 3: PostgreSQL + Redis + Performance (13-19 Feb)

### **Lunes 13 Febrero** - Configurar NEON PostgreSQL
- [ ] 9:00 AM - Crear cuenta NEON (https://console.neon.tech/signup)
- [ ] 9:30 AM - Crear proyecto "MSP_AXS_Production"
- [ ] 10:00 AM - Crear base de datos:
  * Primary: `axs_production`
  * Read replica: `axs_production_replica`
- [ ] 10:30 AM - Obtener connection string:
  ```bash
  # .env
  DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/axs_production?sslmode=require
  DATABASE_URL_REPLICA=postgresql://user:password@ep-xxx-replica.us-east-2.aws.neon.tech/axs_production?sslmode=require
  ```
- [ ] 11:00 AM - Instalar dependencias:
  ```bash
  pip install psycopg2-binary sqlalchemy asyncpg
  ```
- [ ] 11:30 AM - Actualizar `backend/db/connection.py`:
  ```python
  DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./axs_event.db")
  engine = create_engine(DATABASE_URL)
  ```
- [ ] 12:00 PM - Testing: Conectar a NEON con psql

### **Martes 14 Febrero** - Migración de Esquema
- [ ] 9:00 AM - Consolidar todas las migraciones en un solo script:
  ```bash
  cd database
  cat migration_*.sql > migration_consolidated.sql
  ```
- [ ] 9:30 AM - Agregar particionamiento por MSP + mes:
  ```sql
  -- Tabla principal
  CREATE TABLE registro_escaneo (
      escaneo_id VARCHAR(50) PRIMARY KEY,
      qr_id VARCHAR(50) NOT NULL,
      msp_id VARCHAR(50) NOT NULL,  -- Agregar para particionamiento
      timestamp TIMESTAMP NOT NULL,
      resultado VARCHAR(20) NOT NULL,
      -- ... resto de columnas
  ) PARTITION BY RANGE (timestamp);
  
  -- Particiones mensuales
  CREATE TABLE registro_escaneo_2026_01 PARTITION OF registro_escaneo
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
  
  CREATE TABLE registro_escaneo_2026_02 PARTITION OF registro_escaneo
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
  
  -- Índices por partición
  CREATE INDEX idx_escaneo_qr_2026_01 ON registro_escaneo_2026_01(qr_id);
  CREATE INDEX idx_escaneo_condo_2026_01 ON registro_escaneo_2026_01(condominio_id);
  ```
- [ ] 11:00 AM - Ejecutar migración en NEON:
  ```bash
  psql $DATABASE_URL -f migration_consolidated.sql
  ```
- [ ] 11:30 AM - Verificar tablas:
  ```sql
  \dt
  SELECT schemaname, tablename, partitioned FROM pg_tables WHERE schemaname = 'public';
  ```
- [ ] 12:00 PM - Crear script de backup diario:
  ```bash
  #!/bin/bash
  # backup_daily.sh
  DATE=$(date +%Y%m%d)
  pg_dump $DATABASE_URL > backups/axs_$DATE.sql
  aws s3 cp backups/axs_$DATE.sql s3://msp-axs-backups/
  ```

### **Miércoles 15 Febrero** - Migración de Datos SQLite → PostgreSQL
- [ ] 9:00 AM - Exportar datos de SQLite:
  ```bash
  sqlite3 axs_event.db .dump > sqlite_export.sql
  ```
- [ ] 9:30 AM - Transformar SQL (SQLite → PostgreSQL):
  ```python
  # scripts/transform_sqlite_to_postgres.py
  with open('sqlite_export.sql') as f:
      sql = f.read()
      # Reemplazar sintaxis SQLite
      sql = sql.replace('AUTOINCREMENT', 'SERIAL')
      sql = sql.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
      # Guardar
      with open('postgres_import.sql', 'w') as out:
          out.write(sql)
  ```
- [ ] 10:30 AM - Importar a PostgreSQL:
  ```bash
  psql $DATABASE_URL -f postgres_import.sql
  ```
- [ ] 11:00 AM - Verificar conteos:
  ```sql
  SELECT 'usuarios' as tabla, COUNT(*) FROM usuarios
  UNION ALL
  SELECT 'condominios', COUNT(*) FROM condominios
  UNION ALL
  SELECT 'qr_accesos', COUNT(*) FROM qr_accesos;
  ```
- [ ] 11:30 AM - Testing: Ejecutar queries de la app contra PostgreSQL
- [ ] 2:00 PM - Switchear app a usar PostgreSQL (cambiar DATABASE_URL en .env)
- [ ] 3:00 PM - Smoke test completo
- [ ] 4:00 PM - Monitorear performance con pgAdmin

### **Jueves 16 Febrero** - Redis Caché
- [ ] 9:00 AM - Instalar Redis local:
  ```bash
  docker run -d -p 6379:6379 redis:alpine
  ```
- [ ] 9:30 AM - Instalar SDK:
  ```bash
  pip install redis aioredis
  ```
- [ ] 10:00 AM - Crear `backend/utils/cache_service.py`:
  ```python
  import redis
  import json
  from datetime import timedelta
  
  class CacheService:
      def __init__(self):
          self.redis = redis.Redis(
              host=os.getenv("REDIS_HOST", "localhost"),
              port=6379,
              db=0,
              decode_responses=True
          )
      
      def get_qr(self, qr_id: str) -> dict | None:
          cached = self.redis.get(f"qr:{qr_id}")
          if cached:
              return json.loads(cached)
          return None
      
      def set_qr(self, qr_id: str, data: dict, ttl_seconds: int):
          self.redis.setex(
              f"qr:{qr_id}",
              timedelta(seconds=ttl_seconds),
              json.dumps(data)
          )
      
      def invalidate_qr(self, qr_id: str):
          self.redis.delete(f"qr:{qr_id}")
  ```
- [ ] 11:00 AM - Integrar en `/qr/escanear`:
  ```python
  @router.post("/escanear")
  async def escanear_qr(qr_id: str, guardia_id: str):
      # 1. Intentar cache
      qr_data = cache_service.get_qr(qr_id)
      
      # 2. Si no está en cache, buscar en BD
      if not qr_data:
          qr = db.query(QRAcceso).filter_by(qr_id=qr_id).first()
          if not qr:
              return {"resultado": "DENEGADO", "motivo": "QR no encontrado"}
          
          qr_data = qr.to_dict()
          # Guardar en cache por 1 hora
          cache_service.set_qr(qr_id, qr_data, ttl_seconds=3600)
      
      # 3. Validar vigencia
      if datetime.now() > qr_data['vigencia_hasta']:
          return {"resultado": "DENEGADO", "motivo": "QR expirado"}
      
      # 4. Validar estado
      if qr_data['estado'] != 'ACTIVO':
          return {"resultado": "DENEGADO", "motivo": f"QR {qr_data['estado']}"}
      
      # 5. Registrar escaneo
      escaneo = RegistroEscaneo(...)
      db.add(escaneo)
      db.commit()
      
      return {"resultado": "PERMITIDO", "visitante": qr_data['visitante']}
  ```
- [ ] 2:00 PM - Integrar en `/qr/revocar`:
  * Invalidar cache cuando se revoca QR
- [ ] 3:00 PM - Load test: Comparar latencia con/sin cache
  ```bash
  # Sin cache
  ab -n 1000 -c 10 http://localhost:8000/api/qr/escanear
  
  # Con cache
  ab -n 1000 -c 10 http://localhost:8000/api/qr/escanear
  ```
- [ ] 4:00 PM - Documentar resultados (esperado: 50ms → 5ms)

### **Viernes 17 Febrero** - Load Testing + Optimización
- [ ] 9:00 AM - Instalar herramientas:
  ```bash
  pip install locust pytest-benchmark
  ```
- [ ] 9:30 AM - Crear `tests/load_test.py`:
  ```python
  from locust import HttpUser, task, between
  
  class GuardiaUser(HttpUser):
      wait_time = between(1, 3)
      
      @task
      def escanear_qr(self):
          self.client.post("/api/qr/escanear", json={
              "qr_id": "qr_test_123",
              "guardia_id": "guardia_001"
          })
      
      @task(2)
      def listar_escaneos(self):
          self.client.get("/api/escaneos/hoy")
  ```
- [ ] 10:30 AM - Ejecutar load test:
  ```bash
  locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10
  ```
- [ ] 11:00 AM - Objetivos:
  * Latencia p50 < 50ms
  * Latencia p95 < 100ms
  * Latencia p99 < 200ms
  * Throughput > 100 req/s
  * Error rate < 0.1%
- [ ] 2:00 PM - Identificar bottlenecks (pgAdmin + Redis Monitor)
- [ ] 3:00 PM - Optimizaciones:
  * Agregar índices faltantes
  * Aumentar connection pool (SQLAlchemy)
  * Configurar Redis maxmemory policy
- [ ] 4:00 PM - Re-ejecutar load test → Verificar mejoras
- [ ] 5:00 PM - Documentar resultados en PERFORMANCE.md

### **Fin de Semana (18-19 Feb)** - Monitoreo + Observabilidad
- [ ] Configurar Prometheus + Grafana
- [ ] Métricas custom (escaneos/min, latencia, errores)
- [ ] Alertas (latencia > 200ms, error rate > 1%)
- [ ] Dashboard público para clientes (uptime, escaneos totales)

---

## 📅 SEMANA 4: Testing + Documentación + Deploy (20-26 Feb)

### **Lunes 20 Febrero** - Testing End-to-End
- [ ] 9:00 AM - Instalar pytest + plugins:
  ```bash
  pip install pytest pytest-asyncio pytest-cov httpx
  ```
- [ ] 9:30 AM - Crear `tests/test_flujo_completo.py`:
  ```python
  import pytest
  from httpx import AsyncClient
  from backend.main import app
  
  @pytest.mark.asyncio
  async def test_flujo_completo_visitante():
      async with AsyncClient(app=app, base_url="http://test") as client:
          # 1. Login residente
          login_resp = await client.post("/api/auth/login", json={
              "username": "residente_test",
              "password": "test123"
          })
          assert login_resp.status_code == 200
          token = login_resp.json()["access_token"]
          headers = {"Authorization": f"Bearer {token}"}
          
          # 2. Autorizar visitante
          autorizar_resp = await client.post("/api/visitantes/autorizar", 
              json={
                  "nombre": "Juan Test",
                  "vigencia_horas": 8,
                  "tipo": "OCASIONAL"
              },
              headers=headers
          )
          assert autorizar_resp.status_code == 200
          qr_id = autorizar_resp.json()["qr_id"]
          
          # 3. Guardia escanea QR
          escaneo_resp = await client.post("/api/qr/escanear",
              json={"qr_id": qr_id, "guardia_id": "guardia_test"}
          )
          assert escaneo_resp.status_code == 200
          assert escaneo_resp.json()["resultado"] == "PERMITIDO"
          
          # 4. Subir evidencia
          with open("tests/fixtures/foto_test.jpg", "rb") as f:
              evidencia_resp = await client.post(
                  f"/api/evidencias/entrada/{qr_id}",
                  files={"foto": f}
              )
          assert evidencia_resp.status_code == 200
          
          # 5. Revocar QR
          revocar_resp = await client.post(f"/api/qr/revocar",
              json={"qr_id": qr_id},
              headers=headers
          )
          assert revocar_resp.status_code == 200
          
          # 6. Intentar escanear QR revocado (debe fallar)
          escaneo2_resp = await client.post("/api/qr/escanear",
              json={"qr_id": qr_id, "guardia_id": "guardia_test"}
          )
          assert escaneo2_resp.json()["resultado"] == "DENEGADO"
  ```
- [ ] 11:00 AM - Tests unitarios para servicios:
  * `tests/test_qr_service.py`
  * `tests/test_cloudinary_service.py`
  * `tests/test_sms_service.py`
- [ ] 2:00 PM - Ejecutar suite completa:
  ```bash
  pytest tests/ -v --cov=backend --cov-report=html
  ```
- [ ] 3:00 PM - Objetivo: > 80% coverage
- [ ] 4:00 PM - Revisar reporte: `open htmlcov/index.html`

### **Martes 21 Febrero** - Documentación APIs (Swagger)
- [ ] 9:00 AM - Agregar docstrings a todos los endpoints:
  ```python
  @router.post("/qr/generar", response_model=QRResponse)
  async def generar_qr(
      data: QRGenerarRequest,
      current_user: dict = Depends(require_role("RESIDENTE"))
  ):
      """
      Genera un código QR de acceso para un visitante.
      
      Args:
          data: Datos del visitante y vigencia del QR
          current_user: Usuario autenticado (debe ser RESIDENTE)
      
      Returns:
          QRResponse con qr_id, imagen, URL y metadatos
      
      Raises:
          HTTPException 403: Si el usuario no es RESIDENTE
          HTTPException 400: Si los datos son inválidos
      
      Example:
          ```json
          {
              "nombre": "Juan Pérez",
              "vigencia_horas": 8,
              "tipo": "OCASIONAL"
          }
          ```
      """
  ```
- [ ] 11:00 AM - Configurar OpenAPI en main.py:
  ```python
  app = FastAPI(
      title="MSP_AXS API",
      description="Sistema de gestión de accesos para condominios",
      version="2.0.0",
      docs_url="/docs",
      redoc_url="/redoc"
  )
  ```
- [ ] 12:00 PM - Verificar Swagger UI: http://localhost:8000/docs
- [ ] 2:00 PM - Exportar OpenAPI spec:
  ```bash
  curl http://localhost:8000/openapi.json > docs/openapi.json
  ```
- [ ] 3:00 PM - Crear Postman Collection desde OpenAPI
- [ ] 4:00 PM - Documentar en README.md cómo usar las APIs

### **Miércoles 22 Febrero** - Deploy a Railway (Producción)
- [ ] 9:00 AM - Verificar `railway.json`:
  ```json
  {
      "$schema": "https://railway.app/railway.schema.json",
      "build": {
          "builder": "NIXPACKS"
      },
      "deploy": {
          "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
          "healthcheckPath": "/health",
          "restartPolicyType": "ON_FAILURE",
          "restartPolicyMaxRetries": 10
      }
  }
  ```
- [ ] 9:30 AM - Configurar variables de entorno en Railway:
  * DATABASE_URL (NEON)
  * REDIS_HOST (Railway Redis addon)
  * CLOUDINARY_* (credenciales)
  * TWILIO_* (credenciales)
  * SECRET_KEY (generar nuevo)
- [ ] 10:00 AM - Git commit: "chore: Preparar deploy producción"
- [ ] 10:30 AM - Push a main:
  ```bash
  git push origin main
  ```
- [ ] 11:00 AM - Railway detecta push → Deploy automático
- [ ] 11:30 AM - Monitorear logs:
  ```bash
  railway logs --tail
  ```
- [ ] 12:00 PM - Verificar health check:
  ```bash
  curl https://msp-axs.up.railway.app/health
  ```
- [ ] 2:00 PM - Smoke test en producción:
  * Login admin
  * Crear condominio
  * Crear residente
  * Autorizar visitante
  * Escanear QR
  * Subir evidencia
- [ ] 3:00 PM - Configurar dominio custom (si aplica):
  * axs.tusitio.com
- [ ] 4:00 PM - Configurar SSL (Railway lo hace automático)

### **Jueves 23 Febrero** - Capacitación Interna
- [ ] 9:00 AM - Crear guía de usuario:
  * docs/GUIA_RESIDENTE.md (cómo autorizar visitantes)
  * docs/GUIA_GUARDIA.md (cómo escanear QR y subir fotos)
  * docs/GUIA_ADMIN.md (cómo gestionar condominios)
- [ ] 11:00 AM - Video tutorial (screen recording):
  * Flujo completo end-to-end (5 minutos)
  * Subir a YouTube (unlisted)
- [ ] 2:00 PM - Sesión de Q&A con equipo (si aplica)
- [ ] 4:00 PM - Documentar FAQs en README.md

### **Viernes 24 Febrero** - Preparar Piloto (10 Clientes)
- [ ] 9:00 AM - Crear checklist de onboarding:
  ```markdown
  ## Checklist Onboarding Cliente
  
  ### Pre-requisitos
  - [ ] Contrato firmado
  - [ ] Datos de contacto (admin + guardias)
  - [ ] Logo del condominio
  - [ ] Lista de casas/departamentos
  
  ### Setup Técnico
  - [ ] Crear MSP en plataforma
  - [ ] Crear condominio
  - [ ] Importar casas (CSV)
  - [ ] Crear usuarios:
    - [ ] ADMIN_CONDOMINIO (1)
    - [ ] GUARDIA (2-5)
  - [ ] Configurar notificaciones SMS
  
  ### Capacitación
  - [ ] Sesión con admin (30 min)
  - [ ] Sesión con guardias (45 min)
  - [ ] Enviar video tutorial
  - [ ] Entregar guías PDF
  
  ### Go-Live
  - [ ] Crear 5 residentes de prueba
  - [ ] Generar 10 QRs de prueba
  - [ ] Escanear QRs → Validar PERMITIDO/DENEGADO
  - [ ] Subir evidencias de prueba
  - [ ] Verificar notificaciones SMS
  
  ### Post Go-Live
  - [ ] Follow-up día 1, 3, 7
  - [ ] Recopilar feedback
  - [ ] Iterar según necesidades
  ```
- [ ] 10:00 AM - Crear plantilla de contrato piloto:
  * Gratis por 90 días
  * Hasta 50 casas
  * 500 escaneos/mes incluidos
  * Soporte prioritario
- [ ] 11:00 AM - Identificar 10 candidatos:
  * Condominios pequeños (20-50 casas)
  * Actualmente usan papel/Excel
  * Con MSP partner
- [ ] 2:00 PM - Preparar presentación de ventas (slides)
- [ ] 4:00 PM - Enviar propuesta a primeros 3 candidatos

### **Fin de Semana (25-26 Feb)** - Buffer / Hotfixes
- [ ] Monitorear producción
- [ ] Resolver bugs críticos (si aparecen)
- [ ] Preparar demo para inversores (opcional)

---

## 📅 SEMANA 5: Retrospectiva + Próximos Pasos (27 Feb - 28 Feb)

### **Jueves 27 Febrero** - Retrospectiva 30 Días
- [ ] 9:00 AM - Reunión retrospectiva:
  * ¿Qué salió bien?
  * ¿Qué salió mal?
  * ¿Qué aprendimos?
  * ¿Qué cambiaríamos?
- [ ] 10:00 AM - Revisar métricas:
  * Escaneos realizados
  * Evidencias capturadas
  * Latencia promedio (p50, p95, p99)
  * Uptime
  * Errores reportados
- [ ] 11:00 AM - Feedback de pilotos:
  * Encuesta NPS (Net Promoter Score)
  * Solicitudes de features
  * Bugs reportados
- [ ] 2:00 PM - Actualizar roadmap para próximos 60 días:
  * Priorizar features más solicitados
  * Ajustar timelines según aprendizajes

### **Viernes 28 Febrero** - Planificación Marzo-Abril
- [ ] 9:00 AM - Definir objetivos Q1:
  * Objetivo 1: 10 clientes piloto activos
  * Objetivo 2: 10,000 escaneos/mes
  * Objetivo 3: Latencia p95 < 50ms
  * Objetivo 4: NPS > 50
  * Objetivo 5: 0 incidentes críticos
- [ ] 10:00 AM - Roadmap Mobile Apps (React Native):
  * Semana 1-2: Setup + Autenticación
  * Semana 3-4: Scanner QR + Evidencias (Guardia)
  * Semana 5-6: Autorización visitantes (Residente)
  * Semana 7-8: Testing + Deploy (App Store + Play Store)
- [ ] 11:00 AM - Roadmap Dashboard Métricas (Grafana):
  * Semana 1: Setup Grafana + Prometheus
  * Semana 2: Dashboards básicos (escaneos, latencia)
  * Semana 3: Dashboards avanzados (por condominio, por guardia)
  * Semana 4: Alertas automáticas
- [ ] 2:00 PM - Definir budget para Q1:
  * Infraestructura: $500/mes (Railway + NEON + Redis)
  * Cloudinary: $50/mes (Plan Plus)
  * Twilio: $100/mes (SMS)
  * Herramientas: $200/mes (Grafana Cloud, Sentry)
  * **Total:** $850/mes
- [ ] 3:00 PM - Plan de contrataciones (si aplica):
  * Desarrollador mobile (React Native)
  * Diseñador UI/UX (medio tiempo)
  * DevOps (medio tiempo)
- [ ] 4:00 PM - Actualizar pitch deck para inversores:
  * Slides actualizados con métricas reales
  * Demo video
  * Testimonios de pilotos
  * Ask: $500K Seed @ $1.5M pre-money

---

## ✅ Criterios de Éxito (Fin de 30 Días)

### Funcionalidad
- [x] Flujo completo Residente → Visitante → Guardia funcionando
- [x] Cloudinary integrado y funcionando
- [x] QR persistentes con ciclo de vida (ACTIVO → USADO/REVOCADO/EXPIRADO)
- [x] Notificaciones SMS automáticas (Twilio)
- [x] Evidencias fotográficas en cada visita
- [x] 3 portales HTML funcionales (guardian.html, residente.html, visitante.html)

### Performance
- [x] Latencia p95 < 100ms (objetivo: < 50ms)
- [x] PostgreSQL con particionamiento mensual
- [x] Redis caché para QRs activos
- [x] Throughput > 100 req/s
- [x] Uptime > 99.5%

### Testing
- [x] > 80% test coverage
- [x] Suite de tests end-to-end
- [x] Load testing (1,000 req/s)
- [x] 0 bugs críticos en producción

### Documentación
- [x] APIs documentadas en Swagger
- [x] Guías de usuario (residente, guardia, admin)
- [x] Video tutorial (5 min)
- [x] FAQs actualizadas

### Go-to-Market
- [x] Deploy a Railway (producción)
- [x] 10 clientes piloto identificados
- [x] Primeros 3 contratos firmados
- [x] Onboarding checklist listo

---

## 📊 Métricas a Monitorear (Diarias)

### Técnicas
- **Uptime**: > 99.5% (máximo 3.6 horas downtime/mes)
- **Latencia p50**: < 50ms
- **Latencia p95**: < 100ms
- **Latencia p99**: < 200ms
- **Throughput**: > 100 req/s
- **Error rate**: < 0.1%

### Negocio
- **Escaneos/día**: > 500 (objetivo: 10K en Q2)
- **Visitantes únicos/mes**: > 100
- **Evidencias capturadas**: > 90% de visitas
- **SMS enviados**: > 200/mes
- **Clientes piloto activos**: > 3 (objetivo: 10 en 60 días)

### Producto
- **NPS (Net Promoter Score)**: > 50
- **Tiempo promedio de autorización**: < 2 min
- **Tiempo promedio de escaneo**: < 30 seg
- **Bugs reportados/semana**: < 5
- **Features solicitadas/semana**: > 10 (señal de engagement)

---

## 🚨 Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **SQLite no aguanta carga** | Alta | Alto | ✅ Migrar a PostgreSQL semana 3 |
| **Cloudinary muy caro** | Media | Medio | Monitor usage, comprimir fotos, purge cada 90 días |
| **Twilio sin saldo** | Media | Alto | Alertas cuando saldo < $20, topup automático |
| **Guardias no tienen smartphone** | Alta | Alto | Webapp responsive, funciona en cualquier celular |
| **Residentes no adoptan sistema** | Media | Alto | Video tutorial, incentivos (sorteos), soporte 24/7 |
| **Latencia > 200ms** | Media | Medio | Redis caché, CDN Cloudinary, optimizar queries |
| **Bugs en producción** | Media | Alto | Tests > 80%, staging environment, rollback automático |
| **Infraestructura > $1K/mes** | Baja | Medio | Monitor costos diarios, optimizar uso Cloudinary/Twilio |

---

## 📞 Contactos Clave

### Proveedores
- **Railway**: support@railway.app (infraestructura)
- **NEON**: support@neon.tech (PostgreSQL)
- **Cloudinary**: support@cloudinary.com (imágenes)
- **Twilio**: support@twilio.com (SMS)

### Comunidad
- **Railway Discord**: https://discord.gg/railway
- **FastAPI Discord**: https://discord.gg/fastapi
- **PostgreSQL Slack**: https://slack.postgresql.org

---

## 🎯 Próximos Hitos (Post 30 Días)

### Marzo 2026
- [ ] 10 clientes piloto activos
- [ ] 10,000 escaneos/mes
- [ ] Mobile app MVP (Guardia + Residente)
- [ ] Dashboard Grafana con métricas

### Abril 2026
- [ ] 20 clientes activos
- [ ] 50,000 escaneos/mes
- [ ] NPS > 60
- [ ] Primeros $5K MRR

### Q2 2026
- [ ] 50 clientes activos
- [ ] 500,000 escaneos/mes
- [ ] $25K MRR
- [ ] Seed fundraising ($500K @ $1.5M pre-money)

---

**Última actualización:** 30 Enero 2026  
**Responsable:** Founder MSP_AXS  
**Revisión:** Diaria (primeros 30 días), semanal (después)
