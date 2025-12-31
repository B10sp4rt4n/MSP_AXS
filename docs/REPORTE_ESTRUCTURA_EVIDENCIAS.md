# 📊 REPORTE: Análisis de Estructura de Tabla Evidencias

**Fecha:** 31 de diciembre de 2025  
**Sistema:** MSP_AXS  
**Componente:** Tabla `evidencias` (AUP_CORE)  
**Revisor:** Claude (Arquitectura AUP)

---

## 1. PROPUESTA ORIGINAL

```sql
CREATE TABLE evidencias (
    evidencia_id UUID PRIMARY KEY,
    visita_id UUID NOT NULL REFERENCES visitas(visita_id),
    tipo TEXT NOT NULL,
    categoria TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 2. IMPLEMENTACIÓN ACTUAL

```python
class Evidencia(Base_CORE):
    __tablename__ = "evidencias"
    
    id = Column(Integer, primary_key=True, index=True)
    evidencia_id = Column(String, unique=True, index=True)
    visita_id = Column(String, ForeignKey("visitas.visita_id"), index=True)
    categoria = Column(String)        # entrada / salida
    sub_tipo = Column(String)         # visitante, ine_frente, ine_reverso, placas, vehiculo, documento
    archivo_url = Column(Text)
    hash_sha256 = Column(Text)
    guardia_id = Column(String, ForeignKey("usuarios.usuario_id"))
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 3. ANÁLISIS DE DIFERENCIAS

### 3.1 Inconsistencia en Tipos de ID

| Aspecto | Propuesta | Sistema Actual | Impacto |
|---------|-----------|----------------|---------|
| Tipo de ID | `UUID` nativo | `String` (36 chars) | ⚠️ **INCONSISTENCIA** |
| Generación | PostgreSQL | Python `uuid.uuid4()` | Todo el código usa String |
| PK Técnico | Solo `evidencia_id` | `id` (Integer) + `evidencia_id` (String) | Sistema usa doble PK |

**Problema:** El sistema completo usa `String` para UUIDs. Cambiar a `UUID` nativo requeriría migrar:
- 7 tablas (usuarios, condominios, msps, visitas, evidencias, casetas, scopes)
- Todos los foreign keys
- Toda la lógica de generación de IDs en Python

**Recomendación:** Mantener `String` por consistencia.

---

### 3.2 Campo `tipo` Ambiguo

**Propuesta:**
- `tipo TEXT NOT NULL` (único campo, semántica poco clara)

**Sistema Actual:**
- `categoria`: entrada/salida
- `sub_tipo`: visitante, ine_frente, ine_reverso, placas, vehiculo, documento

**Ventaja de separación:**
```python
# Query simple
evidencias_entrada = db.query(Evidencia).filter(Evidencia.categoria == 'entrada')

# Query específica
fotos_ine = db.query(Evidencia).filter(
    Evidencia.categoria == 'entrada',
    Evidencia.sub_tipo.in_(['ine_frente', 'ine_reverso'])
)
```

**Recomendación:** Mantener `categoria` + `sub_tipo`.

---

### 3.3 Falta de Contexto de Identidad (AUP_IDENTITY)

**Propuesta:**
- ❌ No tiene campo `guardia_id`

**Sistema Actual:**
- ✅ `guardia_id` vinculado a `usuarios.usuario_id`

**Violación AUP:** Propuesta no responde **"¿Quién capturó la evidencia?"**

**Escenarios Críticos:**
1. **Auditoría:** Evidencia manipulada → No puedes rastrear responsable
2. **Incidente legal:** Visita demanda por foto → No puedes identificar guardia
3. **Conflicto laboral:** Guardia despedido → No puedes auditar sus capturas

**Principio AUP violado:**
> "No acción sin IDENTITY explícita. El sistema no infiere quién, lo declara."

**Recomendación:** `guardia_id` es **OBLIGATORIO**.

---

### 3.4 Falta de URL de Archivo

**Propuesta:**
- Solo `file_hash TEXT NOT NULL`

**Sistema Actual:**
- `archivo_url TEXT` (path S3/storage)
- `hash_sha256 TEXT` (verificación)

**Problema con propuesta:**
```
Hash almacenado: "a3f5c8d2..."
Usuario solicita evidencia → ¿Cómo la recuperas?
```

