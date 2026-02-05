"""
Servicio de gestión de imágenes con Cloudinary
===============================================

FASE 1: Sistema de evidencias consolidado con almacenamiento en la nube.

Ventajas vs almacenamiento local:
- ✅ URLs públicas con CDN global
- ✅ Transformaciones on-the-fly (resize, crop, calidad)
- ✅ Backup automático
- ✅ Metadatos y búsqueda
- ✅ No consume storage del servidor
- ✅ Escala automáticamente

Configuración requerida:
------------------------
Variables de entorno (agregar a .env o Railway):
    CLOUDINARY_CLOUD_NAME=tu-cloud-name
    CLOUDINARY_API_KEY=tu-api-key
    CLOUDINARY_API_SECRET=tu-api-secret
    CLOUDINARY_UPLOAD_PRESET=axs_evidencias  # Opcional

Instalación:
    pip install cloudinary

Uso básico:
-----------
```python
from backend.utils.cloudinary_service import CloudinaryService

service = CloudinaryService()

# Subir foto de visitante
result = service.upload_evidencia(
    file_bytes=foto_visitante.file.read(),
    filename="visitante_123.jpg",
    folder="visitantes",
    metadata={
        "visita_id": "vis_abc123",
        "tipo": "entrada",
        "guardia_id": "usr_456"
    }
)

# result = {
#     "public_id": "visitantes/visitante_123_xyz",
#     "secure_url": "https://res.cloudinary.com/.../visitante_123.jpg",
#     "asset_id": "abc123",
#     "width": 1920,
#     "height": 1080,
#     "format": "jpg"
# }
```

Categorías de evidencias:
--------------------------
- visitantes/entrada/{visita_id}/foto_principal
- visitantes/entrada/{visita_id}/ine_frente
- visitantes/entrada/{visita_id}/ine_reverso
- vehiculos/{visita_id}/placas
- vehiculos/{visita_id}/foto_vehiculo
- documentos/{visita_id}/documento_adicional
- salidas/{visita_id}/foto_salida

Optimizaciones automáticas:
----------------------------
- Compresión inteligente (calidad 80%, formato auto)
- Límite de dimensiones (max 2048x2048)
- Conversión a WebP para navegadores modernos
- Thumbnails automáticos
"""

import os
import logging
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime
import mimetypes

# Importación condicional (si no está instalado, dará error descriptivo)
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    from cloudinary.exceptions import Error as CloudinaryError
except ImportError:
    raise ImportError(
        "Cloudinary no está instalado. Ejecuta: pip install cloudinary"
    )

logger = logging.getLogger(__name__)


