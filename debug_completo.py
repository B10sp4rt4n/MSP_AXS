#!/usr/bin/env python3
"""
Script de debug completo para verificar el flujo de autenticación
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("DEBUG COMPLETO DEL SISTEMA")
print("=" * 80)

# 1. Verificar que el servidor responde
print("\n1️⃣ Verificando servidor...")
try:
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("   ✅ Servidor funcionando")
    else:
        print(f"   ⚠️ Servidor responde con {response.status_code}")
except Exception as e:
    print(f"   ❌ Servidor no responde: {e}")
    exit(1)

# 2. Hacer login y obtener token
print("\n2️⃣ Haciendo login...")
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "test@example.com", "password": "test123"}
)

if response.status_code != 200:
    print(f"   ❌ Login falló: {response.status_code}")
    print(f"   Response: {response.text}")
    exit(1)

data = response.json()
token = data["access_token"]
print(f"   ✅ Login exitoso")
print(f"   Token (primeros 50 chars): {token[:50]}...")

# 3. Decodificar el token (sin verificar firma)
print("\n3️⃣ Decodificando token (payload)...")
import base64
try:
    # El JWT tiene 3 partes: header.payload.signature
    parts = token.split('.')
    # Decodificar el payload (segunda parte)
    payload = parts[1]
    # Añadir padding si es necesario
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += '=' * padding
    
    decoded = base64.urlsafe_b64decode(payload)
    payload_data = json.loads(decoded)
    
    print(f"   Usuario ID (sub): {payload_data.get('sub')}")
    print(f"   Rol: {payload_data.get('role')}")
    print(f"   Método: {payload_data.get('method')}")
    print(f"   Emitido (iat): {payload_data.get('iat')}")
    print(f"   Expira (exp): {payload_data.get('exp')}")
    
except Exception as e:
    print(f"   ❌ Error al decodificar: {e}")

# 4. Probar endpoint /msps/
print("\n4️⃣ Probando GET /msps/...")
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/msps/", headers=headers)

print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ Endpoint funciona correctamente")
    msps = response.json()
    print(f"   Total MSPs: {len(msps)}")
    for msp in msps[:3]:
        print(f"      - {msp.get('nombre')} (ID: {msp.get('msp_id')})")
else:
    print(f"   ❌ Error: {response.status_code}")
    print(f"   Response: {response.text}")

# 5. Probar endpoint /condominios/
print("\n5️⃣ Probando GET /condominios/...")
response = requests.get(f"{BASE_URL}/condominios/", headers=headers)

print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   ✅ Endpoint funciona correctamente")
    condos = response.json()
    print(f"   Total Condominios: {len(condos)}")
    for condo in condos[:3]:
        print(f"      - {condo.get('nombre')} (ID: {condo.get('condominio_id')})")
else:
    print(f"   ❌ Error: {response.status_code}")
    print(f"   Response: {response.text}")

# 6. Verificar usuario en BD
print("\n6️⃣ Verificando usuario en BD...")
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv('DATABASE_CORE_URL'))

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT usuario_id, email, nombre, rol 
        FROM usuarios 
        WHERE email = 'test@example.com'
    """))
    user = result.fetchone()
    
    if user:
        print(f"   ✅ Usuario encontrado en BD:")
        print(f"      ID: {user[0]}")
        print(f"      Email: {user[1]}")
        print(f"      Nombre: {user[2]}")
        print(f"      Rol: {user[3]}")
    else:
        print(f"   ❌ Usuario NO encontrado en BD")

print("\n" + "=" * 80)
print("RESUMEN DEL DEBUG")
print("=" * 80)
print(f"✅ Token JWT válido para copiar en el navegador:")
print(f"\nlocalStorage.setItem('token', '{token}');\nlocation.reload();")
print("\n" + "=" * 80)