**Necesitas:**
```python
# Recuperar archivo
file_url = evidencia.archivo_url  # "s3://bucket/evidencias/abc-123.jpg"
file_content = storage.get(file_url)

# Verificar integridad
calculated_hash = sha256(file_content)
if calculated_hash != evidencia.hash_sha256:
    raise IntegrityError("Archivo corrupto")
```

**Recomendación:** `archivo_url` + `hash_sha256` (ambos necesarios).

---

### 3.5 Falta de Metadata Extensible

**Propuesta:**
- ❌ Solo campos fijos

**Sistema Actual:**
- ✅ `metadata_json JSONB`

**Ventaja de metadata flexible:**
```json
{
  "device": "iPad-Caseta-Norte",
  "app_version": "2.1.0",
  "gps": {"lat": 19.432608, "lon": -99.133209},
  "file_size_bytes": 245678,
  "mime_type": "image/jpeg",
  "upload_duration_ms": 1234,
  "network_type": "wifi",
  "thumbnail_url": "s3://bucket/thumbs/abc-123.jpg"
}
```

**Escenarios que necesitan metadata:**
1. **Debugging:** Upload falló → Revisar device/network
2. **Auditoría:** Foto sospechosa → Verificar GPS del dispositivo
3. **Performance:** Subida lenta → Analizar file_size vs network
4. **Feature toggle:** Agregar thumbnail sin migración

**Recomendación:** `metadata_json` es **ALTAMENTE RECOMENDADO**.

---

### 3.6 Constraint `NOT NULL` en `file_hash`

**Propuesta:**
- `file_hash TEXT NOT NULL`

**Riesgo:**
```python
# Flujo típico
1. Upload archivo a S3 → OK
2. Calcular hash → ❌ FALLA (timeout, error de red)
3. Intentar guardar registro → ❌ NOT NULL violation
4. Evidencia se pierde (archivo en S3 huérfano)
```

**Mejor approach:**
```python
# Permitir NULL temporal
1. Upload archivo → OK
2. Guardar registro con hash=NULL → OK
3. Background job calcula hash → Actualiza registro

# Validación en lógica
if evidencia.hash_sha256 is None:
    logger.warning(f"Evidencia {id} sin hash, recalculando...")
    calculate_hash_async(evidencia)
```

**Recomendación:** `hash_sha256 TEXT` (permitir NULL), validar en aplicación.

---

## 4. TABLA RECOMENDADA (Alineada con AUP)

```sql
CREATE TABLE IF NOT EXISTS evidencias (
    -- ═══════════════════════════════════════════════════
    -- PK Técnico (compatibilidad ORMs)
    -- ═══════════════════════════════════════════════════
    id SERIAL PRIMARY KEY,
    
    -- ═══════════════════════════════════════════════════
    -- PK de Negocio (UUID como String para consistencia)
    -- ═══════════════════════════════════════════════════
    evidencia_id VARCHAR(36) UNIQUE NOT NULL,
    
    -- ═══════════════════════════════════════════════════
    -- AUP_SCOPE: Relación con visita (CORE domain)
    -- ═══════════════════════════════════════════════════
    visita_id VARCHAR(36) NOT NULL REFERENCES visitas(visita_id) ON DELETE CASCADE,
    
    -- ═══════════════════════════════════════════════════
    -- Clasificación de Evidencia
    -- ═══════════════════════════════════════════════════
    categoria VARCHAR(20) NOT NULL,      -- 'entrada' | 'salida'
    sub_tipo VARCHAR(50) NOT NULL,       -- 'visitante' | 'ine_frente' | 'ine_reverso' | 'placas' | 'vehiculo' | 'documento'
    
    -- ═══════════════════════════════════════════════════
    -- Artefacto y Verificación
    -- ═══════════════════════════════════════════════════
    archivo_url TEXT NOT NULL,           -- S3/storage path: "s3://bucket/evidencias/abc-123.jpg"
    hash_sha256 TEXT,                    -- SHA-256 del archivo (calculado post-upload, puede ser NULL temporalmente)
    
    -- ═══════════════════════════════════════════════════
    -- AUP_IDENTITY: Quién capturó (Trazabilidad)
    -- ═══════════════════════════════════════════════════
    guardia_id VARCHAR(36) NOT NULL REFERENCES usuarios(usuario_id),
    
    -- ═══════════════════════════════════════════════════
    -- Metadata Extensible (Flexibilidad sin migración)
    -- ═══════════════════════════════════════════════════
    metadata_json JSONB,                 -- {device, gps, app_version, file_size, mime_type, thumbnail_url, etc.}
    
    -- ═══════════════════════════════════════════════════
    -- AUP_EVENT: Timestamps
    -- ═══════════════════════════════════════════════════
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- ═══════════════════════════════════════════════════
-- Índices para Performance
-- ═══════════════════════════════════════════════════
CREATE INDEX idx_evidencias_visita ON evidencias(visita_id);
CREATE INDEX idx_evidencias_categoria ON evidencias(categoria);
CREATE INDEX idx_evidencias_guardia ON evidencias(guardia_id);
CREATE INDEX idx_evidencias_created ON evidencias(created_at DESC);
CREATE INDEX idx_evidencias_hash ON evidencias(hash_sha256) WHERE hash_sha256 IS NOT NULL;

-- ═══════════════════════════════════════════════════
-- Constraint de Integridad
-- ═══════════════════════════════════════════════════
ALTER TABLE evidencias ADD CONSTRAINT chk_categoria 
    CHECK (categoria IN ('entrada', 'salida'));

ALTER TABLE evidencias ADD CONSTRAINT chk_sub_tipo
    CHECK (sub_tipo IN ('visitante', 'ine_frente', 'ine_reverso', 'placas', 'vehiculo', 'documento'));
```

