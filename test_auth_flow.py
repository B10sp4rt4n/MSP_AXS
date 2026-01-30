#!/usr/bin/env python3
"""
Script para verificar que el flujo de autenticación funciona correctamente
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Prueba el endpoint de login"""
    print("🔐 [PASO 1] Hacer login...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "test@example.com", "password": "test123"}
    )
    
    if response.status_code != 200:
        print(f"❌ Login fallido: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    token = data.get("access_token")
    print(f"✅ Token obtenido: {token[:30]}...")
    return token

def test_get_msps(token):
    """Prueba acceder a /msps/ con el token"""
    print("\n📦 [PASO 2] Obtener lista de MSPs...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/msps/",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ GET /msps/ fallido: {response.status_code}")
        print(f"Respuesta: {response.text}")
        return False
    
    data = response.json()
    print(f"✅ MSPs obtenidos: {len(data)} MSPs encontrados")
    if data:
        print(f"   Primer MSP: {data[0]['nombre']}")
    return True

def test_create_msp(token):
    """Prueba crear un nuevo MSP"""
    print("\n🆕 [PASO 3] Crear nuevo MSP...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    new_msp = {
        "nombre": "Test MSP Creado",
        "email": "test-msp@example.com",
        "telefono": "555-1234"
    }
    
    response = requests.post(
        f"{BASE_URL}/msps/",
        headers=headers,
        json=new_msp
    )
    
    if response.status_code != 200:
        print(f"❌ POST /msps/ fallido: {response.status_code}")
        print(f"Respuesta: {response.text}")
        return False
    
    data = response.json()
    print(f"✅ MSP creado: {data['nombre']} (ID: {data['msp_id']})")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 PRUEBA DE FLUJO DE AUTENTICACIÓN")
    print("=" * 60)
    
    token = test_login()
    if not token:
        print("\n❌ No se pudo obtener token, abortando")
        exit(1)
    
    if not test_get_msps(token):
        print("\n❌ No se pudo acceder a MSPs")
        exit(1)
    
    if not test_create_msp(token):
        print("\n❌ No se pudo crear MSP")
        exit(1)
    
    print("\n" + "=" * 60)
    print("✅ TODO OK - Flujo de autenticación funcionando correctamente")
    print("=" * 60)
