# 🚀 IMPLEMENTACIÓN: Modo Guardia - INICIO

**Status:** 🟢 COMENZANDO  
**Prioridad:** CRÍTICA (Semana 1)  
**Dev:** 1 senior engineer  
**Tiempo:** 40 horas

---

## 🔐 ACLARACIÓN: Autenticación del Guardia

**NO es JWT almacenado:**
```
Antes (Incorrecto en mi doc):
  ❌ Guardia obtiene token JWT
  ❌ Guardia guarda token en BD
  ❌ Guardia lo usa luego

Correcto (Como funciona hoy):
  ✅ Guardia entra con usuario + password
  ✅ Sistema genera JWT en memoria (no se guarda)
  ✅ JWT se usa en headers de requests (Bearer token)
  ✅ JWT expira en 8 horas
```

**Flujo de Login Guardia:**
```
1. Guardia abre app
2. Guardia entra: usuario=carlos, password=secret123
3. Sistema busca Usuario.email == carlos
4. Sistema valida password_hash
5. Sistema GENERA JWT con identity_id + rol=GUARDIA
6. JWT retorna al cliente (en memoria)
7. Guardia usa JWT en cada request: Authorization: Bearer <token>
8. JWT expira automáticamente (8 horas)
```

**NO hay tabla de tokens/sesiones guardadas.**

---

## 📋 ENDPOINTS A IMPLEMENTAR

### 1️⃣ POST /visitas/rapida (PRIMERO - HOY)

**Endpoint:** Crear visita in-situ sin QR previo

**Autenticación:** AUP_SESSION (JWT válido + rol GUARDIA)

**Request:**
```json
{
  "condominio_id": "cond_123",
  "nombre_visitante": "Juan Pérez Rodríguez",
  "telefono": "5551234567",
  "casa_unidad": "4B",
  "residente_anfitrion": "Carlos López",
  "tipo_visitante": "cliente",
  "motivo": "Reunión de negocios",
  "placa_vehiculo": "ABC1234"
}
```

**Response (201):**
```json
{
  "visita_id": "vis_abc123",
  "nombre_visitante": "Juan Pérez Rodríguez",
  "estado": "creada_sin_qr",
  "casa_unidad": "4B",
  "condominio_id": "cond_123",
  "fecha_creacion": "2026-01-31T14:30:00Z",
  "qr_token": null,
  "mensaje": "Visita creada. Capturar evidencias."
}
```

**Validaciones:**
- ✅ AUP_SESSION: Usuario autenticado (JWT)
- ✅ Rol: GUARDIA
- ✅ AUP_SCOPE: Guardia en condominio_id
- ✅ Residente existe
- ✅ AUP_EVENT: Registrar creación

---

## 🔧 IMPLEMENTACIÓN (Paso a Paso)

### Paso 1: Schema Nuevo

```python
# backend/schemas/visita.py - AGREGAR AL FINAL

class VisitaRapidaCreate(BaseModel):
    """Schema para crear visita IN-SITU sin QR previo (Guardias)"""
    condominio_id: str
    nombre_visitante: str
    telefono: str
    casa_unidad: str
    residente_anfitrion: str
    tipo_visitante: str  # cliente|entrega|consulta|familia
    motivo: str
    placa_vehiculo: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "condominio_id": "cond_123",
                "nombre_visitante": "Juan Pérez",
                "telefono": "5551234567",
                "casa_unidad": "4B",
                "residente_anfitrion": "Carlos López",
                "tipo_visitante": "cliente",
                "motivo": "Reunión de negocios",
                "placa_vehiculo": "ABC1234"
            }
        }
```

### Paso 2: Endpoint en visitas_router.py

