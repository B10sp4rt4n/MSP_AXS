"""
Router de Condominios - INTEGRADO CON AUP_GOV

Operaciones críticas:
  - Crear tenant (condominio) → Requiere AUP_GOV
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..core.dependencies import get_db
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from backend.db.core import Usuario, Condominio, MSP, UserTenantScope, AccessLevel, get_core_db
from ..core.gov.facade import puede_ejecutar_accion
import uuid

logger = logging.getLogger("axs.condominios")
router = APIRouter(prefix="/condominios", tags=["condominios"])


class CondominioCreate(BaseModel):
    nombre: str
    msp_id: str
    direccion: Optional[str] = None


class CasaCreate(BaseModel):
    casa_unidad: str
    residente_nombre: Optional[str] = None
    residente_email: Optional[str] = None


class ResidenteBasico(BaseModel):
    usuario_id: str
    nombre: str
    email: str
    rol: str


class CasaResponse(BaseModel):
    casa_unidad: str
    residente: Optional[ResidenteBasico] = None


class CondominioResponse(BaseModel):
    condominio_id: str
    nombre: str
    msp_id: str
    total_usuarios: int = 0
    casas: List[CasaResponse] = []


@router.get("/", response_model=List[CondominioResponse])
def list_condominios(
    msp_id: Optional[str] = None,
    db: Session = Depends(get_core_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Lista condominios con sus casas anidadas."""
    if usuario.rol not in ["MSP_ADMIN", "ADMIN", "ADMIN_CONDOMINIO"]:
        raise HTTPException(403, detail="Acceso denegado")
    
    query = db.query(Condominio)
    
    # Filtrar por MSP si se especifica
    if msp_id:
        query = query.filter(Condominio.msp_id == msp_id)
    elif usuario.rol == "ADMIN_CONDOMINIO":
        # Ver solo su condominio
        query = query.filter(Condominio.condominio_id == usuario.condominio_id)
    
    condominios = query.all()
    
    resultado = []
    for c in condominios:
        # Contar usuarios
        total_usuarios = db.query(Usuario).filter(
            Usuario.condominio_id == c.condominio_id
        ).count()
        
        # Obtener casas con sus residentes
        casas_db = db.query(Usuario).filter(
            Usuario.condominio_id == c.condominio_id,
            Usuario.casa_unidad.isnot(None)
        ).all()
        
        # Agrupar por casa_unidad
        casas_dict = {}
        for usuario_db in casas_db:
            casa = usuario_db.casa_unidad
            if casa not in casas_dict:
                casas_dict[casa] = {
                    "casa_unidad": casa,
                    "residente": None
                }
            # El primer residente (usualmente el propietario/principal)
            if usuario_db.rol == "RESIDENTE":
                casas_dict[casa]["residente"] = {
                    "usuario_id": usuario_db.usuario_id,
                    "nombre": usuario_db.nombre,
                    "email": usuario_db.email,
                    "rol": usuario_db.rol
                }
        
        casas = [CasaResponse(**casa) for casa in casas_dict.values()]
        
        resultado.append(CondominioResponse(
            condominio_id=c.condominio_id,
            nombre=c.nombre,
            msp_id=c.msp_id or "",
            total_usuarios=total_usuarios,
            casas=casas
        ))
    
    return resultado


