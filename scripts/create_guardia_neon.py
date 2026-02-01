#!/usr/bin/env python3
"""Crear guardia demo directo en Neon PostgreSQL"""
import os
import psycopg2
import uuid
import bcrypt
from datetime import datetime
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# Obtener DB URL
db_url = os.getenv("DATABASE_CORE_URL")
if not db_url:
    print("❌ DATABASE_CORE_URL no definida en .env")
    exit(1)

print("🔗 Conectando a Neon PostgreSQL...")

# Generar hash con bcrypt
pwd = 'guard123'
salt = bcrypt.gensalt()
hash_pwd = bcrypt.hashpw(pwd.encode('utf-8'), salt).decode('utf-8')

try:
    # Conectar
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Eliminar guardia anterior si existe
    cur.execute("DELETE FROM usuarios WHERE email = 'guardia@condoriente.com'")
    print(f"   Usuarios anteriores eliminados")
    
    # Insertar guardia
    usuario_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO usuarios (usuario_id, email, nombre, password_hash, rol, condominio_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (usuario_id, 'guardia@condoriente.com', 'Guardia Demo', hash_pwd, 'GUARDIA', 'COND-001'))
    
    conn.commit()
    
    print(f"\n✅ Guardia creado exitosamente")
    print(f"   Usuario ID: {usuario_id}")
    print(f"   Email: guardia@condoriente.com")
    print(f"   Password: guard123")
    print(f"   Rol: GUARDIA")
    print(f"   Condominio: COND-001")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)
