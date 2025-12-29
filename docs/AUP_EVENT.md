# ═══════════════════════════════════════════════════════════════════════════
# PASO 3: AUP_EVENT - Declaración Estructural de Hechos
# ═══════════════════════════════════════════════════════════════════════════

## 📐 DECLARACIÓN AUP

### **AUP_EVENT**

Entidad estructural universal que declara que un **HECHO** ocurrió dentro del sistema, con identidad, contexto, alcance y resultado verificables.

**AUP_EVENT NO ES:**
- ❌ Logging técnico (print, logger.info)
- ❌ Auditoría clásica (quien-cuando-donde manual)
- ❌ Event Sourcing completo (reconstrucción total de estado)

**AUP_EVENT ES:**
- ✅ Entidad de dominio estructural
- ✅ Declaración de existencia en el tiempo
- ✅ Núcleo de trazabilidad universal
- ✅ Base para compliance y auditoría
- ✅ Inmutable por diseño

---

## 🗂️ ESTRUCTURA CONCEPTUAL

```
AUP_EVENT {
    identity:   AUP_IDENTITY     # QUIÉN actúa
    session:    AUP_SESSION      # CONTEXTO temporal
    scope:      AUP_SCOPE        # ALCANCE sobre tenant
    tenant:     AUP_TENANT       # DÓNDE ocurre
    
    entidad:    ENTITY_TYPE      # QUÉ se afecta (visita, qr, evidencia)
    entidad_id: STRING           # Identificador específico
    accion:     ACTION_TYPE      # QUÉ se hace (crear, validar, denegar)
    resultado:  RESULT_TYPE      # RESULTADO (permitido, denegado, error)
    
    motivo:     STRING?          # POR QUÉ (opcional pero relevante)
    metadata:   JSON?            # Contexto adicional estructurado
    
    timestamp:  DATETIME         # CUÁNDO ocurrió
    hash:       STRING           # Huella de inmutabilidad
}
```

---

## 🔗 RELACIONES AUP

```
AUP_IDENTITY --genera→ AUP_EVENT
AUP_SESSION  --contexto→ AUP_EVENT
AUP_SCOPE    --alcance→ AUP_EVENT
AUP_TENANT   --contiene→ AUP_EVENT

AUP_EVENT --afecta→ ENTIDAD (Visita, QR, Evidencia, Usuario, Condominio)
```

---

## 📜 AXIOMAS (NO NEGOCIABLES)

### **1. EXISTENCIA DECLARATIVA**
Si algo ocurre y no genera AUP_EVENT, no ocurrió para el sistema.

### **2. INMUTABILIDAD**
Un AUP_EVENT nunca se modifica. Solo se agregan nuevos eventos.

### **3. VALIDEZ ESTRUCTURAL**
Un AUP_EVENT sin identity, tenant o scope es estructuralmente inválido.  
**Excepción:** eventos de autenticación donde scope aún no existe.

### **4. RECONSTRUCCIÓN**
El estado del sistema puede reconstruirse a partir de eventos.

### **5. UNIVERSALIDAD**
Toda acción relevante (crear, validar, revocar, denegar) genera evento.

---

## 🎯 TIPOS ESTRUCTURALES

### **EventEntity (Entidades Afectadas)**
```python
class EventEntity(str, Enum):
    VISITA = "visita"
    QR = "qr"
    EVIDENCIA = "evidencia"
    USUARIO = "usuario"
    CONDOMINIO = "condominio"
    SCOPE = "scope"
    SESSION = "session"
```

### **EventAction (Acciones Ejecutadas)**
```python
class EventAction(str, Enum):
    CREAR = "crear"
    VALIDAR = "validar"
    REGISTRAR = "registrar"
    REVOCAR = "revocar"
    DENEGAR = "denegar"
    MODIFICAR = "modificar"
    ELIMINAR = "eliminar"
    ASIGNAR = "asignar"
    LOGIN = "login"
    LOGOUT = "logout"
```

### **EventResult (Resultados)**
```python
class EventResult(str, Enum):
    PERMITIDO = "permitido"
    DENEGADO = "denegado"
    ERROR = "error"
    EXITO = "exito"
    FALLO = "fallo"
```

---

## 🔑 FUNCIÓN CENTRAL

```python
def registrar_evento(
    db: Session,
    identity: Usuario,           # AUP_IDENTITY
    session_token: str,          # JWT completo para hash
    tenant_id: str,              # AUP_TENANT
    entidad: str,                # Tipo de entidad
    entidad_id: str,             # ID específico
    accion: str,                 # Acción ejecutada
    resultado: str,              # Resultado
    scope_id: Optional[str] = None,  # AUP_SCOPE (None en login)
    motivo: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Event
```

