# AUP: DECLARACIÓN DE SESIONES POR ROUTER

**Fecha:** 2025-12-29  
**Responsabilidad:** Declarar explícitamente qué router usa qué sesión de BD.

---

## AXIOMA FUNDAMENTAL

> **El router NO decide dónde persiste.**  
> **El dominio AUP declara la memoria.**

---

## TABLA DE SESIONES POR ROUTER

| Router               | Operación          | Lee         | Escribe     | Notas                                    |
|---------------------|-------------------|-------------|-------------|------------------------------------------|
| `/auth/login`       | Autenticación     | **CORE**    | **EVENT**   | Lee identidad, registra verdad histórica |
| `/qr/generate`      | Generar QR        | **CORE**    | **EVENT**   | Lee visita/usuario, registra acción      |
| `/qr/validate`      | Validar QR        | **CORE**    | **EVENT**   | Lee QR, registra entrada/salida          |
| `/visitas/*`        | CRUD Visitas      | **CORE**    | **CORE**    | Entidad de negocio vive en CORE          |
| `/evidencias/*`     | CRUD Evidencias   | **CORE**    | **CORE**    | Artefactos de operación viven en CORE    |
| `/condominios/*`    | Gobierno Tenants  | **CORE**    | **GOV**     | Lee tenant, escribe políticas            |
| `/preregistro/*`    | Pre-registro      | **CORE**    | **CORE**    | Entidad de negocio                       |
| `registrar_evento()`| Registro central  | —           | **EVENT**   | **Siempre** escribe en EVENT             |

---

## REGLAS DE USO

### ✅ Patrón correcto

```python
from backend.db.core import get_core_db, Usuario
from backend.db.event import get_event_db
from backend.core.event.registry import registrar_evento

@router.post("/accion")
def accion(
    db_core: Session = Depends(get_core_db),
    db_event: Session = Depends(get_event_db)
):
    # Lee identidad desde CORE
    usuario = db_core.query(Usuario).filter(...).first()
    
    # Registra evento en EVENT
    registrar_evento(
        db=db_event,
        identity=usuario,
        ...
    )
```

### ❌ Patrón incorrecto

```python
# ❌ NO usar sesión genérica "db"
from backend.db.connection import SessionLocal

@router.post("/accion")
def accion(db: Session = Depends(get_db)):
    # ¿Qué base es esta? Ontológicamente indefinido
    pass
```

---

## DECLARACIÓN DE DOMINIO

### AUP_CORE (Identidad y Alcance)
- **Responsabilidad:** Declarar existencia de identidades y sus alcances.
- **Modelos:**
  - `Usuario` (AUP_IDENTITY)
  - `MSP`, `Condominio` (AUP_TENANT)
  - `UserTenantScope` (AUP_SCOPE)
  - `Visita`, `Evidencia`, `Caseta` (negocio)
- **Variable entorno:** `DATABASE_CORE_URL`

### AUP_EVENT (Verdad Histórica)
- **Responsabilidad:** Registrar hechos inmutables.
- **Modelos:**
  - `Event` (único modelo)
- **Axiomas:**
  - Append-only (solo INSERT)
  - Si no hay evento, no ocurrió
  - Hash de inmutabilidad
- **Variable entorno:** `DATABASE_EVENT_URL`

### AUP_GOV (Poder Explícito)
- **Responsabilidad:** Declarar quién tiene poder, sobre qué, bajo qué límites.
- **Modelos:**
  - `Authority` (AUP_AUTHORITY)
  - `Policy` (AUP_POLICY)
  - `Delegation` (AUP_DELEGATION)
- **Axiomas:**
  - Gobierno precede operación
  - Sin política → denegado
  - Revocación inmediata
- **Variable entorno:** `DATABASE_GOV_URL`

---

## PROHIBICIÓN DE IMPORTS CRUZADOS

### ❌ NUNCA hacer esto:

```python
# ❌ NO importar modelos de otro dominio
from backend.db.core.models import Usuario
from backend.db.event.models import Event  # En el mismo archivo

# ❌ NO relacionar modelos entre dominios
class Usuario(Base_CORE):
    eventos = relationship("Event")  # Event vive en otro dominio
```

### ✅ Relaciones solo por IDs:

```python
# ✅ Event referencia a Usuario solo por UUID (string)
class Event(Base_EVENT):
    identity_id = Column(String, nullable=False)  # UUID, no ForeignKey
```

---

## ESTADO ACTUAL

| Archivo                          | Estado      | Notas                                      |
|----------------------------------|-------------|--------------------------------------------|
| `backend/db/models.py`           | DEPRECATED  | Renombrado a `models_DEPRECATED.py`        |
| `backend/db/core/models.py`      | ✅ ACTIVO   | Modelos de identidad/alcance/negocio       |
| `backend/db/event/models.py`     | ✅ ACTIVO   | Modelo de eventos                          |
| `backend/db/gov/models.py`       | ✅ ACTIVO   | Modelos de gobierno                        |
| `backend/routers/auth_router.py` | ✅ CORRECTO | Usa `get_core_db()` + `get_event_db()`     |
| `backend/main.py`                | ✅ CORRECTO | Crea tablas en 3 bases separadas           |

---

## PRÓXIMOS PASOS

1. ✅ Actualizar `/qr/*` routers para usar sesiones correctas
2. ✅ Actualizar `/condominios/*` para separar CORE y GOV
3. ✅ Verificar que `registrar_evento()` siempre recibe `db_event`
4. 🔜 Crear bases en Neon
5. 🔜 Ejecutar migraciones por dominio
6. 🔜 Smoke test AUP

---

**Declaración AUP:**  
Esta separación NO es refactoring cosmético.  
Es una declaración ontológica de que cada dominio tiene memoria independiente,  
y que las operaciones respetan la naturaleza de lo que persisten.
