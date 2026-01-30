"""
Script de Verificación de Cloudinary
====================================

Verifica que la configuración de Cloudinary esté correcta y funcional.

Ejecutar:
    python scripts/verify_cloudinary.py

Requisitos:
    - Variables de entorno configuradas (CLOUDINARY_*)
    - Dependencia cloudinary instalada
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para poder importar módulos
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

def verificar_variables_entorno():
    """Verifica que las variables de entorno necesarias estén configuradas."""
    print("🔍 Verificando variables de entorno...")
    
    required_vars = [
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == "your_cloud_name" or value == "your_api_secret_here":
            missing_vars.append(var)
        else:
            print(f"  ✅ {var}: {'*' * 10}")
    
    if missing_vars:
        print(f"\n❌ Faltan variables de entorno: {', '.join(missing_vars)}")
        print("\n📖 Guía de configuración:")
        print("  1. Crea una cuenta gratuita en https://cloudinary.com/users/register/free")
        print("  2. Ve a Dashboard → Settings → Access Keys")
        print("  3. Agrega las variables a tu .env:")
        print("\n  CLOUDINARY_CLOUD_NAME=tu_cloud_name_aqui")
        print("  CLOUDINARY_API_KEY=123456789012345")
        print("  CLOUDINARY_API_SECRET=tu_api_secret_aqui")
        return False
    
    print("  ✅ Todas las variables configuradas")
    return True

def verificar_instalacion():
    """Verifica que la librería cloudinary esté instalada."""
    print("\n🔍 Verificando instalación de cloudinary...")
    
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
        version = getattr(cloudinary, '__version__', 'unknown')
        print(f"  ✅ cloudinary instalado (versión {version})")
        return True
    except ImportError as e:
        print(f"  ❌ cloudinary no está instalado: {e}")
        print("\n📦 Para instalar:")
        print("  pip install cloudinary")
        return False

def verificar_conexion():
    """Verifica la conexión con Cloudinary."""
    print("\n🔍 Verificando conexión con Cloudinary...")
    
    try:
        from backend.utils.cloudinary_service import CloudinaryService
        
        service = CloudinaryService()
        print("  ✅ Servicio inicializado correctamente")
        print(f"  ✅ Cloud Name: {service.cloud_name}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error al inicializar servicio: {e}")
        return False

def probar_ping():
    """Hace un ping a la API de Cloudinary."""
    print("\n🔍 Probando ping a Cloudinary API...")
    
    try:
        import cloudinary.api
        
        # Configurar cloudinary
        import cloudinary
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET")
        )
        
        # Hacer ping
        result = cloudinary.api.ping()
        
        if result.get("status") == "ok":
            print("  ✅ Ping exitoso - Cloudinary está respondiendo")
            return True
        else:
            print(f"  ❌ Ping falló: {result}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error en ping: {e}")
        return False

def listar_recursos():
    """Lista los primeros recursos en Cloudinary (si existen)."""
    print("\n🔍 Listando recursos existentes...")
    
    try:
        import cloudinary.api
        
        result = cloudinary.api.resources(
            max_results=5,
            resource_type="image"
        )
        
        resources = result.get("resources", [])
        total = result.get("total_count", 0)
        
        if total == 0:
            print("  ℹ️  No hay imágenes aún (cuenta nueva)")
        else:
            print(f"  ✅ Encontradas {total} imágenes")
            print("\n  Primeras 5 imágenes:")
            for r in resources[:5]:
                print(f"    - {r.get('public_id')} ({r.get('format')}, {r.get('bytes')} bytes)")
        
        return True
        
    except Exception as e:
        print(f"  ⚠️  No se pudo listar recursos: {e}")
        return True  # No es error crítico

def verificar_cuota():
    """Verifica el uso de cuota del plan."""
    print("\n🔍 Verificando uso de cuota...")
    
    try:
        import cloudinary.api
        
        usage = cloudinary.api.usage()
        
        # Transformaciones
        transformations = usage.get("transformations", {})
        trans_used = transformations.get("usage", 0)
        trans_limit = transformations.get("limit", 0)
        
        # Storage
        storage = usage.get("storage", {})
        storage_used = storage.get("usage", 0)
        
        # Bandwidth
        bandwidth = usage.get("bandwidth", {})
        bandwidth_used = bandwidth.get("usage", 0)
        
        print(f"  📊 Plan: {usage.get('plan', 'free')}")
        print(f"  📊 Transformaciones: {trans_used}/{trans_limit}")
        print(f"  📊 Storage: {storage_used / (1024*1024):.2f} MB")
        print(f"  📊 Bandwidth: {bandwidth_used / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"  ⚠️  No se pudo obtener uso de cuota: {e}")
        return True  # No es error crítico

def main():
    """Función principal de verificación."""
    print("=" * 60)
    print("🚀 VERIFICACIÓN DE CLOUDINARY - MSP_AXS")
    print("=" * 60)
    
    checks = [
        ("Variables de entorno", verificar_variables_entorno),
        ("Instalación", verificar_instalacion),
        ("Conexión", verificar_conexion),
        ("Ping API", probar_ping),
        ("Recursos", listar_recursos),
        ("Cuota", verificar_cuota),
    ]
    
    passed = 0
    failed = 0
    
    for name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Error inesperado: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed}/{len(checks)} verificaciones exitosas")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ TODO CORRECTO - Cloudinary está listo para usar")
        print("\n📝 Próximos pasos:")
        print("  1. Integrar router en backend/main.py")
        print("  2. Crear formulario en frontend")
        print("  3. Probar subida de evidencia")
        return 0
    else:
        print(f"\n⚠️  {failed} verificaciones fallaron")
        print("📖 Ver la guía completa: docs/CLOUDINARY_SETUP.md")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
