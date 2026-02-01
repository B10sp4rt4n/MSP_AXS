# 🔧 IMPLEMENTACIÓN: Modo Guardia MVP

**Estado:** 🔴 CRÍTICO  
**Prioridad:** Semana 1  
**Effort:** 40 horas (1 dev senior)

---

## 📌 Endpoints a Implementar (Orden de Desarrollo)

### 1️⃣ POST /visitas/rapida ← PRIMERO

**Propósito:** Crear visita sin QR previo (visitante sorpresa).

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

**Response (200):**
```json
{
  "visita_id": "vis_abc123def456",
  "nombre_visitante": "Juan Pérez Rodríguez",
  "estado": "creada_sin_qr",
  "casa_unidad": "4B",
  "condominio_id": "cond_123",
  "fecha_creacion": "2026-01-31T14:30:00Z",
  "mensaje": "Visita creada. Guardia debe capturar fotos."
}
```

**Validaciones:**
- ✅ AUP_SESSION: Usuario GUARDIA autenticado
- ✅ AUP_SCOPE: Guardia en condominio_id
- ✅ Verificar residente_anfitrion existe
- ✅ Registrar AUP_EVENT "CREAR_VISITA_RAPIDA"

**Código Base:**
```python
# backend/routers/visitas_router.py

@router.post("/rapida", response_model=VisitaResponse)
def crear_visita_rapida(
    data: VisitaRapidaCreate,  # Nuevo schema
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Crear visita in-situ sin QR previo.
    Usado por Guardias en puerta para visitantes no registrados.
    
    AUP Layers:
      1. AUP_SESSION: Validado por get_current_user
      2. AUP_SCOPE: Validar usuario en condominio
      3. AUP_EVENT: Registrar creación
    """
    verificar_rol(usuario, ["GUARDIA"])
    
    # AUP_SCOPE: Verificar guardia en este condominio
    scope = obtener_scope_usuario_en_tenant(
        db, usuario.usuario_id, data.condominio_id
    )
    if not scope:
        raise HTTPException(403, "No tienes acceso a este condominio")
    
    # Crear visita
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
        estado="creada_sin_qr",  # Nuevo estado
        qr_token=None,
        qr_vigencia=None,
        fecha_creacion=datetime.utcnow(),
        creada_por=usuario.usuario_id
    )
    db.add(visita)
    db.commit()
    
    # AUP_EVENT
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
        scope_id=scope.id,
        motivo="Visita creada in-situ por guardia",
        metadata={
            "visitante": data.nombre_visitante,
            "tipo": data.tipo_visitante,
            "metodo_creacion": "rapida_sin_qr"
        }
    )
    
    return visita
```

**Schema Requerido:**
```python
# backend/schemas/visita.py

class VisitaRapidaCreate(BaseModel):
    condominio_id: str
    nombre_visitante: str
    telefono: str
    casa_unidad: str
    residente_anfitrion: str
    tipo_visitante: str  # cliente|entrega|consulta|familia
    motivo: str
    placa_vehiculo: Optional[str] = None
```

---

### 2️⃣ POST /visitas/{visita_id}/registrar-entrada

**Propósito:** Marcar entrada oficial (después de fotos).

**Request:**
```json
{
  "fotos_capturadas": 5,
  "notas": "Documento válido, vehículo permitido"
}
```

**Response (200):**
```json
{
  "visita_id": "vis_abc123",
  "estado": "entrada_registrada",
  "hora_entrada": "2026-01-31T14:35:00Z",
  "autorizado_por": "gua_001",
  "duracion_proceso": "5 minutos",
  "mensaje": "Visitante autorizado para ingresar"
}
```

**Lógica:**
1. Validar visita existe en estado "creada_sin_qr" o pre-registrada
2. Verificar que hay al menos 3 fotos capturadas
3. Cambiar estado a "entrada_registrada"
4. Generar QR automáticamente (vigencia +12h)
5. Registrar AUP_EVENT "REGISTRAR_ENTRADA"

**Código Base:**
```python
@router.post("/{visita_id}/registrar-entrada")
def registrar_entrada(
    visita_id: str,
    data: RegistrarEntradaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    verificar_rol(usuario, ["GUARDIA"])
    
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    # Contar fotos de entrada
    fotos = db.query(Evidencia).filter(
        Evidencia.visita_id == visita_id,
        Evidencia.tipo == "entrada"
    ).count()
    
    if fotos < 3:
        raise HTTPException(400, f"Se requieren al menos 3 fotos. Tienes {fotos}")
    
    # Actualizar visita
    visita.estado = "entrada_registrada"
    visita.hora_entrada = datetime.utcnow()
    db.commit()
    
    # Generar QR automáticamente si no existe
    if not visita.qr_token:
        qr_data = qr_service.generar_qr_para_visita(visita_id)
        visita_service.actualizar_qr(
            db, visita_id, qr_data["token"], qr_data["qr_vigencia"]
        )
    
    # AUP_EVENT
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    registrar_evento(
        db=db,
        identity=usuario,
        session_token=token,
        tenant_id=visita.condominio_id,
        entidad=EventEntity.VISITA.value,
        entidad_id=visita_id,
        accion=EventAction.REGISTRAR_ENTRADA.value,
        resultado=EventResult.EXITO.value,
        motivo="Entrada registrada por guardia",
        metadata={
            "fotos_capturadas": fotos,
            "visitante": visita.nombre_visitante,
            "hora_entrada": str(datetime.utcnow())
        }
    )
    
    return {
        "visita_id": visita_id,
        "estado": visita.estado,
        "hora_entrada": visita.hora_entrada,
        "autorizado_por": usuario.usuario_id,
        "qr_token": visita.qr_token
    }
```

