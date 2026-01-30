from sqlalchemy.orm import Session
from backend.db.core import Evidencia
from ..utils.cloudinary_service import get_cloudinary_service
from ..utils.hash_tools import calcular_hash_sha256
import uuid
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

# Max upload size in MB (fallback to 15MB)
_MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
_MAX_UPLOAD_BYTES = _MAX_UPLOAD_MB * 1024 * 1024

# Feature flag: usar Cloudinary o almacenamiento local
USE_CLOUDINARY = os.getenv("USE_CLOUDINARY", "true").lower() == "true"


def guardar_evidencias_opcionales(
    db: Session,
    visita_id: str,
    guardia_id: str,
    categoria: str,
    archivos: dict,
    metadata_extra: Optional[dict] = None,
):
    """
    Guarda evidencias usando Cloudinary (producción) o almacenamiento local (desarrollo).
    
    Para usar almacenamiento local (no recomendado para producción):
        USE_CLOUDINARY=false
    
    Cloudinary requiere variables de entorno:
        CLOUDINARY_CLOUD_NAME=tu-cloud-name
        CLOUDINARY_API_KEY=tu-api-key
        CLOUDINARY_API_SECRET=tu-api-secret
    """
    registros = []
    
    # Inicializar servicio de Cloudinary si está habilitado
    cloudinary_service = None
    if USE_CLOUDINARY:
        try:
            cloudinary_service = get_cloudinary_service()
            logger.info(f"☁️ Usando Cloudinary para evidencias (visita: {visita_id})")
        except Exception as e:
            logger.warning(f"⚠️ Cloudinary no disponible, usando almacenamiento local: {e}")
            USE_CLOUDINARY_LOCAL = False
    else:
        logger.info(f"💾 Usando almacenamiento local para evidencias (visita: {visita_id})")

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
            raise ValueError(f"Archivo '{filename}' excede tamaño máximo de {_MAX_UPLOAD_MB} MB")

        # Calcular hash para verificación de integridad
        hash_sha = calcular_hash_sha256(contenido)
        
        # Subir a Cloudinary o guardar localmente
        try:
            if cloudinary_service:
                # 📤 CLOUDINARY: Subir a la nube
                folder = f"evidencias/{categoria}/{sub_tipo}"
                metadata = {
                    "visita_id": visita_id,
                    "guardia_id": guardia_id,
                    "tipo": categoria,
                    "sub_tipo": sub_tipo,
                    "hash_sha256": hash_sha
                }
                
                # Agregar metadatos extra si existen
                if metadata_extra:
                    metadata.update(metadata_extra)
                
                # Subir a Cloudinary con organización jerárquica
                result = cloudinary_service.upload_evidencia(
                    file_bytes=contenido,
                    filename=filename,
                    folder=folder,
                    metadata=metadata,
                    public_id=None,  # Cloudinary genera ID único
                    max_dimension=2048,  # Limitar resolución
                    quality=80  # Compresión inteligente
                )
                
                # Usar URL segura de Cloudinary
                archivo_url = result["secure_url"]
                cloudinary_public_id = result["public_id"]
                
                # Construir metadata_json con información de Cloudinary
                metadata_json = {
                    "filename": filename,
                    "cloudinary_public_id": cloudinary_public_id,
                    "cloudinary_asset_id": result.get("asset_id"),
                    "width": result.get("width"),
                    "height": result.get("height"),
                    "format": result.get("format"),
                    "bytes": result.get("bytes"),
                    "uploaded_at": result.get("created_at"),
                }
                
                if metadata_extra:
                    metadata_json.update(metadata_extra)
                
                logger.info(f"✅ Evidencia subida a Cloudinary: {cloudinary_public_id}")
                
            else:
                # 💾 LOCAL: Fallback a almacenamiento local
                from ..utils.file_storage import guardar_archivo
                archivo_url = guardar_archivo(filename, contenido)
                metadata_json = metadata_extra or {"filename": filename}
                logger.info(f"💾 Evidencia guardada localmente: {archivo_url}")
                
        except Exception as e:
            logger.error(f"❌ Error al guardar evidencia {sub_tipo}: {str(e)}")
            # Si falla Cloudinary, intentar guardar localmente como respaldo
            if cloudinary_service:
                logger.warning("⚠️ Intentando guardar localmente como respaldo...")
                try:
                    from ..utils.file_storage import guardar_archivo
                    archivo_url = guardar_archivo(filename, contenido)
                    metadata_json = {
                        "filename": filename,
                        "cloudinary_error": str(e),
                        "fallback": "local_storage"
                    }
                    if metadata_extra:
                        metadata_json.update(metadata_extra)
                    logger.info(f"💾 Evidencia guardada localmente (respaldo): {archivo_url}")
                except Exception as fallback_error:
                    logger.error(f"❌ Falló respaldo local: {str(fallback_error)}")
                    raise
            else:
                raise

        # Crear registro en base de datos
        evidencia = Evidencia(
            evidencia_id=str(uuid.uuid4()),
            visita_id=visita_id,
            guardia_id=guardia_id,
            categoria=categoria,  # entrada / salida
            sub_tipo=sub_tipo,  # visitante, ine_frente, placas, etc.
            archivo_url=archivo_url,
            hash_sha256=hash_sha,
            metadata_json=metadata_json,
        )
        db.add(evidencia)
        registros.append(evidencia)

    # Commit transaccional
    try:
        db.commit()
        # refresh added registros
        for r in registros:
            try:
                db.refresh(r)
            except Exception:
                pass
        logger.info(f"✅ {len(registros)} evidencias registradas en base de datos")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error al guardar en base de datos: {str(e)}")
        raise

    return registros