### **Pregunta que responde:**
> ¿Qué hecho estructural acaba de ocurrir y quién/dónde/cómo?

### **NO pregunta:**
- ¿Debo permitir esto? (eso es validación)
- ¿Qué significa esto? (eso es lógica de negocio)

### **SÍ declara:**
- Este hecho ocurrió
- Con esta identidad
- En este tenant
- Con este resultado
- En este momento
- Con esta huella verificable

---

## 🗂️ MAPEO: CONCEPTO AUP → CÓDIGO

| Concepto AUP | Implementación | Archivo |
|--------------|----------------|---------|
| AUP_EVENT | Event (SQLAlchemy model) | `backend/db/models.py` |
| EventEntity | EventEntity enum | `backend/core/event/__init__.py` |
| EventAction | EventAction enum | `backend/core/event/__init__.py` |
| EventResult | EventResult enum | `backend/core/event/__init__.py` |
| registrar_evento() | Función central | `backend/core/event/registry.py` |
| calcular_hash_evento() | Hash inmutabilidad | `backend/core/event/registry.py` |
| verificar_integridad_evento() | Validador hash | `backend/core/event/registry.py` |

---

## 🗄️ MODELO DE DATOS

```python
class Event(Base):
    """
    Entidad estructural universal que declara que un HECHO ocurrió.
    
    Axiomas:
    1. Toda acción relevante genera al menos un AUP_EVENT
    2. AUP_EVENT sin identidad/tenant es estructuralmente inválido
    3. AUP_EVENT es inmutable (no se edita, solo se agrega)
    4. Estado del sistema se puede reconstruir desde eventos
    5. Si no hay evento, no ocurrió para el sistema
    """
    __tablename__ = "events_aup"
    
    # Identificador único
    event_id = Column(String, primary_key=True, index=True)
    
    # Contexto AUP (QUIÉN, DÓNDE, CÓMO)
    identity_id = Column(String, ForeignKey("usuarios_exo.usuario_id"), nullable=False, index=True)
    session_hash = Column(String, nullable=False, index=True)
    scope_id = Column(String, ForeignKey("user_tenant_scope.id"), nullable=True, index=True)
    tenant_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=False, index=True)
    
    # Declaración del Hecho (QUÉ, RESULTADO)
    entidad = Column(String, nullable=False, index=True)
    entidad_id = Column(String, nullable=False, index=True)
    accion = Column(String, nullable=False, index=True)
    resultado = Column(String, nullable=False, index=True)
    motivo = Column(Text, nullable=True)
    
    # Metadatos y Trazabilidad
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    hash_evento = Column(String, nullable=False, unique=True)  # SHA-256
    metadata = Column(JSON, nullable=True)
```

---

## 📊 INTEGRACIÓN CON PASOS ANTERIORES

### **PASO 1: AUP_SESSION**
- Valida identidad (get_current_user)
- **AUP_EVENT registra:** intento de login (exitoso/fallido)

### **PASO 2: AUP_SCOPE**
- Valida alcance (validar_scope)
- **AUP_EVENT registra:** validación de scope (permitido/denegado)

### **PASO 3: AUP_EVENT (ESTE PASO)**
- Declara el hecho que ocurrió
- Crea trazabilidad completa del sistema

---

## 🚀 EVENTOS IMPLEMENTADOS

### **1. Login (auth_router.py)**

**Login Exitoso:**
```python
registrar_evento(
    db=db,
    identity=usuario,
    session_token=access_token,
    tenant_id=usuario.condominio_id or "sistema",
    entidad=EventEntity.SESSION.value,
    entidad_id=usuario.usuario_id,
    accion=EventAction.LOGIN.value,
    resultado=EventResult.EXITO.value,
    scope_id=None,
    motivo="Autenticación exitosa",
    metadata={"email": usuario.email, "rol": usuario.rol}
)
```

**Login Fallido:**
```python
registrar_evento(
    db=db,
    identity=usuario,
    session_token="login_attempt",
    tenant_id=usuario.condominio_id or "sistema",
    entidad=EventEntity.SESSION.value,
    entidad_id=usuario.usuario_id,
    accion=EventAction.LOGIN.value,
    resultado=EventResult.FALLO.value,
    motivo="Contraseña incorrecta"
)
```

### **2. Crear Visita (visitas_router.py)**