```python
# backend/routers/visitas_router.py - AGREGAR DESPUÉS DE crear_visita()

@router.post("/rapida", response_model=VisitaResponse, status_code=201)
def crear_visita_rapida(
    data: VisitaRapidaCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION
):
    """
    CREAR VISITA IN-SITU SIN QR PREVIO
    
    Usado por Guardias cuando visitante llega SIN registro previo.
    
    Flujo AUP:
      1. AUP_SESSION: get_current_user() valida JWT
      2. AUP_SCOPE: Validar guardia en condominio
      3. AUP_EVENT: Registrar creación
    
    Resultado:
      - Visita creada con estado "creada_sin_qr"
      - Sin QR generado aún (generará después al registrar entrada)
      - Listo para capturar evidencias
    """
    
    logger = logging.getLogger("axs.visitas")
    
    # ─────────────────────────────────────────────────────────────────
    # VALIDACIÓN 1: AUP_SESSION
    # ─────────────────────────────────────────────────────────────────
    # Ya validado por get_current_user() decorator
    
    # ─────────────────────────────────────────────────────────────────
    # VALIDACIÓN 2: Rol GUARDIA
    # ─────────────────────────────────────────────────────────────────
    if usuario.rol != "GUARDIA":
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=token,
            tenant_id=data.condominio_id,
            entidad=EventEntity.VISITA.value,
            entidad_id="pending",
            accion=EventAction.CREAR.value,
            resultado=EventResult.DENEGADO.value,
            motivo=f"Rol no autorizado para crear visita rápida. Rol: {usuario.rol}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Solo GUARDIAS pueden crear visitas rápidas. Tu rol: {usuario.rol}"
        )
    
    # ─────────────────────────────────────────────────────────────────
    # VALIDACIÓN 3: AUP_SCOPE - Guardia en condominio
    # ─────────────────────────────────────────────────────────────────
    try:
        scope = obtener_scope_usuario_en_tenant(
            db, usuario.usuario_id, data.condominio_id
        )
        if not scope:
            raise ValueError("Sin scope en condominio")
    except Exception as e:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=token,
            tenant_id=data.condominio_id,
            entidad=EventEntity.VISITA.value,
            entidad_id="pending",
            accion=EventAction.CREAR.value,
            resultado=EventResult.DENEGADO.value,
            motivo=f"Sin scope válido en condominio: {str(e)}"
        )
        raise HTTPException(403, f"No tienes acceso a este condominio")
    
    # ─────────────────────────────────────────────────────────────────
    # VALIDACIÓN 4: Residente anfitrión existe
    # ─────────────────────────────────────────────────────────────────
    residente = db.query(Usuario).filter(
        Usuario.nombre.ilike(f"%{data.residente_anfitrion}%"),
        Usuario.condominio_id == data.condominio_id,
        Usuario.rol.in_(["RESIDENTE", "ADMIN_CONDOMINIO"])
    ).first()
    
    if not residente:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=token,
            tenant_id=data.condominio_id,
            entidad=EventEntity.VISITA.value,
            entidad_id="pending",
            accion=EventAction.CREAR.value,
            resultado=EventResult.FALLO.value,
            motivo=f"Residente anfitrión no encontrado: {data.residente_anfitrion}"
        )
        raise HTTPException(404, f"Residente no encontrado: {data.residente_anfitrion}")
    
    # ─────────────────────────────────────────────────────────────────
    # CREAR VISITA
    # ─────────────────────────────────────────────────────────────────
    from ..utils.id_generator import generar_id
    
    visita = Visita(
        visita_id=generar_id("vis"),
        condominio_id=data.condominio_id,
        nombre_visitante=data.nombre_visitante,
        telefono=data.telefono,
        casa_unidad=data.casa_unidad,
        residente_anfitrion=data.residente_anfitrion,
        tipo_visitante=data.tipo_visitante,
        motivo=data.motivo,
        placa_vehiculo=data.placa_vehiculo or None,
        estado="creada_sin_qr",  # ← Estado nuevo
        qr_token=None,
        qr_vigencia=None,
        fecha_creacion=datetime.utcnow(),
        creada_por=usuario.usuario_id  # ← Guardia que creó
    )
    
    db.add(visita)
    db.flush()  # Para obtener visita_id inmediatamente
    
    logger.info(
        f"Visita rápida creada: {visita.visita_id}",
        extra={"usuario": usuario.usuario_id, "condominio": data.condominio_id}
    )
    
    # ─────────────────────────────────────────────────────────────────
    # AUP_EVENT: Registrar creación exitosa
    # ─────────────────────────────────────────────────────────────────
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    registrar_evento(
        db=db,
        identity=usuario,
        session_token=token,
        tenant_id=data.condominio_id,
        entidad=EventEntity.VISITA.value,
        entidad_id=visita.visita_id,
        accion=EventAction.CREAR.value,
        resultado=EventResult.EXITO.value,
        scope_id=scope.id if scope else None,
        motivo="Visita creada in-situ por guardia (sin QR previo)",
        metadata={
            "visitante": data.nombre_visitante,
            "tipo_visitante": data.tipo_visitante,
            "residente_anfitrion": data.residente_anfitrion,
            "casa_unidad": data.casa_unidad,
            "metodo_creacion": "rapida_sin_qr"
        }
    )
    
    db.commit()
    
    return visita
```

