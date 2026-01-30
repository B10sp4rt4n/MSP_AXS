#!/usr/bin/env python3
"""
Script para extraer el token que se generó en el navegador
y probarlo directamente contra el servidor.

Instrucciones:
1. Ejecuta este script en VS Code terminal
2. Sigue las instrucciones para copiar el token desde el navegador
"""

import requests
import sys

print("""
╔════════════════════════════════════════════════════════════════════╗
║           🔐 SCRIPT PARA DEBUGGEAR AUTENTICACIÓN                 ║
╚════════════════════════════════════════════════════════════════════╝

Este script va a:
1. Pedirte el token que ves en la consola del navegador
2. Probarlo contra el servidor
3. Mostrarte exactamente qué está fallando

INSTRUCCIONES:
──────────────
1. Abre la consola del navegador (F12 → Console)
2. En la consola, ejecuta:

   localStorage.getItem('auth_token')

3. Copia el resultado COMPLETO (desde eyJ... hasta el final)
4. Pégalo aquí abajo cuando te lo pida

""")

input("Presiona ENTER para continuar...")

print("\n🔐 Pega el token completo (sin comillas):")
print("(Presiona ENTER al final cuando hayas pegado todo)")
print()

token = input().strip()

if not token:
    print("❌ No ingresaste un token")
    sys.exit(1)

# Validar que sea un JWT válido
parts = token.split('.')
if len(parts) != 3:
    print(f"❌ Token inválido: tiene {len(parts)} partes, debería tener 3")
    sys.exit(1)

print(f"\n✅ Token recibido:")
print(f"   Longitud: {len(token)} caracteres")
print(f"   Partes: {len(parts)}")
print(f"   Primeros 50 caracteres: {token[:50]}")
print(f"   Últimos 50 caracteres: {token[-50:]}")

# Probar contra servidor
print("\n🧪 Probando contra servidor...")
print("   Intento 1: GET http://localhost:8000/msps/")

try:
    response = requests.get(
        "http://localhost:8000/msps/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ FUNCIONA contra localhost")
        data = response.json()
        print(f"   MSPs obtenidos: {len(data)}")
    else:
        print(f"   ❌ Error {response.status_code}")
        print(f"   Respuesta: {response.text[:300]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*70)
print("📋 INFORMACIÓN PARA COMPARTIR:")
print("="*70)
print(f"\nToken completo:")
print(token)
print(f"\nToken en 3 partes:")
print(f"1. Header:    {parts[0]}")
print(f"2. Payload:   {parts[1]}")
print(f"3. Signature: {parts[2]}")
print("\n" + "="*70)