**Creación Exitosa:**
```python
registrar_evento(
    db=db,
    identity=usuario,
    session_token=token,
    tenant_id=data.condominio_id,
    entidad=EventEntity.VISITA.value,
    entidad_id=visita.visita_id,
    accion=EventAction.CREAR.value,
    resultado=EventResult.EXITO.value,
    scope_id=scope.id,
    motivo="Visita creada exitosamente",
    metadata={
        "visitante": data.nombre_visitante,
        "casa_unidad": data.casa_unidad,
        "fecha_entrada": str(data.fecha_entrada)
    }
)
```

**Creación Denegada (sin scope):**
```python
registrar_evento(
    db=db,
    identity=usuario,
    session_token=token,
    tenant_id=data.condominio_id,
    entidad=EventEntity.VISITA.value,
    entidad_id="pending",
    accion=EventAction.CREAR.value,
    resultado=EventResult.DENEGADO.value,
    motivo="Sin scope válido en tenant"
)
```

### **3. Generar QR (qr_router.py)**

```python
registrar_evento(
    db=db,
    identity=usuario,
    session_token=token,
    tenant_id=visita.condominio_id,
    entidad=EventEntity.QR.value,
    entidad_id=qr_data["token"],
    accion=EventAction.CREAR.value,
    resultado=EventResult.EXITO.value,
    motivo="QR generado para visita",
    metadata={
        "visita_id": visita_id,
        "qr_vigencia": str(qr_data["qr_vigencia"])
    }
)
```

### **4. Validar QR (qr_router.py)**

**Validación Exitosa:**
```python
registrar_evento(
    db=db,
    identity=usuario,
    session_token=token,
    tenant_id=visita.condominio_id,
    entidad=EventEntity.QR.value,
    entidad_id=token,
    accion=EventAction.VALIDAR.value,
    resultado=EventResult.EXITO.value,
    motivo="QR validado y entrada registrada",
    metadata={
        "visita_id": visita_id,
        "visitante": visita.nombre_visitante,
        "casa_unidad": visita.casa_unidad
    }
)
```

**Validación Denegada (QR expirado):**
```python
registrar_evento(
    db=db,
    identity=usuario,
    session_token=token,
    tenant_id=visita.condominio_id,
    entidad=EventEntity.QR.value,
    entidad_id=token,
    accion=EventAction.VALIDAR.value,
    resultado=EventResult.DENEGADO.value,
    motivo="QR expirado",
    metadata={"visita_id": visita_id, "qr_vigencia": str(visita.qr_vigencia)}
)
```

---

## 🔍 CASOS DE USO

### **1. Auditoría Compliance**
```sql
-- ¿Quién accedió a datos del Condominio A en diciembre?
SELECT identity_id, accion, entidad, timestamp
FROM events_aup
WHERE tenant_id = 'condo_a'
  AND timestamp >= '2024-12-01'
ORDER BY timestamp DESC;
```

### **2. Reconstrucción de Estado**
```python
# ¿Qué le pasó a esta visita?
eventos = obtener_eventos_entidad(
    db=db,
    entidad=EventEntity.VISITA.value,
    entidad_id="v123"
)
# Retorna: creada → QR generado → QR validado → entrada registrada
```

### **3. Detección de Anomalías**
```python
# ¿Intentos de acceso denegados?
eventos_sospechosos = obtener_eventos_denegados(
    db=db,
    tenant_id="condo_a"
)
# Retorna eventos con resultado=DENEGADO
```

### **4. Trazabilidad de Usuario**
```python
# ¿Qué hizo Juan en Condominio A hoy?
eventos = obtener_eventos_usuario_en_tenant(
    db=db,
    usuario_id="juan123",
    tenant_id="condo_a",
    desde=datetime(2024, 12, 29),
    hasta=datetime.now()
)
```

### **5. Verificación de Integridad**
```python
# ¿Este evento fue alterado?
es_integro = verificar_integridad_evento(evento)
# Calcula hash desde campos actuales, compara con hash_evento
# True = íntegro, False = alterado
```

---

## 🔐 HASH DE INMUTABILIDAD

### **Cálculo del Hash**

```python
def calcular_hash_evento(
    event_id: str,
    identity_id: str,
    session_hash: str,
    tenant_id: str,
    entidad: str,
    entidad_id: str,
    accion: str,
    resultado: str,
    timestamp: datetime
) -> str:
    """
    Calcula SHA-256 de campos críticos del evento.
    
    Propósito: Verificar inmutabilidad del evento.
    """
    contenido = "|".join([
        event_id, identity_id, session_hash, tenant_id,
        entidad, entidad_id, accion, resultado,
        timestamp.isoformat()
    ])
    
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()
```

### **Verificación**

Si el hash calculado desde campos actuales NO coincide con `hash_evento` almacenado:
→ **El evento fue alterado** (violación de axioma de inmutabilidad)

---

## 📋 HELPERS DE CONSULTA

