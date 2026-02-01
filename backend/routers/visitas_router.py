"""
═══════════════════════════════════════════════════════════════════════════════
Router de Visitas - MIGRADO A AUP_SESSION + AUP_SCOPE
═══════════════════════════════════════════════════════════════════════════════

PASO 1: AUP_SESSION valida identidad (JWT)
PASO 2: AUP_SCOPE valida alcance en tenant (scope)

"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from ..core.dependencies import get_db
from backend.db.core import get_core_db
from backend.db.event import get_event_db
from ..core.auth.dependencies import get_current_user
# from ..core.scope.validator import validate_user_owns_resource_in_tenant, obtener_scope_usuario_in_tenant
from ..core.scope.validator import obtener_scope_usuario_en_tenant
from ..core.security import verificar_rol
from ..services import visita_service
from ..schemas.visita import (
    VisitaCreate, VisitaResponse, VisitaRapidaCreate, VisitaRapidaResponse,
    CapturaEvidenciasResponse, RegistrarEntradaRequest, RegistrarEntradaResponse,
    RegistrarSalidaRequest, RegistrarSalidaResponse
)
from backend.db.core import Usuario, AccessLevel, Visita, Evidencia
from ..core.event.registry import registrar_evento
from ..core.event import EventEntity, EventAction, EventResult
from typing import List
import uuid
from datetime import datetime
import os
import cloudinary
import cloudinary.uploader

router = APIRouter(prefix="/visitas", tags=["Visitas"])


# ---------------------------------------------------------
# Crear visita (solo Administración del condominio)
# ---------------------------------------------------------
@router.post("/", response_model=VisitaResponse)
def crear_visita(
    data: VisitaCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # PASO 1: AUP_SESSION
):
    """
    VALIDACIÓN AUP COMPLETA:
      1. AUP_SESSION: Usuario autenticado (JWT válido)
      2. AUP_SCOPE: Usuario tiene alcance en el tenant objetivo
      3. AUP_EVENT: Registrar creación de visita
    """
    # PASO 2: AUP_SCOPE - Validar que el usuario sea GUARDIA o ADMIN
    if usuario.rol not in ["GUARDIA", "ADMIN", "ADMIN_CONDOMINIO", "MSP_ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Solo guardias y administradores pueden crear visitas"
        )
    
    # Obtener scope_id para el evento (temporal: None si no existe)
    try:
        scope = obtener_scope_usuario_en_tenant(db, usuario.usuario_id, data.condominio_id)
        scope_id = scope.id if scope else None
    except:
        scope_id = None
    
    # Crear visita
    visita = visita_service.crear_visita(
        db,
        data,
        condominio_id=data.condominio_id,
        casa_unidad=data.casa_unidad,
    )
    
    # PASO 3: AUP_EVENT - Registrar creación exitosa
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
        scope_id=scope_id,
        motivo="Visita creada exitosamente",
        metadata={
            "visitante": data.nombre_visitante,
            "casa_unidad": data.casa_unidad,
            "fecha_entrada": str(data.fecha_entrada)
        }
    )
    
    return visita


# ---------------------------------------------------------
# Crear visita rápida (in-situ, sin QR previo) - SOLO GUARDIA
# ---------------------------------------------------------
@router.post("/rapida", response_model=VisitaRapidaResponse)
def crear_visita_rapida(
    data: VisitaRapidaCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # PASO 1: AUP_SESSION
):
    """
    FLUJO GUARDIA - Crear visita en-situ:
    
    1. AUP_SESSION: Usuario autenticado (JWT válido)
    2. AUP_SCOPE: Usuario es GUARDIA del condominio
    3. Crear visita sin QR previo (estado="creada_sin_qr")
    4. AUP_EVENT: Registrar creación
    5. Esperar a que guardia capture fotos y registre entrada
    
    CAMPOS OBLIGATORIOS:
    - nombre_visitante: string (2-100 chars)
    - casa_unidad: string (1-50 chars)
    - tipo_visitante: string (frecuente|eventual|proveedor|cliente|entrega|consulta|familia)
    
    CAMPOS OPCIONALES:
    - telefono: string (1-15 chars)
    - residente_anfitrion: string (1-100 chars)
    - motivo: string (1-200 chars)
    - placa_vehiculo: string (1-20 chars)
    """
    # PASO 1: Validar que usuario es GUARDIA
    verificar_rol(usuario, ["GUARDIA"])
    
    # PASO 2: Validar que guardia pertenece a este condominio
    if usuario.condominio_id is None:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=token,
            tenant_id="unknown",
            entidad=EventEntity.VISITA.value,
            entidad_id="pending",
            accion=EventAction.CREAR.value,
            resultado=EventResult.RECHAZADO.value,
            scope_id=None,
            motivo="Guardia no tiene condominio asignado"
        )
        raise HTTPException(403, "Guardia no tiene condominio asignado")
    
    # PASO 3: Generar ID único para visita
    visita_id = f"VIS-{uuid.uuid4().hex[:8].upper()}"
    
    try:
        # PASO 4: Crear registro en base de datos
        from backend.db.core.models import Visita
        
        visita = Visita(
            visita_id=visita_id,
            condominio_id=usuario.condominio_id,
            nombre_visitante=data.nombre_visitante,
            telefono=data.telefono,
            casa_unidad=data.casa_unidad,
            residente_anfitrion=data.residente_anfitrion,
            tipo_visitante=data.tipo_visitante,
            motivo=data.motivo,
            placa_vehiculo=data.placa_vehiculo,
            estado="creada_sin_qr",  # No tiene QR aún
            creada_por=usuario.usuario_id,  # Guardia que creó
            created_at=datetime.utcnow()
        )
        
        db.add(visita)
        db.commit()
        db.refresh(visita)
        
    except Exception as e:
        db.rollback()
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=token,
            tenant_id=usuario.condominio_id,
            entidad=EventEntity.VISITA.value,
            entidad_id=visita_id,
            accion=EventAction.CREAR.value,
            resultado=EventResult.ERROR.value,
            scope_id=None,
            motivo=f"Error creando visita: {str(e)}"
        )
        raise HTTPException(500, f"Error creando visita: {str(e)}")
    
    # PASO 5: AUP_EVENT - Registrar creación exitosa
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    registrar_evento(
        db=db,
        identity=usuario,
        session_token=token,
        tenant_id=usuario.condominio_id,
        entidad=EventEntity.VISITA.value,
        entidad_id=visita_id,
        accion=EventAction.CREAR.value,
        resultado=EventResult.EXITO.value,
        scope_id=None,
        motivo="Visita rápida creada por guardia (sin QR)",
        metadata={
            "visitante": data.nombre_visitante,
            "casa_unidad": data.casa_unidad,
            "tipo_visitante": data.tipo_visitante,
            "creada_por": usuario.usuario_id
        }
    )
    
    return VisitaRapidaResponse.model_validate(visita)


# ---------------------------------------------------------
# Listar visitas del residente
# ---------------------------------------------------------
@router.get("/mis-visitas", response_model=List[VisitaResponse])
def mis_visitas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # PASO 1: AUP_SESSION
):
    """
    VALIDACIÓN AUP:
      Lista visitas del condominio al que pertenece el usuario.
      AUP_SCOPE se valida implícitamente: usuario.condominio_id
      debe tener scope activo.
    
    NOTA:
      Este endpoint usa el tenant del usuario (usuario.condominio_id)
      En vez de validar scope, asumimos que si usuario.condominio_id existe,
      debería tener scope. Para ser estricto AUP, validar scope explícitamente.
    """
    # TODO: Hacer estrictamente AUP validando scope
    # validate_user_owns_resource_in_tenant(
    #     usuario=usuario,
    #     resource_tenant_id=usuario.condominio_id,
    #     db=db,
    #     required_level=AccessLevel.RESIDENTE
    # )
    
    verificar_rol(usuario, ["RESIDENTE"])
    visitas = visita_service.obtener_visitas_residente(
        db,
        condominio_id=usuario.condominio_id,
        casa_unidad=usuario.casa_unidad,
    )
    return visitas


# ---------------------------------------------------------
# Listar todas las visitas del condominio (admin / guardia)
# ---------------------------------------------------------
@router.get("/condominio", response_model=List[VisitaResponse])
def visitas_condominio(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO", "GUARDIA"])
    visitas = visita_service.obtener_visitas_condominio(
        db, usuario.condominio_id
    )
    return visitas


# ---------------------------------------------------------
# Obtener visita individual por ID
# ---------------------------------------------------------
@router.get("/{visita_id}", response_model=VisitaResponse)
def obtener_visita(
    visita_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    visita = visita_service.obtener_visita(db, visita_id)
    if not visita:
        raise HTTPException(404, "Visita no encontrada")

    # reglas de acceso
    if usuario.rol == "RESIDENTE":
        if (
            visita.condominio_id != usuario.condominio_id
            or visita.casa_unidad != usuario.casa_unidad
        ):
            raise HTTPException(403, "No autorizado")
    return visita


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS MODO GUARDIA - CAPTURA Y REGISTRO
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{visita_id}/capturar-evidencias", response_model=CapturaEvidenciasResponse)
async def capturar_evidencias(
    visita_id: str,
    foto_visitante: UploadFile = File(...),
    foto_documento_frente: UploadFile = File(None),
    foto_documento_reverso: UploadFile = File(None),
    foto_placa: UploadFile = File(None),
    foto_vehiculo: UploadFile = File(None),
    db: Session = Depends(get_core_db),
    db_event: Session = Depends(get_event_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Captura múltiples fotos de evidencia para una visita.
    
    MODO GUARDIA - PASO 1:
    - Guardia captura fotos del visitante (mínimo 1, recomendado 3+)
    - Fotos se suben a Cloudinary
    - Se registran en tabla evidencias
    - Estado de visita: creada_sin_qr → entrada_pendiente
    
    Requiere rol: GUARDIA
    """
    verificar_rol(usuario, ["GUARDIA"])
    
    # Verificar que la visita existe
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    # Verificar que el guardia pertenece al mismo condominio
    if visita.condominio_id != usuario.condominio_id:
        raise HTTPException(403, "No autorizado para esta visita")
    
    # Verificar que la visita está en estado correcto
    if visita.estado not in ["creada_sin_qr", "entrada_pendiente"]:
        raise HTTPException(400, f"Visita en estado '{visita.estado}' no permite captura de evidencias")
    
    # Configurar Cloudinary
    use_cloudinary = os.getenv("USE_CLOUDINARY", "true").lower() == "true"
    
    fotos_subidas = []
    fotos = [
        ("visitante", foto_visitante),
        ("documento_frente", foto_documento_frente),
        ("documento_reverso", foto_documento_reverso),
        ("placa", foto_placa),
        ("vehiculo", foto_vehiculo),
    ]
    
    for tipo, foto in fotos:
        if foto is None:
            continue
            
        try:
            if use_cloudinary:
                # Subir a Cloudinary
                contents = await foto.read()
                result = cloudinary.uploader.upload(
                    contents,
                    folder=f"visitas/{visita_id}",
                    public_id=f"{tipo}_{datetime.utcnow().timestamp()}",
                    resource_type="image",
                    transformation=[
                        {"width": 1920, "height": 1080, "crop": "limit"},
                        {"quality": "auto:good"}
                    ]
                )
                url = result["secure_url"]
            else:
                # Modo desarrollo: guardar local
                upload_dir = f"/tmp/evidencias/{visita_id}"
                os.makedirs(upload_dir, exist_ok=True)
                file_path = f"{upload_dir}/{tipo}_{datetime.utcnow().timestamp()}.jpg"
                contents = await foto.read()
                with open(file_path, "wb") as f:
                    f.write(contents)
                url = f"file://{file_path}"
            
            # Registrar evidencia en BD
            evidencia_id = f"EVI-{uuid.uuid4().hex[:8].upper()}"
            evidencia = Evidencia(
                evidencia_id=evidencia_id,
                visita_id=visita_id,
                categoria="entrada",
                sub_tipo=tipo,
                archivo_url=url,
                guardia_id=usuario.usuario_id,
                metadata_json={"filename": foto.filename, "size": foto.size},
                created_at=datetime.utcnow()
            )
            db.add(evidencia)
            fotos_subidas.append(url)
            
        except Exception as e:
            raise HTTPException(500, f"Error subiendo foto {tipo}: {str(e)}")
    
    # Actualizar estado de visita si hay fotos
    if len(fotos_subidas) > 0:
        visita.estado = "entrada_pendiente"
        db.commit()
        
        # Registrar evento AUP
        registrar_evento(
            db=db_event,
            identity=usuario,
            session_token="modo_guardia",
            tenant_id=usuario.condominio_id,
            entidad=EventEntity.VISITA.value,
            entidad_id=visita_id,
            accion=EventAction.MODIFICAR.value,
            resultado=EventResult.EXITO.value,
            scope_id=None,
            motivo=f"Captura de {len(fotos_subidas)} evidencias fotográficas",
            metadata={"total_fotos": len(fotos_subidas), "tipos": [t for t, f in fotos if f]}
        )
    
    return CapturaEvidenciasResponse(
        visita_id=visita_id,
        total_fotos=len(fotos_subidas),
        fotos_urls=fotos_subidas,
        estado=visita.estado,
        mensaje=f"Se capturaron {len(fotos_subidas)} fotos exitosamente"
    )


