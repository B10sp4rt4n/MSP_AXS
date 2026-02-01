#!/usr/bin/env python3
"""Crear condominio demo"""
import os
import psycopg2

# Leer .env manualmente
env_path = '/workspaces/MSP_AXS/.env'
db_url = None

with open(env_path, 'r') as f:
    for line in f:
        if line.startswith('DATABASE_CORE_URL='):
            db_url = line.split('=', 1)[1].strip()
            break

if not db_url:
    print("❌ DATABASE_CORE_URL no encontrada")
    exit(1)

print("🔗 Conectando...")

conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Crear MSP primero
cur.execute("""
    INSERT INTO msps_exo (msp_id, nombre)
    VALUES ('MSP-001', 'Demo MSP')
    ON CONFLICT (msp_id) DO NOTHING
""")

# Crear condominio
cur.execute("""
    INSERT INTO condominios_exo (condominio_id, msp_id, nombre)
    VALUES ('COND-001', 'MSP-001', 'Condominio Oriente')
    ON CONFLICT (condominio_id) DO NOTHING
""")

conn.commit()
print("✅ MSP y Condominio creados")

cur.close()
conn.close()
