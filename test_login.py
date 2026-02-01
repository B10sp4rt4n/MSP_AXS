#!/usr/bin/env python3
"""
Script de prueba para verificar login y preregistro
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Prueba el endpoint de login"""
    print("=" * 60)
    print("1. PROBANDO LOGIN")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "test@example.com", "password": "test123"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"\n✅ Login exitoso!")
        print(f"Token: {token[:50]}...")
        return token
    else:
        print(f"\n❌ Login falló")
        return None

def test_preregistro(token):
    """Prueba el endpoint de preregistro"""
    if not token:
        print("\n⚠️ No hay token, saltando prueba de preregistro")
        return
    
    print("\n" + "=" * 60)
    print("2. PROBANDO PREREGISTRO DE VISITA")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "nombre_visitante": "Juan Pérez",
        "tipo_visita": "PROVEEDOR",
        "fecha_esperada": "2026-02-01T10:00:00",
        "observaciones": "Prueba de preregistro desde script"
    }
    
    response = requests.post(
        f"{BASE_URL}/preregistro/crear",
        json=data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print(f"\n✅ Preregistro exitoso!")
    else:
        print(f"\n❌ Preregistro falló")

def test_cloudinary_status(token):
    """Verifica el estado de Cloudinary"""
    print("\n" + "=" * 60)
    print("3. VERIFICANDO CONFIGURACIÓN DE CLOUDINARY")
    print("=" * 60)
    
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    use_cloudinary = os.getenv("USE_CLOUDINARY", "false")
    
    print(f"CLOUDINARY_CLOUD_NAME: {cloud_name}")
    print(f"CLOUDINARY_API_KEY: {'***' + api_key[-4:] if api_key else 'NO CONFIGURADO'}")
    print(f"USE_CLOUDINARY: {use_cloudinary}")
    
    if cloud_name and api_key:
        print(f"\n✅ Cloudinary está configurado")
    else:
        print(f"\n⚠️ Cloudinary NO está completamente configurado")

def test_neon_connection():
    """Verifica la conexión a Neon"""
    print("\n" + "=" * 60)
    print("4. VERIFICANDO CONEXIÓN A NEON")
    print("=" * 60)
    
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    db_url = os.getenv("DATABASE_CORE_URL", "")
    
    if "neon.tech" in db_url:
        print(f"✅ Base de datos Neon configurada")
        print(f"   Host: {db_url.split('@')[1].split('/')[0] if '@' in db_url else 'N/A'}")
    else:
        print(f"⚠️ No se detectó conexión a Neon")
        print(f"   URL actual: {db_url[:50]}...")

if __name__ == "__main__":
    print("\n🚀 INICIANDO PRUEBAS DEL SISTEMA MSP_AXS\n")
    
    # 1. Test de login
    token = test_login()
    
    # 2. Test de preregistro
    if token:
        test_preregistro(token)
    
    # 3. Verificar Cloudinary
    test_cloudinary_status(token)
    
    # 4. Verificar Neon
    test_neon_connection()
    
    print("\n" + "=" * 60)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 60)
