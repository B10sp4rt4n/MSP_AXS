"""
Router de Condominios - INTEGRADO CON AUP_GOV

Operaciones críticas:
  - Crear tenant (condominio) → Requiere AUP_GOV
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Literal
from ..core.auth.dependencies import get_current_user
from backend.db.core import Usuario, Condominio, Casa, MSP, MSPMembership, UserTenantScope, AccessLevel, get_core_db
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
    tipo: Literal["casa", "depto", "local", "administracion", "mantenimiento", "area_comun"] = "casa"
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
    db.flush()
    for tipo, nombre in [("administracion", "Administración"), ("mantenimiento", "Mantenimiento"), ("area_comun", "Área común")]:
        db.add(Casa(casa_id=f"dest_{uuid.uuid4().hex[:12]}", condominio_id=condominio_id, numero=nombre, tipo=tipo))
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

    if casa.tipo not in {"casa", "depto", "local"}:
        raise HTTPException(400, detail="Los residentes requieren una vivienda")

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


class PersonalCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=254)
    rol: Literal["GUARDIA", "ADMIN_CONDOMINIO"]

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Nombre requerido")
        return value

    @field_validator("email")
    @classmethod
    def validar_email(cls, value):
        import re
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Email inválido")
        return value


@router.get("/{condominio_id}/usuarios")
def listar_usuarios(
    condominio_id: str,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista identidades con asignación activa al condominio."""
    require_condominio(db, db_gov, usuario, condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    rows = db.query(Usuario, UserTenantScope).join(
        UserTenantScope, UserTenantScope.usuario_id == Usuario.usuario_id
    ).filter(
        UserTenantScope.tenant_id == condominio_id,
        UserTenantScope.estado == ScopeStatus.ACTIVO,
    ).order_by(Usuario.nombre).all()
    result = {}
    for identity, scope in rows:
        result[identity.usuario_id] = {
            "usuario_id": identity.usuario_id, "nombre": identity.nombre or "",
            "email": identity.email or "", "rol": scope.access_level.name,
            "casa_unidad": identity.casa_unidad if identity.condominio_id == condominio_id else None,
            "casa_id": identity.casa_id if identity.condominio_id == condominio_id else None,
            "registro_pendiente": identity.clerk_id is None,
        }
    return list(result.values())


@router.post("/{condominio_id}/usuarios")
def crear_personal(
    condominio_id: str,
    body: PersonalCreate,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Preasigna una identidad de personal; Clerk conserva su rol al vincularla."""
    condo = require_condominio(db, db_gov, usuario, condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    if body.rol == "ADMIN_CONDOMINIO":
        require_msp_admin(db, db_gov, usuario, condo.msp_id)
    existing = db.query(Usuario).filter(func.lower(Usuario.email) == body.email).with_for_update().first()
    if existing:
        # Sólo incorporar cuentas de autorregistro que aún carezcan de asignación.
        # No cambiar residentes, personal existente ni operadores de otro proveedor.
        assigned = db.query(UserTenantScope.id).filter(
            UserTenantScope.usuario_id == existing.usuario_id
        ).first()
        membership = db.query(MSPMembership.id).filter(
            MSPMembership.usuario_id == existing.usuario_id
        ).first()
        if (existing.condominio_id or existing.casa_id or assigned or membership
                or (existing.rol or "").upper() != "RESIDENTE" or is_platform_operator(db_gov, existing)):
            raise HTTPException(409, detail="Email ya asignado; no se modificó su rol ni su condominio")
        identity = existing
    else:
        identity = Usuario(usuario_id=f"user_{uuid.uuid4().hex[:12]}", email=body.email,
                           password_hash=None)
        db.add(identity)
    identity.nombre = body.nombre
    identity.rol = body.rol
    identity.msp_id = condo.msp_id
    identity.condominio_id = condominio_id
    identity.casa_id = None
    identity.casa_unidad = None
    try:
        db.flush()
        db.add(UserTenantScope(
            usuario_id=identity.usuario_id, tenant_id=condominio_id,
            access_level=AccessLevel[body.rol], estado=ScopeStatus.ACTIVO,
            metadata_json={"assigned_by": usuario.usuario_id, "source": "panel_personal"},
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="Email ya registrado; actualiza la lista de usuarios")
    return {
        "usuario_id": identity.usuario_id, "nombre": identity.nombre,
        "email": identity.email, "rol": identity.rol,
        "registro_pendiente": identity.clerk_id is None,
    }


class UsuarioEdit(PersonalCreate):
    model_config = ConfigDict(extra="forbid")
    rol: Literal["GUARDIA", "ADMIN_CONDOMINIO", "RESIDENTE"]
    casa_id: Optional[str] = None


@router.patch("/{condominio_id}/usuarios/{usuario_id}")
def editar_usuario(
    condominio_id: str,
    usuario_id: str,
    body: UsuarioEdit,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
):
    condo = require_condominio(db, db_gov, usuario, condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    identity = db.query(Usuario).filter(
        Usuario.usuario_id == usuario_id, Usuario.condominio_id == condominio_id
    ).with_for_update().first()
    if not identity:
        raise HTTPException(404, detail="Usuario no encontrado en este condominio")
    scopes = db.query(UserTenantScope).filter(
        UserTenantScope.usuario_id == usuario_id, UserTenantScope.estado == ScopeStatus.ACTIVO
    ).all()
    local = [s for s in scopes if s.tenant_id == condominio_id]
    if not local:
        raise HTTPException(404, detail="Usuario sin asignación activa")
    if (any(s.tenant_id != condominio_id for s in scopes)
            or db.query(MSPMembership.id).filter(MSPMembership.usuario_id == usuario_id).first()
            or is_platform_operator(db_gov, identity)
            or identity.rol not in ("GUARDIA", "ADMIN_CONDOMINIO", "RESIDENTE")):
        raise HTTPException(409, detail="Esta cuenta requiere gestión de alcance global")
    changed_role = body.rol != identity.rol
    if changed_role or identity.rol == "ADMIN_CONDOMINIO":
        require_msp_admin(db, db_gov, usuario, condo.msp_id)
    if changed_role and usuario_id == usuario.usuario_id:
        raise HTTPException(400, detail="No puedes cambiar tu propio rol desde este panel")
    if body.email != identity.email.lower() and identity.clerk_id:
        raise HTTPException(400, detail="El correo de una cuenta registrada se cambia desde Administrar cuenta, verificando el nuevo correo")
    duplicate = db.query(Usuario.usuario_id).filter(
        func.lower(Usuario.email) == body.email, Usuario.usuario_id != usuario_id
    ).first()
    if duplicate:
        raise HTTPException(409, detail="Email ya registrado")
    casa = None
    if body.rol == "RESIDENTE":
        if body.casa_id:
            casa = db.query(Casa).filter(
                Casa.casa_id == body.casa_id, Casa.condominio_id == condominio_id
            ).with_for_update().first()
            if not casa:
                raise HTTPException(400, detail="La vivienda no pertenece a este condominio")
            if casa.tipo not in {"casa", "depto", "local"}:
                raise HTTPException(400, detail="Los residentes requieren una vivienda")
            occupied = db.query(Usuario.usuario_id).filter(
                Usuario.casa_id == casa.casa_id, Usuario.rol == "RESIDENTE",
                Usuario.usuario_id != usuario_id,
            ).first()
            if occupied:
                raise HTTPException(409, detail="La vivienda ya tiene un residente asignado")
        elif changed_role or identity.casa_id:
            raise HTTPException(400, detail="Selecciona la vivienda del residente")
    elif body.casa_id:
        raise HTTPException(400, detail="Sólo los residentes tienen vivienda asignada")
    identity.nombre = body.nombre
    identity.email = body.email
    identity.rol = body.rol
    if casa:
        identity.casa_id = casa.casa_id
        identity.casa_unidad = casa.numero
    elif body.rol != "RESIDENTE":
        identity.casa_id = None
        identity.casa_unidad = None
    for scope in local:
        scope.access_level = AccessLevel[body.rol]
        scope.metadata_json = {
            **(scope.metadata_json or {}), "last_edited_by": usuario.usuario_id,
            "source": "panel_usuarios",
        }
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="Email ya registrado; actualiza la lista")
    return {"status": "ok", "usuario_id": identity.usuario_id}


@router.get("/{condominio_id}/destinos")
def listar_destinos(
    condominio_id: str,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
):
    require_condominio(db, db_gov, usuario, condominio_id, AccessLevel.GUARDIA)
    return [{"destino_id": c.casa_id, "nombre": c.numero, "tipo": c.tipo}
            for c in db.query(Casa).filter(Casa.condominio_id == condominio_id)
            .order_by(Casa.numero).all()]
