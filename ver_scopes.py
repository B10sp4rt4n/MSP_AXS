#!/usr/bin/env python3
"""Ver scopes del usuario"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, '/workspaces/MSP_AXS')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Conectar a la BD
DATABASE_URL = os.getenv("DATABASE_CORE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

# Ver scopes
print("\n" + "="*80)
print("SCOPES DEL USUARIO test@example.com")
print("="*80)

result = db.execute("""
    SELECT 
        u.usuario_id,
        u.email,
        u.rol,
        uts.tenant_id,
        uts.access_level,
        uts.estado
    FROM usuarios u
    LEFT JOIN user_tenant_scope uts ON u.usuario_id = uts.usuario_id
    WHERE u.email = 'test@example.com'
""")

for row in result:
    print(f"\nUsuario ID: {row[0]}")
    print(f"Email: {row[1]}")
    print(f"Rol: {row[2]}")
    print(f"Tenant ID: {row[3]}")
    print(f"Access Level: {row[4]}")
    print(f"Estado: {row[5]}")

print("\n" + "="*80)

# Ver condominios disponibles
print("\nCONDOMINIOS DISPONIBLES:")
print("="*80)

result = db.execute("SELECT condominio_id, nombre FROM condominios")
for row in result:
    print(f"- {row[1]} ({row[0]})")

print("\n" + "="*80)

db.close()
