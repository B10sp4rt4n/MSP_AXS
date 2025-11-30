from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from ..core.dependencies import get_db, get_usuario_actual
from ..core.security import verificar_rol
from ..services.evidencia_service import guardar_evidencias_opcionales

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
    usuario = Depends(get_usuario_actual),
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
