from sqlalchemy.orm import Session
from ..db.models import Evidencia
from ..utils.file_storage import guardar_archivo
from ..utils.hash_tools import calcular_hash_sha256
import uuid
from typing import Optional
import os

# Max upload size in MB (fallback to 15MB)
_MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
_MAX_UPLOAD_BYTES = _MAX_UPLOAD_MB * 1024 * 1024


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

        # Validate size
        if isinstance(contenido, (bytes, bytearray)) and len(contenido) > _MAX_UPLOAD_BYTES:
            # abort the whole batch
            raise ValueError(f"Archivo '{filename}' excede tamaño máximo de {_MAX_UPLOAD_MB} MB")

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
        # refresh added registros
        for r in registros:
            try:
                db.refresh(r)
            except Exception:
                pass
    except Exception:
        db.rollback()
        raise

    return registros