@router.post("/", response_model=CondominioResponse)
def crear_condominio(
    body: CondominioCreate,
    request: Request,
    db: Session = Depends(get_core_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo condominio (tenant).
    
    ═══════════════════════════════════════════════════════════════════════
    OPERACIÓN CRÍTICA: Requiere evaluación de AUP_GOV
    ═══════════════════════════════════════════════════════════════════════
    """
    logger.info(f"📝 Crear condominio solicitado por: {usuario.email} (rol: {usuario.rol})")
    
    if usuario.rol not in ["MSP_ADMIN", "ADMIN"]:
        logger.warning(f"🚫 Acceso denegado: usuario {usuario.email} tiene rol {usuario.rol}")
        raise HTTPException(403, detail="Requiere rol MSP_ADMIN")
    
    # Validar que el MSP existe
    msp = db.query(MSP).filter(MSP.msp_id == body.msp_id).first()
    if not msp:
        raise HTTPException(404, detail=f"MSP {body.msp_id} no encontrado")
    
    # ═══════════════════════════════════════════════════════════════════════
    # AUP_GOV: Evaluar política ANTES de crear tenant
    # Axioma: Gobierno precede a operación
    # ═══════════════════════════════════════════════════════════════════════
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # Contar tenants actuales
    tenants_count = db.query(Condominio).count()
    
    logger.info(f"🔍 Evaluando GOV para crear_tenant: tenants actuales={tenants_count}")
    
    permitido, motivo = puede_ejecutar_accion(
        db=db,
        usuario=usuario,
        session_token=token,
        accion="crear_tenant",
        valor_actual=tenants_count
    )
    
    logger.info(f"📊 Resultado GOV: permitido={permitido}, motivo={motivo}")
    
    if not permitido:
        logger.warning(f"🚫 GOV denegó acción: {motivo}")
        raise HTTPException(403, detail=f"Gobierno denegó creación: {motivo}")
    # ═══════════════════════════════════════════════════════════════════════
    
    # Crear condominio
    condominio_id = f"condo_{uuid.uuid4().hex[:12]}"
    nuevo_condo = Condominio(
        condominio_id=condominio_id,
        msp_id=body.msp_id,
        nombre=body.nombre
    )
    
    db.add(nuevo_condo)
    db.commit()
    db.refresh(nuevo_condo)
    
    return CondominioResponse(
        condominio_id=nuevo_condo.condominio_id,
        nombre=nuevo_condo.nombre,
        msp_id=nuevo_condo.msp_id or "",
        total_usuarios=0
    )


@router.post("/{condominio_id}/casas")
def crear_casa(
    condominio_id: str,
    body: CasaCreate,
    db: Session = Depends(get_core_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Crea una casa/unidad en un condominio y opcionalmente asigna un residente."""
    if usuario.rol not in ["MSP_ADMIN", "ADMIN", "ADMIN_CONDOMINIO"]:
        raise HTTPException(403, detail="Acceso denegado")
    
    # Validar que el condominio existe
    condo = db.query(Condominio).filter(
        Condominio.condominio_id == condominio_id
    ).first()
    if not condo:
        raise HTTPException(404, detail="Condominio no encontrado")
    
    # Si se proporciona residente, crearlo
    if body.residente_email:
        # Verificar que no exista
        existe = db.query(Usuario).filter(
            Usuario.email == body.residente_email
        ).first()
        
        if existe:
            raise HTTPException(400, detail="Email ya registrado")
        
        # Crear usuario residente
        usuario_id = f"user_{uuid.uuid4().hex[:12]}"
        nuevo_usuario = Usuario(
            usuario_id=usuario_id,
            email=body.residente_email,
            nombre=body.residente_nombre or "Residente",
            rol="RESIDENTE",
            condominio_id=condominio_id,
            casa_unidad=body.casa_unidad,
            msp_id=condo.msp_id,
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YQvR9Bc0IaXi"  # default: password123
        )
        
        db.add(nuevo_usuario)
        db.flush()  # Asegurar que el usuario se inserte primero
        
        # Crear scope para el usuario
        scope = UserTenantScope(
            usuario_id=usuario_id,
            tenant_id=condominio_id,
            access_level=AccessLevel.RESIDENTE,
            estado="ACTIVO"
        )
        db.add(scope)
        db.commit()
        
        return {
            "status": "ok",
            "casa_unidad": body.casa_unidad,
            "residente_creado": True,
            "usuario_id": usuario_id,
            "email": body.residente_email,
            "password_temporal": "password123"
        }
    
    return {
        "status": "ok",
        "casa_unidad": body.casa_unidad,
        "residente_creado": False
    }


@router.get("/{condominio_id}/casas")
def listar_casas(
    condominio_id: str,
    db: Session = Depends(get_core_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Lista todas las casas/unidades de un condominio."""
    if usuario.rol not in ["MSP_ADMIN", "ADMIN", "ADMIN_CONDOMINIO", "GUARDIA"]:
        raise HTTPException(403, detail="Acceso denegado")
    
    # Obtener usuarios del condominio agrupados por casa_unidad
    usuarios = db.query(Usuario).filter(
        Usuario.condominio_id == condominio_id
    ).all()
    
    # Agrupar por casa
    casas = {}
    for u in usuarios:
        if u.casa_unidad:
            if u.casa_unidad not in casas:
                casas[u.casa_unidad] = []
            casas[u.casa_unidad].append({
                "usuario_id": u.usuario_id,
                "nombre": u.nombre,
                "email": u.email,
                "rol": u.rol
            })
    
    return {
        "condominio_id": condominio_id,
        "total_casas": len(casas),
        "casas": [
            {
                "casa_unidad": casa,
                "residentes": residentes
            }
            for casa, residentes in casas.items()
        ]
    }