---

## 5. COMPARATIVA DETALLADA

| Característica | Propuesta Original | Sistema Actual | Recomendación | Razón AUP |
|----------------|-------------------|----------------|---------------|-----------|
| **ID Type** | `UUID` nativo | `VARCHAR(36)` | `VARCHAR(36)` | Consistencia con todo el sistema |
| **PK Técnico** | Solo UUID | `id` (SERIAL) + `evidencia_id` | Dual PK | Compatibilidad ORMs |
| **Clasificación** | `tipo` (1 campo) | `categoria` + `sub_tipo` | 2 campos | Claridad semántica y queries |
| **Archivo** | ❌ Ausente | `archivo_url` | ✅ **CRÍTICO** | Sin URL no puedes recuperar archivo |
| **Hash** | `NOT NULL` | Nullable | Nullable | Tolerar fallo en hash, recalcular después |
| **Identidad** | ❌ Ausente | `guardia_id` | ✅ **OBLIGATORIO** | AUP_IDENTITY (quién capturó) |
| **Metadata** | ❌ Ausente | `metadata_json` | ✅ **RECOMENDADO** | Extensibilidad sin migración |
| **Timestamps** | `created_at` | `created_at` | ✅ Con timezone | AUP_EVENT (cuándo) |
| **Índices** | ❌ Ausentes | ❌ Faltan | ✅ **NECESARIOS** | Performance en queries |
| **Constraints** | ❌ Ausentes | ❌ Faltan | ✅ **OPCIONALES** | Validación en BD |

---

## 6. VALIDACIÓN POR PRINCIPIOS AUP

### ✅ AUP_IDENTITY (Quién)
```sql
-- ✅ Recomendación cumple
guardia_id VARCHAR(36) NOT NULL REFERENCES usuarios(usuario_id)

-- ❌ Propuesta viola
-- Sin guardia_id no puedes responder: "¿Quién capturó esta evidencia?"
```

**Axioma violado:**
> "No acción sin IDENTITY explícita. El sistema no infiere quién, lo declara."

---

### ✅ AUP_SCOPE (Dónde)
```sql
-- ✅ Ambas propuestas cumplen (implícitamente)
visita_id → condominio_id (tenant)

-- Validación en runtime:
# 1. Guardia intenta subir evidencia
# 2. Sistema valida: guardia.scope en visita.condominio
# 3. Si no tiene scope → DENIED
```

---

