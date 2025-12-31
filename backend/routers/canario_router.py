"""
═══════════════════════════════════════════════════════════════════════════════
ENDPOINT CANARIO AUP — Demostrador Vivo del Modelo AUP
═══════════════════════════════════════════════════════════════════════════════

PROPÓSITO:
  Este endpoint NO es un feature de negocio.
  ES un demostrador vivo de AUP en acción.
  
  Demuestra:
    1. Bloqueo sin SESSION (AUP-01)
    2. Evaluación de GOV antes de negocio (AUP-02)
    3. Registro de EVENT obligatorio (AUP-03)
  
FLUJO OBLIGATORIO:
  REQUEST
   → AUP_SESSION (middleware AUPSessionGuard)
   → AUP_SCOPE (resolver alcance dinámico)
   → AUP_GOV (evaluar políticas - BLOQUEO AUP-02)
   → NEGOCIO (generar QR)
   → AUP_EVENT (registrar verdad - BLOQUEO AUP-03)
   → RESPONSE

RESTRICCIÓN DE EJEMPLO:
  Política activa: max_qr_dias = 3
  
  Si request pide > 3 días:
    → GOV DENY
    → EVENT registrado (DENIED_POLICY)
    → NEGOCIO NO ejecuta
    → HTTPException 403

AXIOMA VALIDADO:
  SESSION → SCOPE → GOV → NEGOCIO → EVENT
  (orden no negociable)

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import logging

from backend.db.core import Usuario, get_core_db
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.validator import validar_scope
from backend.core.gov.facade import puede_ejecutar_accion
from backend.core.event.registry import registrar_evento
from backend.core.event import EventEntity, EventAction, EventResult
from backend.core.aup_runtime_blocks import AUPGovEnforcer, AUPEventEnforcer

logger = logging.getLogger("aup.canario")

router = APIRouter(prefix="/qr", tags=["🐤 AUP Canario"])


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class GenerarQRGobernado_Request(BaseModel):
    """
    Request para generar QR gobernado.
    """
    visitante_nombre: str = Field(..., min_length=3, max_length=100)
    tenant_id: str = Field(..., description="ID del condominio")
    dias_vigencia: int = Field(..., ge=1, le=30, description="Días de vigencia del QR")


class GenerarQRGobernado_Response(BaseModel):
    """
    Response de QR gobernado.
    """
    qr_id: str
    qr_token: str
    visitante: str
    tenant_id: str
    vigencia_hasta: datetime
    creado_por: str
    evento_id: str  # ← Prueba de que EVENT se registró


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT CANARIO
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/generar_gobernado",
    response_model=GenerarQRGobernado_Response,
    summary="🐤 Endpoint Canario AUP",
    description="""
    **ENDPOINT DEMOSTRADOR DE AUP**
    
    Este endpoint demuestra el flujo completo AUP:
    
    1. **SESSION**: Bloqueada por middleware AUPSessionGuard
    2. **SCOPE**: Resuelto dinámicamente desde memoria CORE
    3. **GOV**: Evaluado ANTES de negocio (BLOQUEO AUP-02)
    4. **NEGOCIO**: Ejecutado solo si GOV permite
    5. **EVENT**: Registrado SIEMPRE (BLOQUEO AUP-03)
    
    **Restricción de gobierno activa:**
    - max_qr_dias = 3
    - Si solicitas > 3 días → GOV DENY
    
    **Casos de prueba:**
    ```
    # Caso éxito (dias_vigencia = 2)
    POST /qr/generar_gobernado
    {
      "visitante_nombre": "Juan Perez",
      "tenant_id": "condo_a",
      "dias_vigencia": 2
    }
    → 200 OK
    
    # Caso denegado por gobierno (dias_vigencia = 7)
    POST /qr/generar_gobernado
    {
      "visitante_nombre": "Juan Perez",
      "tenant_id": "condo_a",
      "dias_vigencia": 7
    }
    → 403 Forbidden (GOV denegó)
    
    # Caso sin SESSION
    POST /qr/generar_gobernado (sin Authorization header)
    → 401 Unauthorized (AUP-01 bloqueó)
    ```
    """
)
def generar_qr_gobernado(
    request: Request,
    body: GenerarQRGobernado_Request,
    db: Session = Depends(get_core_db),
    usuario: Usuario = Depends(get_current_user)  # ← AUP-01: SESSION validada por middleware
):
    """
    ═══════════════════════════════════════════════════════════════════════
    ENDPOINT CANARIO: Generación de QR GOBERNADA
    ═══════════════════════════════════════════════════════════════════════
    
    Este endpoint implementa el flujo AUP COMPLETO con bloqueos duros.
    
    Orden de ejecución (NO negociable):
      1. SESSION → Validada por middleware AUPSessionGuard
      2. SCOPE → Validar alcance en tenant
      3. GOV → Evaluar políticas (BLOQUEO AUP-02)
      4. NEGOCIO → Crear QR (solo si GOV permite)
      5. EVENT → Registrar (BLOQUEO AUP-03)
    
    Violaciones AUP que este endpoint previene:
      ❌ Ejecutar sin SESSION (bloqueado por middleware)
      ❌ Ejecutar sin SCOPE (validación explícita)
      ❌ Ejecutar sin GOV (AUPGovEnforcer lanza excepción)
      ❌ Retornar sin EVENT (AUPEventEnforcer lanza excepción)
    """
    
    logger.info(f"🐤 CANARIO: Iniciando generación QR gobernada por usuario {usuario.usuario_id}")
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 1: SESSION (ya validada por middleware AUPSessionGuard)
    # ─────────────────────────────────────────────────────────────────────
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    logger.info(f"✅ PASO 1/5: SESSION validada (usuario={usuario.usuario_id})")
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 2: SCOPE (validar alcance dinámico)
    # ─────────────────────────────────────────────────────────────────────
    from backend.db.core import AccessLevel
    
    tiene_scope = validar_scope(
        db=db,
        identity=usuario,
        tenant_id=body.tenant_id,
        required_level=AccessLevel.RESIDENTE  # Mínimo nivel requerido
    )
    
    if not tiene_scope:
        logger.warning(f"🚫 PASO 2/5 FALLÓ: Sin SCOPE en tenant {body.tenant_id}")
        
        # Registrar evento de denegación
        registrar_evento(
            db=db,
            identity=usuario,
            session_token=token,
            tenant_id=body.tenant_id,
            entidad=EventEntity.SCOPE.value,
            entidad_id=usuario.usuario_id,
            accion=EventAction.DENEGAR.value,
            resultado=EventResult.DENEGADO.value,
            motivo="Sin SCOPE activo en tenant",
            metadata={"tenant_solicitado": body.tenant_id}
        )
        
        raise HTTPException(
            status_code=403,
            detail="Sin alcance en este tenant"
        )
    
    logger.info(f"✅ PASO 2/5: SCOPE validado (tenant={body.tenant_id})")
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 3: GOV (evaluar gobierno con BLOQUEO AUP-02)
    # ─────────────────────────────────────────────────────────────────────
    with AUPGovEnforcer() as gov:
        # Evaluar política
        permitido, motivo = puede_ejecutar_accion(
            db=db,
            usuario=usuario,
            session_token=token,
            accion="generar_qr",
            tenant_id=body.tenant_id,
            metadata={"dias_vigencia": body.dias_vigencia}
        )
        
        # Marcar que GOV fue evaluado
        gov.mark_evaluated(permitido)
        
        if not permitido:
            logger.warning(f"🚫 PASO 3/5 FALLÓ: GOV denegó → {motivo}")
            raise HTTPException(
                status_code=403,
                detail=f"Gobierno denegó operación: {motivo}"
            )
        
        logger.info(f"✅ PASO 3/5: GOV permitió (política evaluada)")
        
        # ─────────────────────────────────────────────────────────────────
        # PASO 4: NEGOCIO (ejecutar solo después de GOV)
        # ─────────────────────────────────────────────────────────────────
        qr_id = str(uuid.uuid4())
        qr_token = str(uuid.uuid4())[:16].upper()
        vigencia_hasta = datetime.utcnow() + timedelta(days=body.dias_vigencia)
        
        # Aquí normalmente se insertaría en tabla `qrs` (omitido por simplicidad)
        # El objetivo es demostrar el flujo, no implementar QR completo
        
        # Marcar que negocio fue ejecutado
        gov.mark_business_executed()
        
        logger.info(f"✅ PASO 4/5: NEGOCIO ejecutado (QR generado: {qr_id})")
    
    # ─────────────────────────────────────────────────────────────────────
    # PASO 5: EVENT (registrar con BLOQUEO AUP-03)
    # ─────────────────────────────────────────────────────────────────────
    with AUPEventEnforcer(operation="generar_qr_gobernado") as event_guard:
        evento_id = registrar_evento(
            db=db,
            identity=usuario,
            session_token=token,
            tenant_id=body.tenant_id,
            entidad=EventEntity.QR.value,
            entidad_id=qr_id,
            accion=EventAction.CREAR.value,
            resultado=EventResult.EXITO.value,
            motivo="QR generado mediante endpoint gobernado canario",
            metadata={
                "visitante": body.visitante_nombre,
                "dias_vigencia": body.dias_vigencia,
                "vigencia_hasta": vigencia_hasta.isoformat(),
                "qr_token": qr_token
            }
        )
        
        # Marcar que EVENT fue registrado
        event_guard.mark_event_registered()
        
        logger.info(f"✅ PASO 5/5: EVENT registrado (evento_id={evento_id})")
    
    # ─────────────────────────────────────────────────────────────────────
    # RETORNO: Solo después de pasar TODOS los pasos AUP
    # ─────────────────────────────────────────────────────────────────────
    logger.info(f"🎉 CANARIO: Operación completa (QR={qr_id}, EVENT={evento_id})")
    
    return GenerarQRGobernado_Response(
        qr_id=qr_id,
        qr_token=qr_token,
        visitante=body.visitante_nombre,
        tenant_id=body.tenant_id,
        vigencia_hasta=vigencia_hasta,
        creado_por=usuario.usuario_id,
        evento_id=evento_id
    )


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT DE SALUD: Verificar que AUP_GOV tiene políticas cargadas
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/canario/health",
    summary="🏥 Salud del Canario AUP",
    description="Verifica que el sistema AUP tiene políticas cargadas y está listo"
)
def canario_health(db: Session = Depends(get_core_db)):
    """
    Endpoint de salud para verificar que AUP_GOV tiene políticas cargadas.
    
    NO requiere autenticación (útil para debugging).
    """
    from backend.db.gov import Policy
    
    policies_count = db.query(Policy).filter(Policy.estado == "ACTIVO").count()
    
    return {
        "status": "ok",
        "aup_gov_ready": policies_count > 0,
        "active_policies": policies_count,
        "message": (
            "Sistema AUP listo" if policies_count > 0 
            else "⚠️ No hay políticas activas. GOV denegará por defecto."
        )
    }
