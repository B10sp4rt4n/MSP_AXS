#!/usr/bin/env python3
"""Genera un token nuevo con 8 horas de validez"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path
sys.path.insert(0, '/workspaces/MSP_AXS')

from backend.core.auth.jwt import create_access_token

# Generar token para el usuario test
user_id = "user_0ff0e637"  # ID del usuario en la BD
role = "MSP_ADMIN"

token = create_access_token(user_id=user_id, role=role)

print("\n" + "="*80)
print("TOKEN NUEVO GENERADO")
print("="*80)
print(f"\n{token}\n")
print("="*80)
print("\nCopia este código completo en la CONSOLA del navegador (F12 > Console):")
print("="*80)
print(f"\nlocalStorage.setItem('token', '{token}');")
print("location.reload();")
print("\n" + "="*80)
