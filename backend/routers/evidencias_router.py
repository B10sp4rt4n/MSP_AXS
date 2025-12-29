"""Router de Evidencias - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from ..core.dependencies import get_db
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from ..services.evidencia_service import guardar_evidencias_opcionales
from ..db.models import Usuario

router = APIRouter(prefix="/evidencias", tags=["Evidencias"]) 


@router.post("/entrada/{visita_id}")
def evidencias_entrada(
    visita_id: str,
    foto_visitante: UploadFile | None = File(None),
    ine_frente: UploadFile | None = File(None),
    ine_reverso: UploadFile | None = File(None),
    placas: UploadFile | None = File(None),
    vehiculo: UploadFile | None = File(None),
    documento: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["GUARDIA"])

    archivos = {
        "visitante": foto_visitante,
        "ine_frente": ine_frente,
        "ine_reverso": ine_reverso,
        "placas": placas,
        "vehiculo": vehiculo,
        "documento": documento,
    }

    registros = guardar_evidencias_opcionales(
        db,
        visita_id=visita_id,
        guardia_id=usuario.usuario_id,
        categoria="entrada",
        archivos=archivos,
    )

    return {"status": "ok", "evidencias": len(registros)}
