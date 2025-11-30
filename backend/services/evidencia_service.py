from sqlalchemy.orm import Session
from ..db.models import Evidencia
from ..utils.file_storage import guardar_archivo
from ..utils.hash_tools import calcular_hash_sha256
import uuid
from typing import Optional


def guardar_evidencias_opcionales(
    db: Session,
    visita_id: str,
    guardia_id: str,
    categoria: str,
    archivos: dict,
    metadata_extra: Optional[dict] = None,
):
    registros = []

    for sub_tipo, archivo in archivos.items():
        if archivo is None:
            continue

        # archivo puede ser UploadFile de FastAPI o un objeto con .file
        if hasattr(archivo, "file"):
            contenido = archivo.file.read()
            filename = getattr(archivo, "filename", f"{uuid.uuid4().hex}.bin")
        else:
            # si se pasa un par (filename, bytes)
            try:
                filename, contenido = archivo
            except Exception:
                continue

        archivo_url = guardar_archivo(filename, contenido)
        hash_sha = calcular_hash_sha256(contenido)

        evidencia = Evidencia(
            evidencia_id=str(uuid.uuid4()),
            visita_id=visita_id,
            guardia_id=guardia_id,
            categoria=categoria,  # entrada / salida
            sub_tipo=sub_tipo,  # visitante, ine_frente, placas, etc.
            archivo_url=archivo_url,
            hash_sha256=hash_sha,
            metadata_json=metadata_extra or {"filename": filename},
        )
        db.add(evidencia)
        registros.append(evidencia)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return registros