---

### 3️⃣ POST /visitas/{visita_id}/registrar-salida

**Propósito:** Marcar salida oficial.

**Request:**
```json
{
  "fotos_capturadas": 2,
  "notas": "Visitante se retira normalmente"
}
```

**Response (200):**
```json
{
  "visita_id": "vis_abc123",
  "estado": "salida_registrada",
  "hora_entrada": "2026-01-31T14:35:00Z",
  "hora_salida": "2026-01-31T16:45:00Z",
  "duracion_visita": "2 horas 10 minutos",
  "autorizado_por": "gua_001"
}
```

**Código Base:**
```python
@router.post("/{visita_id}/registrar-salida")
def registrar_salida(
    visita_id: str,
    data: RegistrarSalidaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    verificar_rol(usuario, ["GUARDIA"])
    
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    if visita.estado != "entrada_registrada":
        raise HTTPException(400, f"Visita no está en entrada_registrada. Estado actual: {visita.estado}")
    
    visita.estado = "salida_registrada"
    visita.hora_salida = datetime.utcnow()
    duracion = visita.hora_salida - visita.hora_entrada
    
    db.commit()
    
    # AUP_EVENT
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    registrar_evento(
        db=db,
        identity=usuario,
        session_token=token,
        tenant_id=visita.condominio_id,
        entidad=EventEntity.VISITA.value,
        entidad_id=visita_id,
        accion=EventAction.REGISTRAR_SALIDA.value,
        resultado=EventResult.EXITO.value,
        motivo="Salida registrada por guardia",
        metadata={
            "duracion_minutos": int(duracion.total_seconds() / 60),
            "visitante": visita.nombre_visitante,
            "hora_salida": str(visita.hora_salida)
        }
    )
    
    return {
        "visita_id": visita_id,
        "estado": visita.estado,
        "hora_entrada": visita.hora_entrada,
        "hora_salida": visita.hora_salida,
        "duracion_minutos": int(duracion.total_seconds() / 60)
    }
```

---

### 4️⃣ GET /residentes/{condominio_id}

**Propósito:** Listar residentes para autocompletar al capturar visitante.

**Response (200):**
```json
{
  "residentes": [
    {
      "usuario_id": "usr_001",
      "nombre": "Carlos López",
      "unidad": "4B",
      "telefono": "5559876543"
    },
    {
      "usuario_id": "usr_002",
      "nombre": "Ana García",
      "unidad": "5A",
      "telefono": "5558765432"
    }
  ]
}
```

**Código Base:**
```python
@router.get("/residentes/{condominio_id}")
def listar_residentes(
    condominio_id: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO"])
    
    residentes = db.query(Usuario).filter(
        Usuario.condominio_id == condominio_id,
        Usuario.rol.in_(["RESIDENTE", "ADMIN_CONDOMINIO"])
    ).all()
    
    return {
        "residentes": [
            {
                "usuario_id": r.usuario_id,
                "nombre": r.nombre or "Sin nombre",
                "unidad": r.casa_unidad or "N/A",
                "telefono": r.telefono or "N/A"
            }
            for r in residentes
        ]
    }
```

---

## 📋 Estado de BD Requerido

```sql
-- Agregar estados nuevos a tabla visita
ALTER TABLE visita ADD COLUMN hora_entrada TIMESTAMP NULL;
ALTER TABLE visita ADD COLUMN hora_salida TIMESTAMP NULL;
ALTER TABLE visita ADD COLUMN creada_por VARCHAR(50) NULL;

-- Índices para performance
CREATE INDEX idx_visita_estado ON visita(estado);
CREATE INDEX idx_visita_condominio_fecha ON visita(condominio_id, fecha_creacion DESC);
```

---

## 🧪 Tests Requeridos

```python
# tests/test_modo_guardia.py

def test_crear_visita_rapida():
    """Guardia crea visita sin QR"""
    
def test_registrar_entrada_sin_fotos_falla():
    """No se puede marcar entrada sin fotos"""
    
def test_registrar_entrada_genera_qr():
    """Marcar entrada genera QR automáticamente"""
    
def test_registrar_salida_calcula_duracion():
    """Salida registra duración total"""
    
def test_flujo_completo_guardia():
    """Flujo: Crear → Fotos → Entrada → Dentro → Salida"""
```

---

## ⏱️ Timeline

```
Lunes-Martes:
  - POST /visitas/rapida
  - GET /residentes/{id}
  
Miércoles:
  - POST /visitas/{id}/registrar-entrada
  - POST /visitas/{id}/registrar-salida
  
Jueves-Viernes:
  - Tests (20+ casos)
  - UI mejorada (captura rápida)
  - Documentación
```

---

**Prioridad:** 🔴 CRÍTICA  
**Blocker:** Sin esto, los Guardias no pueden funcionar sin pre-registración.
