"""
Router mejorado de Evidencias con soporte para Cloudinary
==========================================================

FASE 1: Sistema consolidado de evidencias fotográficas.

Endpoints disponibles:
----------------------

1. POST /evidencias/entrada/{visita_id}
   - Sube evidencias al momento de entrada del visitante
   - Fotos: visitante, INE (frente/reverso), placas, vehículo, documentos
   - Almacenamiento: Cloudinary (producción) o local (desarrollo)
   - Requiere rol: GUARDIA

2. POST /evidencias/salida/{visita_id}
   - Sube evidencias al momento de salida del visitante
   - Fotos: visitante saliendo, estado del vehículo
   - Requiere rol: GUARDIA

3. GET /evidencias/visita/{visita_id}
   - Obtiene todas las evidencias de una visita específica
   - Retorna URLs de Cloudinary con transformaciones disponibles
   - Requiere rol: GUARDIA, ADMIN_CONDOMINIO, MSP_ADMIN

4. GET /evidencias/visita/{visita_id}/thumbnails
   - Obtiene thumbnails (200x200) de todas las evidencias
   - Optimizado para listados y previews
   - Transformación on-the-fly por Cloudinary

5. DELETE /evidencias/{evidencia_id}
   - Elimina una evidencia específica
   - Borra de Cloudinary y marca como eliminada en BD
   - Requiere rol: MSP_ADMIN, ADMIN_CONDOMINIO

Configuración requerida:
------------------------
Variables de entorno:
    USE_CLOUDINARY=true  # false para desarrollo local
    CLOUDINARY_CLOUD_NAME=tu-cloud-name
    CLOUDINARY_API_KEY=tu-api-key
    CLOUDINARY_API_SECRET=tu-api-secret
    MAX_UPLOAD_SIZE_MB=15  # Tamaño máximo por archivo

Uso desde frontend:
-------------------
```javascript
// Subir foto de visitante en entrada
const formData = new FormData();
formData.append('foto_visitante', fotoFile);
formData.append('ine_frente', ineFrenteFile);
formData.append('placas', placasFile);

const response = await fetch('/evidencias/entrada/vis_123', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
});

// Obtener evidencias con thumbnails
const evidencias = await fetch('/evidencias/visita/vis_123/thumbnails', {
    headers: { 'Authorization': `Bearer ${token}` }
});
```
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from ..core.dependencies import get_db
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from ..services.evidencia_service import guardar_evidencias_opcionales
from ..utils.cloudinary_service import get_cloudinary_service
from backend.db.core import Usuario, Evidencia

logger = logging.getLogger(__name__)
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
    usuario: Usuario = Depends(get_current_user),
):
    """
    📸 Subir evidencias fotográficas al momento de entrada.
    
    - Todas las fotos son opcionales (el guardia decide cuáles tomar)
    - Se suben a Cloudinary con organización jerárquica
    - Se registran en BD con URLs y metadatos
    - Hash SHA256 para verificación de integridad
    
    Rol requerido: GUARDIA
    """
    verificar_rol(usuario, ["GUARDIA"])

    archivos = {
        "visitante": foto_visitante,
        "ine_frente": ine_frente,
        "ine_reverso": ine_reverso,
        "placas": placas,
        "vehiculo": vehiculo,
        "documento": documento,
    }

    try:
        registros = guardar_evidencias_opcionales(
            db,
            visita_id=visita_id,
            guardia_id=usuario.usuario_id,
            categoria="entrada",
            archivos=archivos,
        )
        
        # Construir respuesta con URLs de Cloudinary
        evidencias = []
        for r in registros:
            evidencias.append({
                "evidencia_id": r.evidencia_id,
                "sub_tipo": r.sub_tipo,
                "url": r.archivo_url,
                "metadata": r.metadata_json
            })

        return {
            "status": "ok",
            "message": f"✅ {len(registros)} evidencias guardadas",
            "evidencias": evidencias
        }
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error al guardar evidencias: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar evidencias"
        )


@router.post("/salida/{visita_id}")
def evidencias_salida(
    visita_id: str,
    foto_visitante: UploadFile | None = File(None),
    vehiculo: UploadFile | None = File(None),
    notas: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    📸 Subir evidencias fotográficas al momento de salida.
    
    Rol requerido: GUARDIA
    """
    verificar_rol(usuario, ["GUARDIA"])

    archivos = {
        "visitante_salida": foto_visitante,
        "vehiculo_salida": vehiculo,
    }

    metadata_extra = {}
    if notas:
        metadata_extra["notas_salida"] = notas

    try:
        registros = guardar_evidencias_opcionales(
            db,
            visita_id=visita_id,
            guardia_id=usuario.usuario_id,
            categoria="salida",
            archivos=archivos,
            metadata_extra=metadata_extra,
        )
        
        evidencias = []
        for r in registros:
            evidencias.append({
                "evidencia_id": r.evidencia_id,
                "sub_tipo": r.sub_tipo,
                "url": r.archivo_url,
                "metadata": r.metadata_json
            })

        return {
            "status": "ok",
            "message": f"✅ {len(registros)} evidencias de salida guardadas",
            "evidencias": evidencias
        }
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error al guardar evidencias de salida: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar evidencias"
        )


