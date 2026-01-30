"""
Test rápido de subida a Cloudinary
==================================

Prueba la subida de una imagen de prueba a Cloudinary.
"""

from dotenv import load_dotenv
load_dotenv()

from backend.utils.cloudinary_service import CloudinaryService
from PIL import Image
import io

def crear_imagen_prueba():
    """Crea una imagen de prueba 300x300 con texto."""
    img = Image.new('RGB', (300, 300), color='#3498db')
    
    # Convertir a bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes.read()

def main():
    print("🚀 TEST DE CLOUDINARY - Subida de Imagen")
    print("=" * 60)
    
    # 1. Inicializar servicio
    print("\n1️⃣  Inicializando CloudinaryService...")
    service = CloudinaryService()
    print(f"   ✅ Cloud Name: {service.cloud_name}")
    
    # 2. Crear imagen de prueba
    print("\n2️⃣  Creando imagen de prueba...")
    img_bytes = crear_imagen_prueba()
    print(f"   ✅ Imagen creada: {len(img_bytes)} bytes")
    
    # 3. Subir a Cloudinary
    print("\n3️⃣  Subiendo a Cloudinary...")
    resultado = service.upload_evidencia(
        file_bytes=img_bytes,
        filename="test_image.jpg",
        folder="tests",
        metadata={
            "test": "true",
            "timestamp": "2026-01-30",
            "tipo": "imagen_prueba"
        }
    )
    
    print(f"   ✅ Subida exitosa!")
    print(f"\n📋 Resultado:")
    print(f"   • Public ID: {resultado['public_id']}")
    print(f"   • Formato: {resultado['format']}")
    print(f"   • Dimensiones: {resultado['width']}x{resultado['height']}")
    print(f"   • Tamaño: {resultado.get('bytes', 0) / 1024:.2f} KB")
    print(f"\n🔗 URLs:")
    print(f"   • Original: {resultado['secure_url']}")
    
    # 4. Generar URL con transformaciones
    print("\n4️⃣  Generando transformaciones...")
    public_id = resultado['public_id']
    
    # Thumbnail 200x200
    thumb_url = service.get_url_with_transformations(
        public_id=public_id,
        width=200,
        height=200,
        crop="fill"
    )
    print(f"   • Thumbnail (200x200): {thumb_url}")
    
    # Optimizada para web
    web_url = service.get_url_with_transformations(
        public_id=public_id,
        quality=80,
        format="auto"
    )
    print(f"   • Web optimizada: {web_url}")
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO - Cloudinary funcional")
    print("\n📝 Puedes verificar la imagen en:")
    print(f"   https://console.cloudinary.com/console/c-{service.cloud_name}/media_library")
    
if __name__ == "__main__":
    main()
