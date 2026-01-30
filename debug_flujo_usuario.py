#!/usr/bin/env python3
"""
Script que simula EXACTAMENTE lo que hace el usuario:
1. Hace login en http://localhost:8000/auth/login
2. Obtiene token
3. Intenta acceder a /msps/ con ese token
4. Loguea TODO lo que sucede
"""

import requests
import json
import logging

# Configurar logging para ver TODO
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("🔍 SIMULANDO FLUJO DEL USUARIO")
print("=" * 80)

# 1. Login
print("\n1️⃣ PASO 1: Haciendo login...")
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "test@example.com", "password": "test123"},
    timeout=10
)

print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    token = data['access_token']
    print(f"   ✅ Token obtenido: {token[:50]}...")
    print(f"   Token completo:")
    print(f"   {token}")
else:
    print(f"   ❌ Login falló: {response.text}")
    exit(1)

# 2. Analizar token
print("\n2️⃣ PASO 2: Analizando estructura del token...")
parts = token.split('.')
print(f"   Partes: {len(parts)}")
for i, part in enumerate(parts):
    print(f"      Parte {i+1}: {part[:30]}... ({len(part)} chars)")

# 3. Acceder a /msps/
print("\n3️⃣ PASO 3: Accediendo a GET /msps/...")
response = requests.get(
    f"{BASE_URL}/msps/",
    headers={"Authorization": f"Bearer {token}"},
    timeout=10
)

print(f"   Status: {response.status_code}")
print(f"   Response: {response.text[:500]}")

if response.status_code == 200:
    print(f"   ✅ GET /msps/ exitoso!")
    data = response.json()
    print(f"   MSPs obtenidos: {len(data)}")
else:
    print(f"   ❌ GET /msps/ falló")

print("\n" + "=" * 80)