### ✅ AUP_EVENT (Cuándo/Qué)
```sql
-- ✅ Ambas propuestas cumplen
created_at TIMESTAMPTZ DEFAULT now()

-- ⚠️ Considerar registrar evento separado
INSERT INTO events_aup (
    accion = 'evidencia_subida',
    identity_id = guardia_id,
    tenant_id = (SELECT condominio_id FROM visitas WHERE visita_id = ...),
    resultado = 'exito',
    metadata = {'evidencia_id': ..., 'categoria': ..., 'file_size': ...}
)
```

---

### ⚠️ Integridad y Verificación
```sql
-- ✅ Recomendación permite recuperación
archivo_url + hash_sha256

-- Flujo de verificación:
1. Usuario descarga archivo desde archivo_url
2. Calcula hash del archivo descargado
3. Compara con hash_sha256 almacenado
4. Si difieren → archivo corrupto o manipulado
```

---

## 7. ESCENARIOS DE USO

### 7.1 Captura de Evidencia (Happy Path)

```python
# 1. Guardia toma foto en tablet
foto_binaria = camera.capture()

# 2. Upload a S3
file_url = storage.upload(
    file=foto_binaria,
    path=f"evidencias/{visita_id}/{uuid.uuid4()}.jpg"
)

# 3. Calcular hash
file_hash = hashlib.sha256(foto_binaria).hexdigest()

# 4. Guardar registro
evidencia = Evidencia(
    evidencia_id=str(uuid.uuid4()),
    visita_id=visita_id,
    categoria='entrada',
    sub_tipo='visitante',
    archivo_url=file_url,
    hash_sha256=file_hash,
    guardia_id=current_user.usuario_id,
    metadata_json={
        'device': 'iPad-Caseta-Norte',
        'gps': {'lat': 19.432, 'lon': -99.133},
        'file_size_bytes': len(foto_binaria),
        'mime_type': 'image/jpeg'
    }
)
db.add(evidencia)
db.commit()

# 5. Registrar evento AUP
registrar_evento(
    accion='evidencia_subida',
    identity_id=guardia_id,
    resultado='exito'
)
```

---

### 7.2 Auditoría Forense

```sql
-- Caso: Visita demanda por foto no autorizada

-- 1. Identificar evidencias de la visita
SELECT 
    e.evidencia_id,
    e.categoria,
    e.sub_tipo,
    e.created_at,
    u.nombre AS guardia_nombre,
    u.email AS guardia_email,
    e.metadata_json->>'device' AS dispositivo,
    e.metadata_json->>'gps' AS ubicacion
FROM evidencias e
JOIN usuarios u ON e.guardia_id = u.usuario_id
WHERE e.visita_id = 'visita-demandada-123'
ORDER BY e.created_at;

-- 2. Verificar integridad de archivos
SELECT 
    evidencia_id,
    archivo_url,
    hash_sha256,
    CASE 
        WHEN hash_sha256 IS NULL THEN 'SIN_HASH'
        ELSE 'VERIFICABLE'
    END AS estado_integridad
FROM evidencias
WHERE visita_id = 'visita-demandada-123';

-- 3. Timeline de acciones del guardia
SELECT 
    timestamp,
    accion,
    resultado,
    metadata_json
FROM events_aup
WHERE identity_id = 'guardia-sospechoso-456'
  AND DATE(timestamp) = '2025-12-15'
ORDER BY timestamp;
```

---

### 7.3 Incidente: Archivo Corrupto

```python
# Detección automática (cronjob diario)
def verificar_integridad():
    evidencias = db.query(Evidencia).filter(
        Evidencia.hash_sha256 != None,
        Evidencia.created_at > datetime.now() - timedelta(days=7)
    )
    
    for ev in evidencias:
        # Descargar archivo
        file_content = storage.get(ev.archivo_url)
        
        # Calcular hash actual
        current_hash = hashlib.sha256(file_content).hexdigest()
        
        # Comparar
        if current_hash != ev.hash_sha256:
            logger.critical(
                f"INTEGRIDAD VIOLADA: Evidencia {ev.evidencia_id}"
                f"Hash esperado: {ev.hash_sha256}"
                f"Hash actual: {current_hash}"
            )
            
            # Registrar evento crítico
            registrar_evento(
                accion='integridad_violada',
                identity_id='sistema',
                resultado='alerta_critica',
                metadata={'evidencia_id': ev.evidencia_id}
            )
```

---

## 8. RECOMENDACIÓN FINAL