@router.get("/visita/{visita_id}")
def obtener_evidencias_visita(
    visita_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    📋 Obtener todas las evidencias de una visita específica.
    
    Retorna URLs completas (full resolution) de Cloudinary.
    
    Roles permitidos: GUARDIA, ADMIN_CONDOMINIO, MSP_ADMIN
    """
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO", "MSP_ADMIN"])
    
    # Obtener evidencias de la base de datos
    evidencias_db = (
        db.query(Evidencia)
        .filter(Evidencia.visita_id == visita_id)
        .order_by(Evidencia.categoria, Evidencia.sub_tipo)
        .all()
    )
    
    if not evidencias_db:
        return {
            "visita_id": visita_id,
            "total": 0,
            "evidencias": []
        }
    
    # Formatear respuesta
    evidencias = []
    for ev in evidencias_db:
        evidencias.append({
            "evidencia_id": ev.evidencia_id,
            "categoria": ev.categoria,
            "sub_tipo": ev.sub_tipo,
            "url": ev.archivo_url,
            "hash_sha256": ev.hash_sha256,
            "metadata": ev.metadata_json,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        })
    
    return {
        "visita_id": visita_id,
        "total": len(evidencias),
        "evidencias": evidencias
    }


@router.get("/visita/{visita_id}/thumbnails")
def obtener_thumbnails_visita(
    visita_id: str,
    size: int = 200,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    🖼️ Obtener thumbnails de todas las evidencias de una visita.
    
    Cloudinary genera las imágenes redimensionadas on-the-fly.
    Ideal para listados y previews en la UI.
    
    Args:
        visita_id: ID de la visita
        size: Tamaño del thumbnail (default: 200x200 píxeles)
    
    Roles permitidos: GUARDIA, ADMIN_CONDOMINIO, MSP_ADMIN
    """
    verificar_rol(usuario, ["GUARDIA", "ADMIN_CONDOMINIO", "MSP_ADMIN"])
    
    # Obtener evidencias de la base de datos
    evidencias_db = (
        db.query(Evidencia)
        .filter(Evidencia.visita_id == visita_id)
        .order_by(Evidencia.categoria, Evidencia.sub_tipo)
        .all()
    )
    
    if not evidencias_db:
        return {
            "visita_id": visita_id,
            "total": 0,
            "thumbnails": []
        }
    
    # Generar URLs de thumbnails usando Cloudinary
    thumbnails = []
    
    try:
        cloudinary_service = get_cloudinary_service()
        
        for ev in evidencias_db:
            # Extraer public_id de Cloudinary si existe
            public_id = None
            if ev.metadata_json and "cloudinary_public_id" in ev.metadata_json:
                public_id = ev.metadata_json["cloudinary_public_id"]
            
            # Si la evidencia está en Cloudinary, generar thumbnail
            if public_id:
                thumbnail_url = cloudinary_service.get_url_with_transformations(
                    public_id=public_id,
                    width=size,
                    height=size,
                    crop="thumb",
                    quality=80,
                    format="auto"
                )
            else:
                # Si es almacenamiento local, usar URL original
                thumbnail_url = ev.archivo_url
            
            thumbnails.append({
                "evidencia_id": ev.evidencia_id,
                "categoria": ev.categoria,
                "sub_tipo": ev.sub_tipo,
                "thumbnail_url": thumbnail_url,
                "original_url": ev.archivo_url,
            })
    
    except Exception as e:
        logger.warning(f"⚠️ Cloudinary no disponible, usando URLs originales: {e}")
        # Fallback: usar URLs originales
        for ev in evidencias_db:
            thumbnails.append({
                "evidencia_id": ev.evidencia_id,
                "categoria": ev.categoria,
                "sub_tipo": ev.sub_tipo,
                "thumbnail_url": ev.archivo_url,
                "original_url": ev.archivo_url,
            })
    
    return {
        "visita_id": visita_id,
        "total": len(thumbnails),
        "size": f"{size}x{size}",
        "thumbnails": thumbnails
    }


@router.delete("/{evidencia_id}")
def eliminar_evidencia(
    evidencia_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    🗑️ Eliminar una evidencia específica.
    
    - Elimina el archivo de Cloudinary
    - Marca como eliminada en la base de datos (soft delete)
    - Solo administradores pueden eliminar evidencias
    
    Roles permitidos: MSP_ADMIN, ADMIN_CONDOMINIO
    """
    verificar_rol(usuario, ["MSP_ADMIN", "ADMIN_CONDOMINIO"])
    
    # Buscar evidencia
    evidencia = db.query(Evidencia).filter(Evidencia.evidencia_id == evidencia_id).first()
    
    if not evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada"
        )
    
    # Intentar eliminar de Cloudinary si aplica
    deleted_from_cloudinary = False
    if evidencia.metadata_json and "cloudinary_public_id" in evidencia.metadata_json:
        try:
            cloudinary_service = get_cloudinary_service()
            public_id = evidencia.metadata_json["cloudinary_public_id"]
            
            # Determinar tipo de recurso
            resource_type = evidencia.metadata_json.get("resource_type", "image")
            
            deleted_from_cloudinary = cloudinary_service.delete_evidencia(
                public_id=public_id,
                resource_type=resource_type
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo eliminar de Cloudinary: {e}")
    
    # Eliminar de base de datos (o soft delete)
    try:
        db.delete(evidencia)
        db.commit()
        
        return {
            "status": "ok",
            "message": "✅ Evidencia eliminada",
            "evidencia_id": evidencia_id,
            "deleted_from_cloudinary": deleted_from_cloudinary
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error al eliminar evidencia: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar evidencia"
        )
