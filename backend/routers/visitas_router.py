from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.dependencies import get_db, get_usuario_actual
from ..core.security import verificar_rol
from ..services import visita_service
from ..schemas.visita import VisitaCreate, VisitaResponse
from typing import List

router = APIRouter(prefix="/visitas", tags=["Visitas"])


# ---------------------------------------------------------
# Crear visita (solo Administración del condominio)
# ---------------------------------------------------------
@router.post("/", response_model=VisitaResponse)
def crear_visita(
    data: VisitaCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
    verificar_rol(usuario, ["ADMIN_CONDOMINIO"])
    visita = visita_service.crear_visita(
        db,
        data,
        condominio_id=data.condominio_id,
        casa_unidad=data.casa_unidad,
    )
    return visita


# ---------------------------------------------------------
# Listar visitas del residente
# ---------------------------------------------------------
@router.get("/mis-visitas", response_model=List[VisitaResponse])
def mis_visitas(
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_actual),
):
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
    usuario = Depends(get_usuario_actual),
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
    usuario = Depends(get_usuario_actual),
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
