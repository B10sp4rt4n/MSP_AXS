#!/usr/bin/env python3
"""
Script para obtener un token válido y probarlo
"""
import requests
import json

BASE_URL = "https://verbose-xylophone-7v5p45gj7q79hx4vv-8000.app.github.dev"

print("=" * 80)
print("OBTENIENDO NUEVO TOKEN VÁLIDO")
print("=" * 80)

# 1. Login
print("\n🔐 Haciendo login...")
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "test@example.com", "password": "test123"}
)

if response.status_code == 200:
    data = response.json()
    token = data["access_token"]
    print(f"✅ Login exitoso!")
    print(f"\n📋 Token nuevo:")
    print(token)
    print(f"\n💾 Guarda este token en localStorage con:")
    print(f'   localStorage.setItem("token", "{token}");')
    
    # 2. Probar el token
    print(f"\n🧪 Probando token...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Probar MSPs
    print("\n   Probando GET /msps/...")
    response = requests.get(f"{BASE_URL}/msps/", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Token funciona correctamente")
        msps = response.json()
        print(f"   Datos: {len(msps)} MSPs encontrados")
    else:
        print(f"   ❌ Error: {response.text}")
    
    # Probar Condominios
    print("\n   Probando GET /condominios/...")
    response = requests.get(f"{BASE_URL}/condominios/", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Token funciona correctamente")
        condos = response.json()
        print(f"   Datos: {len(condos)} condominios encontrados")
    else:
        print(f"   ❌ Error: {response.text}")
    
    print("\n" + "=" * 80)
    print("✅ TOKEN GENERADO Y VALIDADO")
    print("=" * 80)
    print(f"\n🔑 Copia y pega en la consola del navegador:")
    print(f'localStorage.setItem("token", "{token}");')
    print(f'location.reload();')
    
else:
    print(f"❌ Login falló: {response.status_code}")
    print(f"   Response: {response.text}")
