"""
Router de Condominios - INTEGRADO CON AUP_GOV

Operaciones críticas:
  - Crear tenant (condominio) → Requiere AUP_GOV
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..core.auth.dependencies import get_current_user
from backend.db.core import Usuario, Condominio, Casa, MSP, UserTenantScope, AccessLevel, get_core_db
from backend.db.core import ScopeStatus
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import (
    active_msp_ids, is_platform_operator, require_condominio, require_msp_admin,
)
from ..core.gov.facade import puede_ejecutar_accion
import uuid

router = APIRouter(prefix="/condominios", tags=["condominios"])


class CondominioCreate(BaseModel):
    nombre: str
    msp_id: str
    direccion: Optional[str] = None


class CasaCreate(BaseModel):
    numero: str
    tipo: Optional[str] = "casa"   # casa / depto / local
    descripcion: Optional[str] = None


class AsignarResidente(BaseModel):
    nombre: str
    email: str


class ResidenteBasico(BaseModel):
    usuario_id: str
    nombre: str
    email: str
    rol: str


class CasaResponse(BaseModel):
    casa_unidad: str
    residente: Optional[ResidenteBasico] = None


class CasaFullResponse(BaseModel):
    casa_id: str
    numero: str
    tipo: str
    descripcion: Optional[str] = None
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
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Lista condominios accesibles para el usuario autenticado."""
    query = db.query(Condominio)
    if msp_id:
        query = query.filter(Condominio.msp_id == msp_id)
    if not is_platform_operator(db_gov, usuario):
        msp_ids = active_msp_ids(db, usuario)
        scoped_tenants = [
            row[0] for row in db.query(UserTenantScope.tenant_id).filter(
                UserTenantScope.usuario_id == usuario.usuario_id,
                UserTenantScope.estado == ScopeStatus.ACTIVO,
            ).all()
        ]
        if not msp_ids and not scoped_tenants:
            return []
        from sqlalchemy import or_
        query = query.filter(or_(
            Condominio.msp_id.in_(msp_ids),
            Condominio.condominio_id.in_(scoped_tenants),
        ))
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
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo condominio (tenant).
    
    ═══════════════════════════════════════════════════════════════════════
    OPERACIÓN CRÍTICA: Requiere evaluación de AUP_GOV
    ═══════════════════════════════════════════════════════════════════════
    """
    require_msp_admin(db, db_gov, usuario, body.msp_id)
    
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
    # La política actual crear_tenant es global; el cupo por MSP requiere
    # una política de proveedor explícita en una migración posterior.
    tenants_count = db.query(Condominio).count()
    
    permitido, motivo = puede_ejecutar_accion(
        db=db,
        usuario=usuario,
        session_token=token,
        accion="crear_tenant",
        valor_actual=tenants_count,
        db_gov=db_gov,
    )
    
    if not permitido:
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


@router.post("/{condominio_id}/casas", response_model=CasaFullResponse)
def crear_casa(
    condominio_id: str,
    body: CasaCreate,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Crea una casa/depto/local en un condominio (sin residente)."""
    require_condominio(db, db_gov, usuario, condominio_id, AccessLevel.ADMIN_CONDOMINIO)

    # Evitar duplicados de número dentro del mismo condominio
    existe = db.query(Casa).filter(
        Casa.condominio_id == condominio_id,
        Casa.numero == body.numero.strip()
    ).first()
    if existe:
        raise HTTPException(400, detail=f"Ya existe la unidad '{body.numero}' en este condominio")

    casa = Casa(
        casa_id=f"casa_{uuid.uuid4().hex[:10]}",
        condominio_id=condominio_id,
        numero=body.numero.strip(),
        tipo=body.tipo or "casa",
        descripcion=body.descripcion,
    )
    db.add(casa)
    db.commit()
    db.refresh(casa)

    return CasaFullResponse(
        casa_id=casa.casa_id,
        numero=casa.numero,
        tipo=casa.tipo,
        descripcion=casa.descripcion,
        residente=None,
    )


@router.post("/{condominio_id}/casas/{casa_id}/residente")
def asignar_residente(
    condominio_id: str,
    casa_id: str,
    body: AsignarResidente,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Asigna un residente a una casa existente."""
    condo = require_condominio(db, db_gov, usuario, condominio_id, AccessLevel.ADMIN_CONDOMINIO)

    casa = db.query(Casa).filter(Casa.casa_id == casa_id, Casa.condominio_id == condominio_id).first()
    if not casa:
        raise HTTPException(404, detail="Casa no encontrada")

    # Verificar que el email no esté registrado
    existe = db.query(Usuario).filter(Usuario.email == body.email.strip()).first()
    if existe:
        raise HTTPException(400, detail="Email ya registrado en el sistema")

    usuario_id = f"user_{uuid.uuid4().hex[:12]}"
    nuevo = Usuario(
        usuario_id=usuario_id,
        email=body.email.strip(),
        nombre=body.nombre.strip() or "Residente",
        rol="RESIDENTE",
        condominio_id=condominio_id,
        casa_id=casa_id,
        casa_unidad=casa.numero,    # Denormalizado para compat legado
        msp_id=condo.msp_id if condo else None,
        password_hash=None,         # Auth via Clerk
    )
    db.add(nuevo)
    db.flush()

    scope = UserTenantScope(
        usuario_id=usuario_id,
        tenant_id=condominio_id,
        access_level=AccessLevel.RESIDENTE,
        estado=ScopeStatus.ACTIVO
    )
    db.add(scope)
    db.commit()

    return {
        "status": "ok",
        "usuario_id": usuario_id,
        "email": body.email,
        "casa_id": casa_id,
        "numero": casa.numero,
    }


@router.get("/{condominio_id}/casas")
def listar_casas(
    condominio_id: str,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Lista todas las casas del condominio con su residente asignado."""
    require_condominio(db, db_gov, usuario, condominio_id, AccessLevel.GUARDIA)

    casas = db.query(Casa).filter(Casa.condominio_id == condominio_id).order_by(Casa.numero).all()

    resultado = []
    for casa in casas:
        residente = db.query(Usuario).filter(
            Usuario.casa_id == casa.casa_id,
            Usuario.rol == "RESIDENTE"
        ).first()
        resultado.append({
            "casa_id": casa.casa_id,
            "numero": casa.numero,
            "tipo": casa.tipo,
            "descripcion": casa.descripcion,
            "residente": {
                "usuario_id": residente.usuario_id,
                "nombre": residente.nombre,
                "email": residente.email,
                "rol": residente.rol,
            } if residente else None,
        })

    return {
        "condominio_id": condominio_id,
        "total_casas": len(resultado),
        "casas": resultado,
    }
