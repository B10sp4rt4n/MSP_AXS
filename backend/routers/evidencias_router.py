"""Router de Evidencias - MIGRADO A AUP_SESSION"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, AccessLevel
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_visita
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from ..services.evidencia_service import guardar_evidencias_opcionales
from backend.db.core import Usuario

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
    db: Session = Depends(get_core_db),
    db_gov: Session = Depends(get_gov_db),
    usuario: Usuario = Depends(get_current_user),  # AUP_SESSION validada
):
    verificar_rol(usuario, ["GUARDIA"])
    require_visita(db, db_gov, usuario, visita_id, AccessLevel.GUARDIA)

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
