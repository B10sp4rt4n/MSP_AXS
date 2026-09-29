from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import uuid

from backend.db.core import get_core_db, MSP, Condominio, Usuario, MSPMembership
from backend.db.gov import get_gov_db
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import active_msp_ids, is_platform_operator, require_platform_operator

router = APIRouter(prefix="/msps", tags=["MSPs"])


class MSPCreate(BaseModel):
    nombre: str


class MSPResponse(BaseModel):
    msp_id: str
    nombre: str
    total_condominios: int = 0


@router.get("/", response_model=List[MSPResponse])
def list_msps(
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user)
):
    """El operador ve todos; el administrador solo sus MSP explícitos."""
    query = db.query(MSP)
    if not is_platform_operator(db_gov, usuario):
        ids = active_msp_ids(db, usuario)
        if not ids:
            return []
        query = query.filter(MSP.msp_id.in_(ids))
    msps = query.all()
    
    resultado = []
    for msp in msps:
        total_condos = db.query(Condominio).filter(
            Condominio.msp_id == msp.msp_id
        ).count()
        
        resultado.append(MSPResponse(
            msp_id=msp.msp_id,
            nombre=msp.nombre,
            total_condominios=total_condos
        ))
    
    return resultado


@router.post("/", response_model=MSPResponse)
def crear_msp(
    body: MSPCreate,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Crear proveedores es una facultad del operador de la plataforma."""
    require_platform_operator(db_gov, usuario)
    
    # Generar ID único
    msp_id = f"msp_{uuid.uuid4().hex[:12]}"
    
    nuevo_msp = MSP(
        msp_id=msp_id,
        nombre=body.nombre
    )
    
    db.add(nuevo_msp)
    db.commit()
    db.refresh(nuevo_msp)
    
    return MSPResponse(
        msp_id=nuevo_msp.msp_id,
        nombre=nuevo_msp.nombre,
        total_condominios=0
    )


@router.put("/{msp_id}/admins/{usuario_id}")
def asignar_admin_msp(
    msp_id: str, usuario_id: str,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
):
    require_platform_operator(db_gov, usuario)
    if not db.query(MSP).filter_by(msp_id=msp_id).first():
        raise HTTPException(404, "Proveedor no encontrado")
    target = db.query(Usuario).filter_by(usuario_id=usuario_id).first()
    if not target:
        raise HTTPException(404, "Usuario no encontrado")
    if target.rol != "MSP_ADMIN":
        raise HTTPException(400, "El usuario debe tener rol MSP_ADMIN")
    membership = db.query(MSPMembership).filter_by(usuario_id=usuario_id, msp_id=msp_id).first()
    if not membership:
        membership = MSPMembership(usuario_id=usuario_id, msp_id=msp_id)
        db.add(membership)
    membership.estado = "activo"
    membership.revoked_at = None
    db.commit()
    return {"msp_id": msp_id, "usuario_id": usuario_id, "estado": "activo"}


@router.delete("/{msp_id}/admins/{usuario_id}")
def revocar_admin_msp(
    msp_id: str, usuario_id: str,
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),
):
    from datetime import datetime
    require_platform_operator(db_gov, usuario)
    membership = db.query(MSPMembership).filter_by(usuario_id=usuario_id, msp_id=msp_id).first()
    if not membership:
        raise HTTPException(404, "Membresía no encontrada")
    membership.estado = "revocado"
    membership.revoked_at = datetime.utcnow()
    db.commit()
    return {"msp_id": msp_id, "usuario_id": usuario_id, "estado": "revocado"}
