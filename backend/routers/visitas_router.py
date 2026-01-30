"""
═══════════════════════════════════════════════════════════════════════════════
Router de Visitas - MIGRADO A AUP_SESSION + AUP_SCOPE
═══════════════════════════════════════════════════════════════════════════════

PASO 1: AUP_SESSION valida identidad (JWT)
PASO 2: AUP_SCOPE valida alcance en tenant (scope)

"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..core.dependencies import get_db
from ..core.auth.dependencies import get_current_user
# from ..core.scope.validator import validate_user_owns_resource_in_tenant, obtener_scope_usuario_en_tenant
from ..core.scope.validator import obtener_scope_usuario_en_tenant
from ..core.security import verificar_rol
from ..services import visita_service
from ..schemas.visita import VisitaCreate, VisitaResponse
from backend.db.core import Usuario, AccessLevel
from ..core.event.registry import registrar_evento
from ..core.event import EventEntity, EventAction, EventResult
from typing import List

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
    # PASO 2: AUP_SCOPE - Validar alcance en tenant
    try:
        validate_user_owns_resource_in_tenant(
            usuario=usuario,
            resource_tenant_id=data.condominio_id,
            db=db,
            required_level=AccessLevel.ADMIN_CONDOMINIO
        )
    except HTTPException as e:
        # AUP_EVENT: Intento denegado por falta de scope
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
            scope_id=None,
            motivo=f"Sin scope válido en tenant: {e.detail}"
        )
        raise
    
    # Obtener scope_id para el evento
    scope = obtener_scope_usuario_en_tenant(db, usuario.usuario_id, data.condominio_id)
    
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
        scope_id=scope.id if scope else None,
        motivo="Visita creada exitosamente",
        metadata={
            "visitante": data.nombre_visitante,
            "casa_unidad": data.casa_unidad,
            "fecha_entrada": str(data.fecha_entrada)
        }
    )
    
    return visita


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
