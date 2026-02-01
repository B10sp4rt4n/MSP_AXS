#!/usr/bin/env python3
"""
Script para ver la estructura real de las tablas en Neon
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_CORE_URL")

print("=" * 80)
print("ESTRUCTURA DE TABLAS EN NEON")
print("=" * 80)

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

with engine.connect() as conn:
    tables = inspector.get_table_names()
    
    for table in sorted(tables):
        print(f"\n📋 Tabla: {table}")
        print("-" * 80)
        
        columns = inspector.get_columns(table)
        print(f"   Columnas ({len(columns)}):")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            col_type = str(col['type'])
            print(f"      - {col['name']:<30} {col_type:<20} {nullable}")
        
        # Contar registros
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"   📊 Registros: {count}")
        except Exception as e:
            print(f"   ⚠️ Error al contar: {e}")
        
        print()

print("=" * 80)
print("✅ ANÁLISIS COMPLETADO")
print("=" * 80)
