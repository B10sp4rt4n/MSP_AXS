"""Visitas con autoridad GLOBAL, membresía MSP o scope de condominio.

Creación y listados autorizan el condominio antes de fijar contexto RLS.
Las operaciones por ID usan require_visita y restringen vivienda del residente.
La creación canónica y legacy comparten gobierno y registro EVENT.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

# AUP_IDENTITY
from backend.core.auth.dependencies import get_current_user
from backend.db.core import Usuario, AccessLevel

# AUP_SCOPE
from backend.core.scope.validator import obtener_scope_usuario_en_tenant

# AUP_GOV
from backend.core.gov.facade import puede_ejecutar_accion

# AUP_EVENT
from backend.core.event.registry import registrar_evento
from backend.core.event import EventEntity, EventAction, EventResult

# Infraestructura
from backend.db.core import get_core_db
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_visita, authorized_tenant_context
from backend.services import visita_service
from backend.services.event_outbox import contexto_evento
from backend.schemas.visita import VisitaCreate, VisitaResponse

# DEPRECADO - Solo para endpoints no migrados aún
from backend.core.security import verificar_rol

router = APIRouter(prefix="/visitas", tags=["Visitas"])


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT MIGRADO FASE 6: POST /visitas/
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/entrada/{condominio_id}", response_model=VisitaResponse)
def crear_visita_con_entrada(
    condominio_id: str,
    data: VisitaCreate,
    request: Request,
    db: Session = Depends(get_core_db),
    current_user: Usuario = Depends(get_current_user),
    db_gov: Session = Depends(get_gov_db),
    _tenant: str = Depends(authorized_tenant_context(AccessLevel.GUARDIA)),
):
    verificar_rol(current_user, ["GUARDIA", "MSP_ADMIN", "ADMIN_CONDOMINIO"])
    return crear_visita(condominio_id, data, request, db, current_user, db_gov, _tenant,
                        entrada_inmediata=True)


@router.post("/{condominio_id}", response_model=VisitaResponse)
def crear_visita(
    condominio_id: str,                                          # PASO 2: tenant desde path
    data: VisitaCreate,
    request: Request,
    db: Session = Depends(get_core_db),
    current_user: Usuario = Depends(get_current_user),           # PASO 1: identidad
    db_gov: Session = Depends(get_gov_db),
    _tenant: str = Depends(authorized_tenant_context(AccessLevel.ADMIN_CONDOMINIO)),                  # PASO 3: SET app.tenant_id
    entrada_inmediata: bool = False,
):
    """Crea dentro del condominio autorizado por GLOBAL, membresía MSP o scope.

    El gobierno permanece obligatorio. Un body con otro condominio se rechaza.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if data.condominio_id != condominio_id:
        raise HTTPException(400, "El condominio del cuerpo no coincide con la ruta")

    label, destination = visita_service.resolver_destino(
        db, condominio_id, destino_id=data.destino_id,
        casa_unidad=data.casa_unidad, motivo=data.destino_motivo,
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
        metadata={"visitante": data.nombre_visitante},
        db_gov=db_gov,
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
        casa_unidad=label,
        entrada_inmediata=entrada_inmediata,
        destino=destination,
        auditoria=contexto_evento(current_user, token, accion="crear", motivo="Visita creada exitosamente"),
    )
    
    # El evento de éxito queda persistido en CORE junto con la visita.
    return visita


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT LEGACY (compatibilidad) - DEPRECADO
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=VisitaResponse, deprecated=True)
def crear_visita_legacy(
    data: VisitaCreate,
    request: Request,
    db: Session = Depends(get_core_db),
    usuario: Usuario = Depends(get_current_user),
    db_gov: Session = Depends(get_gov_db),
):
    """
    ⚠️ DEPRECADO: Usar POST /{condominio_id} en su lugar.
    
    Este endpoint se mantiene temporalmente para compatibilidad.
    Fecha de muerte: 2026-04-01
    """
    from backend.core.scope.msp_boundary import require_condominio
    from backend.core.tenant.context import _set_postgres_tenant
    require_condominio(db, db_gov, usuario, data.condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    _set_postgres_tenant(db, data.condominio_id)
    return crear_visita(data.condominio_id, data, request, db, usuario, db_gov, data.condominio_id)


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS PENDIENTES DE MIGRACIÓN (usan verificar_rol - DEPRECADO)
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/mis-visitas/{condominio_id}", response_model=List[VisitaResponse])
def mis_visitas(
    condominio_id: str,                                          # PASO 2: tenant desde path
    db: Session = Depends(get_core_db),
    current_user: Usuario = Depends(get_current_user),           # PASO 1: identidad
    _tenant: str = Depends(authorized_tenant_context(AccessLevel.RESIDENTE)),                  # PASO 3: SET app.tenant_id
):
    """
    ═══════════════════════════════════════════════════════════════════════════
    LISTAR MIS VISITAS — Endpoint Migrado FASE 6
    ═══════════════════════════════════════════════════════════════════════════
    
    FLUJO AUP COMPLETO:
      1. ✅ Identidad resuelta (get_current_user)
      2. ✅ Tenant resuelto (path param: condominio_id)
      3. ✅ SET app.tenant_id (authorized_tenant_context)
      4. ✅ Validar scope (RESIDENTE mínimo)
      5. ✅ Ejecutar acción (listar visitas)
    
    Lista visitas del residente en su condominio.
    RLS garantiza aislamiento multi-tenant.
    """
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
    db: Session = Depends(get_core_db),
    current_user: Usuario = Depends(get_current_user),           # PASO 1: identidad
    _tenant: str = Depends(authorized_tenant_context(AccessLevel.GUARDIA)),                  # PASO 3: SET app.tenant_id
):
    """
    ═══════════════════════════════════════════════════════════════════════════
    LISTAR VISITAS DEL CONDOMINIO — Endpoint Migrado FASE 6
    ═══════════════════════════════════════════════════════════════════════════
    
    Lista todas las visitas del condominio.
    Requiere nivel GUARDIA (admin o guardia).
    RLS garantiza aislamiento multi-tenant.
    """
    # PASO 6: Ejecutar acción - RLS ya está activo
    visitas = visita_service.obtener_visitas_condominio(
        db, condominio_id
    )
    return visitas


