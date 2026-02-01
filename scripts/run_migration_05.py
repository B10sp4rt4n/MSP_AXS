#!/usr/bin/env python3
"""Ejecutar migración 05 - Modo Guardia"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_CORE_URL")
if not db_url:
    print("❌ DATABASE_CORE_URL no definida")
    exit(1)

print("🔗 Conectando a Neon PostgreSQL...")

# Leer SQL
with open('/workspaces/MSP_AXS/database/migration_05_modo_guardia.sql', 'r') as f:
    sql = f.read()

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    print("📝 Ejecutando migración 05...")
    cur.execute(sql)
    conn.commit()
    
    print("\n✅ Migración ejecutada exitosamente")
    print("\nEstructura de tabla visitas:")
    
    # Mostrar estructura actualizada
    results = cur.fetchall()
    for row in results:
        nullable = "NULL" if row[2] == "YES" else "NOT NULL"
        print(f"   • {row[0]:<30} {row[1]:<20} {nullable}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)
