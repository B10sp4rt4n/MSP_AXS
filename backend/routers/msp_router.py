from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import uuid

from backend.db.core import get_core_db, MSP, Condominio, Usuario
from backend.core.auth.dependencies import get_current_user

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
    usuario: Usuario = Depends(get_current_user)
):
    """Lista todos los MSPs."""
    if usuario.rol not in ["MSP_ADMIN", "ADMIN"]:
        raise HTTPException(403, detail="Requiere rol MSP_ADMIN")
    
    msps = db.query(MSP).all()
    
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
    usuario: Usuario = Depends(get_current_user)
):
    """Crea un nuevo MSP."""
    if usuario.rol not in ["MSP_ADMIN", "ADMIN"]:
        raise HTTPException(403, detail="Requiere rol MSP_ADMIN")
    
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
