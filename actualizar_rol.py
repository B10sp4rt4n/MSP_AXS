#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv('DATABASE_CORE_URL'))

with engine.connect() as conn:
    # Actualizar el rol del usuario a MSP_ADMIN
    result = conn.execute(text("""
        UPDATE usuarios 
        SET rol = 'MSP_ADMIN' 
        WHERE email = 'test@example.com'
    """))
    conn.commit()
    
    # Verificar
    result = conn.execute(text("""
        SELECT usuario_id, email, nombre, rol 
        FROM usuarios 
        WHERE email = 'test@example.com'
    """))
    user = result.fetchone()
    
    print(f"✅ Usuario actualizado:")
    print(f"   ID: {user[0]}")
    print(f"   Email: {user[1]}")
    print(f"   Nombre: {user[2]}")
    print(f"   Rol: {user[3]}")