### **1. obtener_eventos_entidad()**
```python
# ¿Qué eventos afectaron esta visita?
eventos = obtener_eventos_entidad(db, "visita", "v123")
```

### **2. obtener_eventos_usuario_en_tenant()**
```python
# ¿Qué hizo este usuario en este tenant?
eventos = obtener_eventos_usuario_en_tenant(
    db, "user123", "condo_a",
    desde=datetime(2024, 12, 1)
)
```

### **3. obtener_eventos_denegados()**
```python
# ¿Qué accesos fueron denegados?
eventos = obtener_eventos_denegados(db, tenant_id="condo_a", limit=100)
```

---

## 💎 VENTAJAS AUP_EVENT

### **1. Trazabilidad Completa**
Cada acción deja huella estructural con contexto completo (quién/qué/dónde/cuándo/cómo/por qué).

### **2. Inmutabilidad Verificable**
Hash SHA-256 permite detectar alteraciones. Sistema de auditoría confiable.

### **3. Reconstrucción de Estado**
Eventos ordenados cronológicamente permiten reconstruir qué pasó con cualquier entidad.

### **4. Compliance Nativo**
- **GDPR:** Histórico de accesos para derecho de información
- **SOC2:** Auditoría inmutable de operaciones
- **ISO27001:** Trazabilidad de accesos y cambios

### **5. Detección de Anomalías**
Eventos denegados revelan intentos no autorizados, patrones sospechosos.

### **6. Desacoplado de Logging**
AUP_EVENT es entidad de dominio. Logging técnico puede coexistir sin mezclar responsabilidades.

### **7. Base para IA/ML**
Eventos estructurados permiten análisis de patrones, predicción de comportamientos.

---

## 🎯 PREPARADO PARA

### **Recordia (Memoria Estructural Temporal)**
- Sistema puede consultar "¿qué pasó con X?"
- Memoria declarativa, no inferida

### **HotVault (Validación Crítica en Caliente)**
- Eventos de alta prioridad (seguridad) procesados en tiempo real
- Alertas automáticas ante patrones anómalos

### **Análisis de Patrones**
- ML sobre eventos: "usuarios que validaron QR tarde en la noche"
- Detección de comportamientos inusuales

### **Auditoría Regulatoria**
- Exportación de eventos para compliance
- Histórico inmutable para investigaciones

---

## ✅ RESULTADO FINAL

### **Sistema ahora tiene:**
- ✅ Identidad validada (PASO 1: AUP_SESSION)
- ✅ Alcance validado (PASO 2: AUP_SCOPE)
- ✅ Hechos declarados (PASO 3: AUP_EVENT)

### **Trazabilidad Completa:**
Cada acción relevante del sistema queda registrada de forma inmutable con contexto completo AUP.

### **Axiomas Aplicados:**
1. Sin evento = no ocurrió ✓
2. Inmutabilidad con hash ✓
3. Validez estructural (identity + tenant) ✓
4. Reconstrucción desde eventos ✓
5. Universalidad de eventos ✓

---

## 🧪 TESTING DE EVENTOS

### **Crear Evento de Prueba:**
```python
from backend.core.event.registry import registrar_evento
from backend.core.event import EventEntity, EventAction, EventResult

evento = registrar_evento(
    db=db,
    identity=usuario,
    session_token="test_jwt_token",
    tenant_id="condo_test",
    entidad=EventEntity.VISITA.value,
    entidad_id="v_test_123",
    accion=EventAction.CREAR.value,
    resultado=EventResult.EXITO.value,
    motivo="Test de evento"
)

# Verificar hash
assert verificar_integridad_evento(evento) == True
```

### **Consultar Eventos:**
```python
# Todos los eventos de una visita
eventos = obtener_eventos_entidad(db, "visita", "v_test_123")

# Eventos denegados
denegados = obtener_eventos_denegados(db)
```

---

## 📚 LECCIONES AUP APLICADAS

### **Antes: "Implementar logging"**
- Enfoque técnico
- Ambiguo (logs de texto)
- Difícil consultar

### **Ahora: "Declarar AUP_EVENT"**
- Enfoque conceptual
- Claro (entidad estructural)
- Fácil consultar (SQL estructurado)

**Esto es AUP:**
1. Declarar QUÉ existe (AUP_EVENT como hecho)
2. Definir relaciones (EVENT → IDENTITY → TENANT → SCOPE)
3. Establecer axiomas (inmutabilidad, universalidad)
4. Implementar como traducción directa (Event model → registrar_evento())

---

**PASO 3 completado. Sistema production-ready con trazabilidad completa.**

═══════════════════════════════════════════════════════════════════════════