### ❌ **NO APROBAR PROPUESTA ORIGINAL** por:

1. **Falta `guardia_id`** → Viola AUP_IDENTITY (no sabemos quién capturó)
2. **Falta `archivo_url`** → Imposible recuperar archivo (solo tienes hash)
3. **Tipo `UUID` nativo** → Inconsistente con sistema (usa String)
4. **`file_hash NOT NULL`** → Demasiado rígido (perderías registro si falla hash)
5. **Sin metadata extensible** → Inflexible para debugging/auditoría
6. **Sin índices** → Performance degradada en queries

---

### ✅ **APROBAR ESTRUCTURA ACTUAL** con ajustes:

```sql
-- Migración opcional para mejorar estructura actual
ALTER TABLE evidencias ADD CONSTRAINT chk_categoria 
    CHECK (categoria IN ('entrada', 'salida'));

ALTER TABLE evidencias ADD CONSTRAINT chk_sub_tipo
    CHECK (sub_tipo IN ('visitante', 'ine_frente', 'ine_reverso', 'placas', 'vehiculo', 'documento'));

CREATE INDEX IF NOT EXISTS idx_evidencias_visita ON evidencias(visita_id);
CREATE INDEX IF NOT EXISTS idx_evidencias_categoria ON evidencias(categoria);
CREATE INDEX IF NOT EXISTS idx_evidencias_guardia ON evidencias(guardia_id);
CREATE INDEX IF NOT EXISTS idx_evidencias_created ON evidencias(created_at DESC);
```

---

## 9. DECISIONES ARQUITECTÓNICAS

| Decisión | Razón | Impacto |
|----------|-------|---------|
| Mantener `String` para UUIDs | Consistencia con 7 tablas existentes | Evita migración masiva |
| `guardia_id` obligatorio | AUP_IDENTITY (trazabilidad) | Auditoría forense posible |
| `archivo_url` + `hash_sha256` | Recuperación + verificación | Integridad verificable |
| `metadata_json` JSONB | Extensibilidad sin migración | Debugging mejorado |
| `hash_sha256` nullable | Tolerar fallo temporal | Upload no bloquea registro |
| Índices en queries comunes | Performance | Queries 10-100x más rápidas |
| Constraints en categorías | Validación en BD | Previene datos inválidos |

---

## 10. PRÓXIMOS PASOS

### Opción A: Mantener Estructura Actual (Recomendado)
```bash
# Solo agregar índices y constraints
psql $DATABASE_URL_CORE < migrations/add_evidencias_indexes.sql
```

### Opción B: Migrar a UUID Nativo (No Recomendado)
```bash
# Requiere migrar 7 tablas + código Python
# Estimado: 2-3 días de trabajo + testing
# Beneficio: Mínimo (solo tipos más estrictos en BD)
```

### Opción C: Ajustar Propuesta Original
```sql
-- Mínimo viable para aprobar propuesta
CREATE TABLE evidencias (
    evidencia_id VARCHAR(36) PRIMARY KEY,  -- Cambiar UUID → VARCHAR
    visita_id VARCHAR(36) NOT NULL REFERENCES visitas(visita_id),
    categoria VARCHAR(20) NOT NULL,
    sub_tipo VARCHAR(50) NOT NULL,        -- Agregar
    archivo_url TEXT NOT NULL,             -- Agregar
    file_hash TEXT,                        -- Cambiar NOT NULL → nullable
    guardia_id VARCHAR(36) NOT NULL REFERENCES usuarios(usuario_id),  -- Agregar
    metadata_json JSONB,                   -- Agregar
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
```

---

## 11. CONCLUSIÓN

**Veredicto:** ❌ **NO APROBAR PROPUESTA ORIGINAL**

**Estructura actual** es superior porque:
- ✅ Cumple todos los principios AUP
- ✅ Trazabilidad completa (guardia_id)
- ✅ Recuperación de archivos (archivo_url)
- ✅ Verificación de integridad (hash_sha256)
- ✅ Extensibilidad (metadata_json)
- ✅ Consistencia de tipos (String UUID)

**Acción recomendada:** Mantener estructura actual, solo agregar índices y constraints opcionales.

---

**Firmado:**  
Claude (Arquitectura AUP)  
31 de diciembre de 2025
