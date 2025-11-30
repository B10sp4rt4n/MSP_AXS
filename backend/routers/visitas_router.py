from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..schemas.visita import VisitaCreate, VisitaResponse
from ..core.dependencies import get_db, get_usuario_actual
from ..core.security import verificar_rol
from ..services import visita_service

router = APIRouter(prefix="/visitas", tags=["Visitas"]) 


@router.post("/", response_model=VisitaResponse)
def crear_visita(
    data: VisitaCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO"])
    visita = visita_service.crear_visita(
        db, data, condominio_id=data.condominio_id, casa_unidad=data.casa_unidad
    )
    return visita