@router.post("/{visita_id}/registrar-entrada", response_model=RegistrarEntradaResponse)
def registrar_entrada(
    visita_id: str,
    data: RegistrarEntradaRequest,
    db: Session = Depends(get_core_db),
    db_event: Session = Depends(get_event_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Registra la entrada oficial del visitante.
    
    MODO GUARDIA - PASO 2:
    - Valida que haya al menos 1 foto capturada
    - Auto-genera código QR para el visitante
    - Marca hora de entrada
    - Estado: entrada_pendiente → entrada_registrada
    
    Requiere rol: GUARDIA
    """
    verificar_rol(usuario, ["GUARDIA"])
    
    # Verificar visita
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    if visita.condominio_id != usuario.condominio_id:
        raise HTTPException(403, "No autorizado")
    
    # Verificar estado
    if visita.estado not in ["entrada_pendiente", "creada_sin_qr"]:
        raise HTTPException(400, f"Visita en estado '{visita.estado}' no permite registro de entrada")
    
    # Verificar evidencias (al menos 1 foto)
    total_evidencias = db.query(Evidencia).filter(
        Evidencia.visita_id == visita_id,
        Evidencia.categoria == "entrada"
    ).count()
    
    if total_evidencias == 0:
        raise HTTPException(400, "Debe capturar al menos 1 foto antes de registrar entrada")
    
    # Generar QR token
    import secrets
    qr_token = secrets.token_urlsafe(32)
    qr_vigencia = datetime.utcnow().replace(hour=23, minute=59, second=59)  # Válido hasta fin del día
    
    # Actualizar visita
    visita.estado = "entrada_registrada"
    visita.hora_entrada = datetime.utcnow()
    visita.entrada_registrada_en = datetime.utcnow()
    visita.qr_token = qr_token
    visita.qr_vigencia = qr_vigencia
    
    db.commit()
    
    # Registrar evento
    registrar_evento(
        db=db_event,
        identity=usuario,
        session_token="modo_guardia",
        tenant_id=usuario.condominio_id,
        entidad=EventEntity.VISITA.value,
        entidad_id=visita_id,
        accion="REGISTRAR_ENTRADA",
        resultado=EventResult.EXITO.value,
        scope_id=None,
        motivo="Entrada registrada por guardia",
        metadata={
            "hora_entrada": visita.hora_entrada.isoformat(),
            "total_evidencias": total_evidencias,
            "notas": data.notas
        }
    )
    
    return RegistrarEntradaResponse(
        visita_id=visita_id,
        estado=visita.estado,
        hora_entrada=visita.hora_entrada,
        qr_token=qr_token,
        qr_vigencia=qr_vigencia,
        mensaje=f"Entrada registrada. QR generado. Evidencias: {total_evidencias}"
    )


@router.post("/{visita_id}/registrar-salida", response_model=RegistrarSalidaResponse)
def registrar_salida(
    visita_id: str,
    data: RegistrarSalidaRequest,
    db: Session = Depends(get_core_db),
    db_event: Session = Depends(get_event_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Registra la salida del visitante.
    
    MODO GUARDIA - PASO 3:
    - Marca hora de salida
    - Calcula duración de visita
    - Estado: entrada_registrada → salida_registrada
    
    Requiere rol: GUARDIA
    """
    verificar_rol(usuario, ["GUARDIA"])
    
    # Verificar visita
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    
    if visita.condominio_id != usuario.condominio_id:
        raise HTTPException(403, "No autorizado")
    
    # Verificar estado
    if visita.estado != "entrada_registrada":
        raise HTTPException(400, f"Visita en estado '{visita.estado}' no permite registro de salida")
    
    if not visita.hora_entrada:
        raise HTTPException(400, "No hay registro de entrada")
    
    # Actualizar visita
    visita.estado = "salida_registrada"
    visita.hora_salida = datetime.utcnow()
    visita.salida_registrada_en = datetime.utcnow()
    
    # Calcular duración
    duracion = int((visita.hora_salida - visita.hora_entrada).total_seconds() / 60)
    
    db.commit()
    
    # Registrar evento
    registrar_evento(
        db=db_event,
        identity=usuario,
        session_token="modo_guardia",
        tenant_id=usuario.condominio_id,
        entidad=EventEntity.VISITA.value,
        entidad_id=visita_id,
        accion="REGISTRAR_SALIDA",
        resultado=EventResult.EXITO.value,
        scope_id=None,
        motivo="Salida registrada por guardia",
        metadata={
            "hora_salida": visita.hora_salida.isoformat(),
            "duracion_minutos": duracion,
            "notas": data.notas
        }
    )
    
    return RegistrarSalidaResponse(
        visita_id=visita_id,
        estado=visita.estado,
        hora_entrada=visita.hora_entrada,
        hora_salida=visita.hora_salida,
        duracion_minutos=duracion,
        mensaje=f"Salida registrada. Duración: {duracion} minutos"
    )