class CloudinaryService:
    """Servicio centralizado para gestión de evidencias fotográficas con Cloudinary."""
    
    def __init__(self):
        """Inicializa configuración de Cloudinary desde variables de entorno."""
        self.cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        self.api_key = os.getenv("CLOUDINARY_API_KEY")
        self.api_secret = os.getenv("CLOUDINARY_API_SECRET")
        self.upload_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET", "axs_evidencias")
        
        # Validar configuración
        if not all([self.cloud_name, self.api_key, self.api_secret]):
            raise ValueError(
                "Cloudinary no configurado. Define las variables de entorno:\n"
                "  - CLOUDINARY_CLOUD_NAME\n"
                "  - CLOUDINARY_API_KEY\n"
                "  - CLOUDINARY_API_SECRET"
            )
        
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True  # Siempre HTTPS
        )
        
        logger.info(f"✅ Cloudinary configurado: {self.cloud_name}")
    
    def upload_evidencia(
        self,
        file_bytes: bytes,
        filename: str,
        folder: str = "evidencias",
        metadata: Optional[Dict[str, Any]] = None,
        public_id: Optional[str] = None,
        max_dimension: int = 2048,
        quality: int = 80
    ) -> Dict[str, Any]:
        """
        Sube una imagen/documento a Cloudinary.
        
        Args:
            file_bytes: Contenido del archivo (bytes)
            filename: Nombre original del archivo (para detectar tipo MIME)
            folder: Carpeta en Cloudinary (ej: "visitantes", "vehiculos")
            metadata: Metadatos personalizados (visita_id, guardia_id, etc.)
            public_id: ID personalizado (si no se provee, Cloudinary genera uno)
            max_dimension: Máxima dimensión (ancho/alto) en píxeles
            quality: Calidad de compresión (1-100)
        
        Returns:
            Dict con información del archivo subido:
                - public_id: Identificador único en Cloudinary
                - secure_url: URL HTTPS del archivo
                - asset_id: ID interno de Cloudinary
                - width, height: Dimensiones de la imagen
                - format: Formato del archivo (jpg, png, pdf, etc.)
                - bytes: Tamaño en bytes
                - created_at: Timestamp de creación
        
        Raises:
            CloudinaryError: Si la subida falla
            ValueError: Si el archivo es inválido
        """
        try:
            # Detectar tipo de archivo
            mime_type, _ = mimetypes.guess_type(filename)
            resource_type = "image"  # Por defecto
            
            if mime_type:
                if mime_type.startswith("video/"):
                    resource_type = "video"
                elif mime_type == "application/pdf" or not mime_type.startswith("image/"):
                    resource_type = "raw"
            
            # Preparar opciones de subida
            upload_options = {
                "folder": folder,
                "resource_type": resource_type,
                "use_filename": True,
                "unique_filename": True,  # Evita colisiones de nombres
                "overwrite": False,  # No sobreescribir archivos existentes
                "invalidate": True,  # Invalida CDN cache si se reemplaza
            }
            
            # Solo aplicar transformaciones a imágenes
            if resource_type == "image":
                upload_options.update({
                    "quality": quality,
                    "fetch_format": "auto",  # WebP si el navegador lo soporta
                    "transformation": [
                        {
                            "width": max_dimension,
                            "height": max_dimension,
                            "crop": "limit"  # No exceder dimensiones max
                        }
                    ]
                })
            
            # Public ID personalizado (opcional)
            if public_id:
                upload_options["public_id"] = public_id
            
            # Agregar contexto (metadatos estructurados)
            if metadata:
                # Cloudinary solo acepta strings en context
                context_str = "|".join(f"{k}={v}" for k, v in metadata.items())
                upload_options["context"] = context_str
                
                # También agregar como tags para búsqueda fácil
                tags = []
                if "visita_id" in metadata:
                    tags.append(f"visita:{metadata['visita_id']}")
                if "guardia_id" in metadata:
                    tags.append(f"guardia:{metadata['guardia_id']}")
                if "tipo" in metadata:
                    tags.append(f"tipo:{metadata['tipo']}")
                
                if tags:
                    upload_options["tags"] = tags
            
            # Subir a Cloudinary
            logger.info(f"📤 Subiendo {filename} a Cloudinary/{folder}...")
            result = cloudinary.uploader.upload(file_bytes, **upload_options)
            
            # Extraer información relevante
            response = {
                "public_id": result.get("public_id"),
                "secure_url": result.get("secure_url"),
                "asset_id": result.get("asset_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "bytes": result.get("bytes"),
                "created_at": result.get("created_at"),
                "resource_type": result.get("resource_type"),
                "type": result.get("type"),  # upload, private, authenticated
            }
            
            logger.info(f"✅ Archivo subido: {response['public_id']}")
            logger.debug(f"   URL: {response['secure_url']}")
            
            return response
            
        except CloudinaryError as e:
            logger.error(f"❌ Error al subir a Cloudinary: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado: {str(e)}")
            raise ValueError(f"No se pudo subir el archivo: {str(e)}")
    
    def delete_evidencia(self, public_id: str, resource_type: str = "image") -> bool:
        """
        Elimina una evidencia de Cloudinary.
        
        Args:
            public_id: ID del recurso en Cloudinary
            resource_type: Tipo de recurso ("image", "video", "raw")
        
        Returns:
            True si se eliminó correctamente, False si no existía
        """
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
                invalidate=True
            )
            
            if result.get("result") == "ok":
                logger.info(f"🗑️ Evidencia eliminada: {public_id}")
                return True
            elif result.get("result") == "not found":
                logger.warning(f"⚠️ Evidencia no encontrada: {public_id}")
                return False
            else:
                logger.error(f"❌ Error al eliminar: {result}")
                return False
                
        except CloudinaryError as e:
            logger.error(f"❌ Error al eliminar de Cloudinary: {str(e)}")
            raise
    
    def get_url_with_transformations(
        self,
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: str = "fill",
        quality: int = 80,
        format: str = "auto"
    ) -> str:
        """
        Genera URL con transformaciones on-the-fly.
        
        Útil para thumbnails, previews, diferentes tamaños.
        
        Args:
            public_id: ID del recurso en Cloudinary
            width: Ancho deseado en píxeles
            height: Alto deseado en píxeles
            crop: Modo de recorte ("fill", "fit", "limit", "scale", "thumb")
            quality: Calidad de compresión (1-100)
            format: Formato de salida ("auto", "jpg", "png", "webp")
        
        Returns:
            URL con transformaciones aplicadas
        
        Ejemplos:
            # Thumbnail 200x200
            url = service.get_url_with_transformations(
                "visitantes/foto_123",
                width=200,
                height=200,
                crop="thumb"
            )
            
            # Preview 800px de ancho, altura proporcional
            url = service.get_url_with_transformations(
                "vehiculos/placa_456",
                width=800,
                crop="scale"
            )
        """
        try:
            transformation = {
                "quality": quality,
                "fetch_format": format
            }
            
            if width:
                transformation["width"] = width
            if height:
                transformation["height"] = height
            if width or height:
                transformation["crop"] = crop
            
            url = cloudinary.CloudinaryImage(public_id).build_url(
                **transformation,
                secure=True
            )
            
            return url
            
        except Exception as e:
            logger.error(f"❌ Error al generar URL: {str(e)}")
            raise
    
    def search_evidencias(
        self,
        visita_id: Optional[str] = None,
        guardia_id: Optional[str] = None,
        tipo: Optional[str] = None,
        folder: Optional[str] = None,
        max_results: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Busca evidencias por metadatos.
        
        Args:
            visita_id: Filtrar por ID de visita
            guardia_id: Filtrar por ID de guardia
            tipo: Filtrar por tipo (entrada, salida)
            folder: Filtrar por carpeta
            max_results: Máximo de resultados a retornar
        
        Returns:
            Lista de recursos que coinciden con los filtros
        """
        try:
            # Construir expresión de búsqueda
            expressions = []
            
            if folder:
                expressions.append(f"folder:{folder}/*")
            
            if visita_id:
                expressions.append(f"tags=visita:{visita_id}")
            
            if guardia_id:
                expressions.append(f"tags=guardia:{guardia_id}")
            
            if tipo:
                expressions.append(f"tags=tipo:{tipo}")
            
            if not expressions:
                # Búsqueda sin filtros (todas las evidencias)
                expression = "resource_type:image OR resource_type:raw"
            else:
                expression = " AND ".join(expressions)
            
            logger.info(f"🔍 Buscando evidencias: {expression}")
            
            result = cloudinary.Search().expression(expression).max_results(max_results).execute()
            
            resources = result.get("resources", [])
            logger.info(f"✅ Encontradas {len(resources)} evidencias")
            
            return resources
            
        except CloudinaryError as e:
            logger.error(f"❌ Error al buscar en Cloudinary: {str(e)}")
            raise


# Instancia singleton (opcional, para reutilizar)
_cloudinary_service = None


def get_cloudinary_service() -> CloudinaryService:
    """
    Obtiene instancia singleton del servicio de Cloudinary.
    
    Útil para dependency injection en routers:
    
    ```python
    from backend.utils.cloudinary_service import get_cloudinary_service
    
    @router.post("/evidencias/entrada")
    def subir_evidencia(
        file: UploadFile,
        cloudinary: CloudinaryService = Depends(get_cloudinary_service)
    ):
        result = cloudinary.upload_evidencia(
            file_bytes=file.file.read(),
            filename=file.filename,
            folder="visitantes"
        )
        return {"url": result["secure_url"]}
    ```
    """
    global _cloudinary_service
    if _cloudinary_service is None:
        _cloudinary_service = CloudinaryService()
    return _cloudinary_service
