#!/usr/bin/env python3
"""
Script para debuggear exactamente qué está pasando con el token.
Genera un token localmente y lo valida con el mismo SECRET_KEY.
"""

import sys
sys.path.insert(0, '/workspaces/MSP_AXS')

from backend.core.auth.jwt import create_access_token, decode_access_token, SECRET_KEY, ALGORITHM
from jose import jwt as jose_jwt
import json

print("=" * 80)
print("🔍 DEBUG: Generación y Validación de JWT")
print("=" * 80)

# 1. Mostrar configuración
print("\n📋 CONFIGURACIÓN:")
print(f"   SECRET_KEY: {SECRET_KEY[:30]}... (primeros 30 chars)")
print(f"   ALGORITHM: {ALGORITHM}")

# 2. Generar token
print("\n1️⃣ GENERANDO TOKEN...")
token = create_access_token(user_id="user_test_001", role="ADMIN")
print(f"   Token generado: {token[:50]}...")
print(f"   Longitud: {len(token)} chars")

# 3. Analizar estructura JWT
print("\n2️⃣ ANALIZANDO ESTRUCTURA JWT...")
parts = token.split('.')
print(f"   Partes: {len(parts)}")
if len(parts) == 3:
    print(f"   ✅ JWT válido (3 partes)")
    print(f"      Header:    {parts[0][:30]}...")
    print(f"      Payload:   {parts[1][:30]}...")
    print(f"      Signature: {parts[2][:30]}...")
else:
    print(f"   ❌ JWT inválido ({len(parts)} partes)")

# 4. Decodificar manualmente con jose para ver el payload
print("\n3️⃣ DECODIFICANDO PAYLOAD (MANUAL)...")
try:
    # Sin verificación de firma, solo para ver qué hay adentro
    import base64
    payload_b64 = parts[1]
    # Agregar padding si es necesario
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    
    payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
    payload_dict = json.loads(payload_json)
    
    print(f"   ✅ Payload decodificado:")
    for key, value in payload_dict.items():
        print(f"      {key}: {value}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 5. Validar con decode_access_token()
print("\n4️⃣ VALIDANDO CON decode_access_token()...")
payload = decode_access_token(token)
if payload:
    print(f"   ✅ Token válido!")
    print(f"   Payload: {payload}")
else:
    print(f"   ❌ decode_access_token() retornó None")

# 6. Intentar decodificar directamente con jose
print("\n5️⃣ VALIDANDO CON jose.jwt.decode()...")
try:
    payload_jose = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"   ✅ Token válido!")
    print(f"   Payload: {payload_jose}")
except Exception as e:
    print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
    print(f"   Error detalles: {repr(e)}")

print("\n" + "=" * 80)
print("✅ Debug completado")
print("=" * 80)
