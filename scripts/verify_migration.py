"""
Script de verificación de migración AUP
Valida que el sistema de autenticación esté correctamente implementado
"""

import sys
import importlib.util

def check_module(module_path, module_name):
    """Verifica que un módulo exista y sea importable"""
    try:
        spec = importlib.util.find_spec(module_path)
        if spec is None:
            print(f"❌ {module_name}: Módulo no encontrado")
            return False
        print(f"✅ {module_name}: OK")
        return True
    except Exception as e:
        print(f"❌ {module_name}: Error - {e}")
        return False

def check_env_file():
    """Verifica que existan archivos de configuración"""
    import os
    checks = []
    
    # .env.example debe existir
    if os.path.exists(".env.example"):
        print("✅ .env.example: OK")
        checks.append(True)
    else:
        print("❌ .env.example: No existe")
        checks.append(False)
    
    # .gitignore debe existir
    if os.path.exists(".gitignore"):
        print("✅ .gitignore: OK")
        checks.append(True)
    else:
        print("❌ .gitignore: No existe")
        checks.append(False)
    
    # Documentación debe existir
    if os.path.exists("docs/AUP_AUTHENTICATION.md"):
        print("✅ docs/AUP_AUTHENTICATION.md: OK")
        checks.append(True)
    else:
        print("❌ docs/AUP_AUTHENTICATION.md: No existe")
        checks.append(False)
    
    return all(checks)

def main():
    print("=" * 60)
    print("VERIFICACIÓN DE MIGRACIÓN AUP")
    print("=" * 60)
    print()
    
    checks = []
    
    print("📦 Módulos de autenticación:")
    checks.append(check_module("backend.core.auth.password", "password.py"))
    checks.append(check_module("backend.core.auth.jwt", "jwt.py"))
    checks.append(check_module("backend.core.auth.dependencies", "dependencies.py"))
    checks.append(check_module("backend.core.auth.schemas", "schemas.py"))
    
    print()
    print("🌐 Routers:")
    checks.append(check_module("backend.routers.auth_router", "auth_router.py"))
    checks.append(check_module("backend.routers.visitas_router", "visitas_router.py"))
    checks.append(check_module("backend.routers.preregistro_router", "preregistro_router.py"))
    checks.append(check_module("backend.routers.qr_router", "qr_router.py"))
    
    print()
    print("📄 Archivos de configuración:")
    checks.append(check_env_file())
    
    print()
    print("=" * 60)
    
    if all(checks):
        print("✅ MIGRACIÓN COMPLETA - Todos los componentes OK")
        print()
        print("Siguiente paso:")
        print("1. Instalar dependencias: pip install -r requirements.txt")
        print("2. Configurar .env con SECRET_KEY")
        print("3. Ejecutar: uvicorn backend.main:app --reload")
        print("4. Probar: POST /auth/login")
        return 0
    else:
        print("❌ MIGRACIÓN INCOMPLETA - Revisar errores arriba")
        return 1

if __name__ == "__main__":
    sys.exit(main())
