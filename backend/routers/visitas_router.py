"""
═══════════════════════════════════════════════════════════════════════════════
Router de Visitas - FASE 6: ALINEADO CON AUP
═══════════════════════════════════════════════════════════════════════════════

FLUJO CANÓNICO (7 pasos):
  1. Resolver identidad     → get_current_user
  2. Resolver tenant        → path param / body
  3. SET app.tenant_id      → set_tenant_context
  4. Validar scope          → validar_scope (si > LECTURA)
  5. Evaluar gobierno       → puede_ejecutar_accion (si aplica)
  6. Ejecutar acción        → service
  7. Registrar evento       → registrar_evento

ESTADO: Migración FASE 6 en progreso
  - POST /visitas/           → MIGRADO ✅
  - GET /mis-visitas         → PENDIENTE
  - GET /condominio          → PENDIENTE
  - GET /{visita_id}         → PENDIENTE

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
<<<<<<< HEAD
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
=======
>>>>>>> origin/main
from typing import List

# AUP_IDENTITY
from backend.core.auth.dependencies import get_current_user
from backend.db.models import Usuario, AccessLevel

# AUP_TENANT (FASE 6)
from backend.core.tenant.context import set_tenant_context, require_tenant_context

# AUP_SCOPE
from backend.core.scope.validator import validar_scope, obtener_scope_usuario_en_tenant

# AUP_GOV
from backend.core.gov.facade import puede_ejecutar_accion

# AUP_EVENT
from backend.core.event.registry import registrar_evento
from backend.core.event import EventEntity, EventAction, EventResult

# Infraestructura
from backend.core.dependencies import get_db
from backend.services import visita_service
from backend.schemas.visita import VisitaCreate, VisitaResponse

# DEPRECADO - Solo para endpoints no migrados aún
from backend.core.security import verificar_rol

router = APIRouter(prefix="/visitas", tags=["Visitas"])


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT MIGRADO FASE 6: POST /visitas/
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{condominio_id}", response_model=VisitaResponse)
def crear_visita(
    condominio_id: str,                                          # PASO 2: tenant desde path
    data: VisitaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),           # PASO 1: identidad
    _tenant: str = Depends(set_tenant_context),                  # PASO 3: SET app.tenant_id
):
    """
    ═══════════════════════════════════════════════════════════════════════════
    CREAR VISITA — Endpoint Canónico FASE 6
    ═══════════════════════════════════════════════════════════════════════════
    
    FLUJO AUP COMPLETO:
      1. ✅ Identidad resuelta (get_current_user)
      2. ✅ Tenant resuelto (path param: condominio_id)
      3. ✅ SET app.tenant_id (set_tenant_context)
      4. ✅ Validar scope (ADMIN_CONDOMINIO requerido)
      5. ✅ Evaluar gobierno (límite de visitas si aplica)
      6. ✅ Ejecutar acción (crear visita)
      7. ✅ Registrar evento (éxito o denegación)
    
    CRITERIOS AUP-A:
      - AUP-A1: No usa verificar_rol() ✅
      - AUP-A2: No usa usuario.rol para decisiones ✅
      - AUP-A3: Usa get_current_user ✅
      - AUP-A4: Usa set_tenant_context ✅
      - AUP-A5: Usa validar_scope ✅
      - AUP-A6: Usa puede_ejecutar_accion ✅
      - AUP-A7: Usa registrar_evento ✅
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PASO 4: Validar scope (requiere ADMIN_CONDOMINIO para crear visitas)
    # ─────────────────────────────────────────────────────────────────────────
    if not validar_scope(db, current_user, condominio_id, AccessLevel.ADMIN_CONDOMINIO):
        # Registrar intento denegado ANTES de fallar
        registrar_evento(
            db=db,
            identity=current_user,
            session_token=token,
            tenant_id=condominio_id,
            entidad=EventEntity.VISITA.value,
            entidad_id="pending",
            accion=EventAction.CREAR.value,
            resultado=EventResult.DENEGADO.value,
            scope_id=None,
            motivo="Scope insuficiente: requiere ADMIN_CONDOMINIO"
        )
        raise HTTPException(
            status_code=403,
            detail="Requiere nivel ADMIN_CONDOMINIO en este condominio"
        )
    
    # Obtener scope_id para eventos
    scope = obtener_scope_usuario_en_tenant(db, current_user.usuario_id, condominio_id)
    
    # ─────────────────────────────────────────────────────────────────────────
    # PASO 5: Evaluar gobierno (límites de política si aplica)
    # ─────────────────────────────────────────────────────────────────────────
    permitido, motivo_gov = puede_ejecutar_accion(
        db=db,
        usuario=current_user,
        session_token=token,
        accion="crear_visita",
        tenant_id=condominio_id,
        metadata={"visitante": data.nombre_visitante}
    )
    
    if not permitido:
        registrar_evento(
            db=db,
            identity=current_user,
            session_token=token,
            tenant_id=condominio_id,
            entidad=EventEntity.VISITA.value,
            entidad_id="pending",
            accion=EventAction.CREAR.value,
            resultado=EventResult.DENEGADO.value,
            scope_id=scope.id if scope else None,
            motivo=f"Gobierno denegó: {motivo_gov}"
        )
        raise HTTPException(status_code=403, detail=f"Gobierno denegó: {motivo_gov}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PASO 6: Ejecutar acción de negocio
    # ─────────────────────────────────────────────────────────────────────────
    visita = visita_service.crear_visita(
        db,
        data,
        condominio_id=condominio_id,
        casa_unidad=data.casa_unidad,
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # PASO 7: Registrar evento de éxito
    # ─────────────────────────────────────────────────────────────────────────
    registrar_evento(
        db=db,
        identity=current_user,
        session_token=token,
        tenant_id=condominio_id,
        entidad=EventEntity.VISITA.value,
        entidad_id=visita.visita_id,
        accion=EventAction.CREAR.value,
        resultado=EventResult.EXITO.value,
        scope_id=scope.id if scope else None,
        motivo="Visita creada exitosamente",
        metadata={
            "visitante": data.nombre_visitante,
            "casa_unidad": data.casa_unidad,
            "fecha_entrada": str(data.fecha_entrada) if data.fecha_entrada else None
        }
    )
    
    return visita


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT LEGACY (compatibilidad) - DEPRECADO
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=VisitaResponse, deprecated=True)
def crear_visita_legacy(
    data: VisitaCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    ⚠️ DEPRECADO: Usar POST /{condominio_id} en su lugar.
    
    Este endpoint se mantiene temporalmente para compatibilidad.
    Fecha de muerte: 2026-04-01
    """
    # Redirigir al nuevo endpoint usando condominio_id del body
    from backend.core.scope.validator import validate_user_owns_resource_in_tenant
    
    try:
        validate_user_owns_resource_in_tenant(
            usuario=usuario,
            resource_tenant_id=data.condominio_id,
            db=db,
            required_level=AccessLevel.ADMIN_CONDOMINIO
        )
    except HTTPException as e:
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
            motivo=f"[LEGACY] Sin scope válido: {e.detail}"
        )
        raise
    
    scope = obtener_scope_usuario_en_tenant(db, usuario.usuario_id, data.condominio_id)
    visita = visita_service.crear_visita(db, data, condominio_id=data.condominio_id, casa_unidad=data.casa_unidad)
    
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
        motivo="[LEGACY] Visita creada",
        metadata={"visitante": data.nombre_visitante, "casa_unidad": data.casa_unidad}
    )
    
    return visita


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS PENDIENTES DE MIGRACIÓN (usan verificar_rol - DEPRECADO)
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/mis-visitas/{condominio_id}", response_model=List[VisitaResponse])
def mis_visitas(
    condominio_id: str,                                          # PASO 2: tenant desde path
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),           # PASO 1: identidad
    _tenant: str = Depends(set_tenant_context),                  # PASO 3: SET app.tenant_id
):
    """
    ═══════════════════════════════════════════════════════════════════════════
    LISTAR MIS VISITAS — Endpoint Migrado FASE 6
    ═══════════════════════════════════════════════════════════════════════════
    
    FLUJO AUP COMPLETO:
      1. ✅ Identidad resuelta (get_current_user)
      2. ✅ Tenant resuelto (path param: condominio_id)
      3. ✅ SET app.tenant_id (set_tenant_context)
      4. ✅ Validar scope (RESIDENTE mínimo)
      5. ✅ Ejecutar acción (listar visitas)
    
    Lista visitas del residente en su condominio.
    RLS garantiza aislamiento multi-tenant.
    """
    # PASO 4: Validar scope (requiere al menos RESIDENTE)
    if not validar_scope(db, current_user, condominio_id, AccessLevel.RESIDENTE):
        raise HTTPException(
            status_code=403,
            detail="Requiere nivel RESIDENTE en este condominio"
        )
    
    # PASO 6: Ejecutar acción - RLS ya está activo
    visitas = visita_service.obtener_visitas_residente(
        db,
        condominio_id=condominio_id,
        casa_unidad=current_user.casa_unidad,
    )
    return visitas

# ---------------------------------------------------------
# Listar todas las visitas del condominio (admin / guardia) - MIGRADO FASE 6
# ---------------------------------------------------------
@router.get("/condominio/{condominio_id}", response_model=List[VisitaResponse])
def visitas_condominio(
    condominio_id: str,                                          # PASO 2: tenant desde path
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),           # PASO 1: identidad
    _tenant: str = Depends(set_tenant_context),                  # PASO 3: SET app.tenant_id
):
    """
    ═══════════════════════════════════════════════════════════════════════════
    LISTAR VISITAS DEL CONDOMINIO — Endpoint Migrado FASE 6
    ═══════════════════════════════════════════════════════════════════════════
    
    Lista todas las visitas del condominio.
    Requiere nivel GUARDIA (admin o guardia).
    RLS garantiza aislamiento multi-tenant.
    """
    # PASO 4: Validar scope (requiere GUARDIA mínimo)
    if not validar_scope(db, current_user, condominio_id, AccessLevel.GUARDIA):
        raise HTTPException(
            status_code=403,
            detail="Requiere nivel GUARDIA o superior en este condominio"
        )
    
    # PASO 6: Ejecutar acción - RLS ya está activo
    visitas = visita_service.obtener_visitas_condominio(
        db, condominio_id
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