### Paso 3: Imports Necesarios

Agregar al inicio de `visitas_router.py`:

```python
from ..schemas.visita import VisitaRapidaCreate  # ← NUEVO
import logging  # ← Verificar que existe
from datetime import datetime  # ← Verificar que existe
```

---

## 🧪 TEST (Para verificar)

```python
# tests/test_modo_guardia.py - NUEVO ARCHIVO

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_crear_visita_rapida_exitosa():
    """Guardia crea visita sin QR previo"""
    
    # 1. Login como Guardia
    login_response = client.post("/auth/login", json={
        "email": "guardia@condominio.com",
        "password": "password123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. Crear visita rápida
    response = client.post(
        "/visitas/rapida",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "condominio_id": "cond_123",
            "nombre_visitante": "Juan Pérez",
            "telefono": "5551234567",
            "casa_unidad": "4B",
            "residente_anfitrion": "Carlos López",
            "tipo_visitante": "cliente",
            "motivo": "Reunión",
            "placa_vehiculo": "ABC1234"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "creada_sin_qr"
    assert data["qr_token"] is None
    assert "visita_id" in data


def test_crear_visita_rapida_no_guardia_falla():
    """Solo GUARDIAS pueden crear visitas rápidas"""
    
    # Login como RESIDENTE (no guardia)
    login_response = client.post("/auth/login", json={
        "email": "residente@condominio.com",
        "password": "password123"
    })
    token = login_response.json()["access_token"]
    
    # Intentar crear visita rápida
    response = client.post(
        "/visitas/rapida",
        headers={"Authorization": f"Bearer {token}"},
        json={...}
    )
    
    assert response.status_code == 403
    assert "Solo GUARDIAS" in response.json()["detail"]


def test_crear_visita_rapida_residente_invalido():
    """No puedes crear visita con residente que no existe"""
    
    token = "..."  # Token de guardia
    
    response = client.post(
        "/visitas/rapida",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "condominio_id": "cond_123",
            "nombre_visitante": "Juan",
            "telefono": "5551234567",
            "casa_unidad": "4B",
            "residente_anfitrion": "RESIDENTE_QUE_NO_EXISTE",
            "tipo_visitante": "cliente",
            "motivo": "Reunión",
            "placa_vehiculo": "ABC1234"
        }
    )
    
    assert response.status_code == 404
    assert "Residente no encontrado" in response.json()["detail"]
```

---

## 🎯 CHECKLIST DE IMPLEMENTACIÓN

- [ ] Agregar `VisitaRapidaCreate` schema en `backend/schemas/visita.py`
- [ ] Agregar endpoint `POST /visitas/rapida` en `visitas_router.py`
- [ ] Agregar imports necesarios
- [ ] Crear `tests/test_modo_guardia.py` con 3 tests
- [ ] Verificar que Visita model tiene campo `creada_por`
- [ ] Verificar migrations si es necesario
- [ ] Probar manualmente en Swagger: `http://localhost:8000/docs`
- [ ] Verificar AUP_EVENT registrado correctamente

---

## 📝 VERIFICACIÓN EN SERVIDOR

```bash
# 1. Verificar que Usuario modelo tiene campo creada_por
grep -n "creada_por" backend/db/core/models.py

# 2. Revisar tabla Visita
psql -c "\\d visita" $DATABASE_URL

# 3. Verificar generar_id function
grep -r "def generar_id" backend/
```

---

## 🚀 SIGUIENTE PASO

Una vez implementado y testeado `/visitas/rapida`:

→ POST `/visitas/{id}/registrar-entrada` (Marcar entrada oficial)

→ POST `/visitas/{id}/registrar-salida` (Marcar salida)

→ GET `/residentes/{condominio_id}` (Autocomplete)

---

**Documento:** Plan de Implementación - Modo Guardia MVP  
**Actualizado:** 31 Enero 2026  
**Status:** 🟢 LISTO PARA IMPLEMENTAR