# ---------------------------------------------------------
# Registrar salida (guardia / admin)
# ---------------------------------------------------------
@router.patch("/{visita_id}/entrada", response_model=VisitaResponse)
def registrar_entrada_manual(
    visita_id: str,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
    condominio_id: str | None = None,
):
    verificar_rol(usuario, ["GUARDIA", "MSP_ADMIN", "ADMIN_CONDOMINIO"])
    visita = require_visita(db, db_gov, usuario, visita_id, AccessLevel.GUARDIA,
                           condominio_id=condominio_id)
    if visita.estado not in ["pendiente", "activa"] or visita.entrada_registrada_en:
        raise HTTPException(400, "La visita ya tiene entrada o está finalizada")
    if visita.qr_token:
        raise HTTPException(400, "Esta visita requiere validar su QR")
    return visita_service.registrar_entrada(db, visita_id, auditoria=contexto_evento(
        usuario, request.headers.get("Authorization", "").replace("Bearer ", ""),
        motivo="Entrada manual registrada"))


@router.patch("/{visita_id}/salida")
def registrar_salida(
    visita_id: str,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
    condominio_id: str | None = None,
):
    verificar_rol(usuario, ["GUARDIA", "MSP_ADMIN", "ADMIN_CONDOMINIO"])
    visita = require_visita(db, db_gov, usuario, visita_id, AccessLevel.GUARDIA,
                           condominio_id=condominio_id)
    if visita.estado != "entrada_registrada" or not visita.entrada_registrada_en:
        raise HTTPException(400, f"No se puede registrar salida en estado '{visita.estado}'")
    visita = visita_service.registrar_salida(db, visita_id, auditoria=contexto_evento(
        usuario, request.headers.get("Authorization", "").replace("Bearer ", ""),
        motivo="Salida registrada"))
    return {"status": "ok", "visita_id": visita_id, "estado": visita.estado}


# ---------------------------------------------------------
# Cancelar visita (residente / admin)
# ---------------------------------------------------------
@router.patch("/{visita_id}/cancelar")
def cancelar_visita(
    visita_id: str,
    request: Request,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
    condominio_id: str | None = None,
):
    if usuario.rol not in ["RESIDENTE", "MSP_ADMIN", "ADMIN_CONDOMINIO"]:
        raise HTTPException(403, "No autorizado")
    level = AccessLevel.RESIDENTE if usuario.rol == "RESIDENTE" else AccessLevel.ADMIN_CONDOMINIO
    visita = require_visita(db, db_gov, usuario, visita_id, level,
                           own_unit=usuario.rol == "RESIDENTE", condominio_id=condominio_id)
    if usuario.rol == "RESIDENTE":
        if visita.condominio_id != usuario.condominio_id or visita.casa_unidad != usuario.casa_unidad:
            raise HTTPException(403, "No autorizado para esta visita")
    if visita.estado in ["cancelada", "salida_registrada"]:
        raise HTTPException(400, f"La visita ya está en estado '{visita.estado}'")
    visita_service.cancelar_visita(db, visita_id, estado_esperado=visita.estado,
        auditoria=contexto_evento(usuario, request.headers.get("Authorization", "").replace("Bearer ", ""),
                                  accion="revocar", motivo="Visita cancelada"))
    return {"status": "ok", "visita_id": visita_id, "estado": "cancelada"}


# ---------------------------------------------------------
# Obtener visita individual por ID
# ---------------------------------------------------------
@router.get("/{visita_id}", response_model=VisitaResponse)
def obtener_visita(
    visita_id: str,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
    condominio_id: str | None = None,
):
    return require_visita(db, db_gov, usuario, visita_id, AccessLevel.RESIDENTE,
                          own_unit=usuario.rol == "RESIDENTE", condominio_id=condominio_id)

