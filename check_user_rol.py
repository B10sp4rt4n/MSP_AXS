#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()
sys.path.insert(0, '/workspaces/MSP_AXS')

engine = create_engine(os.getenv("DATABASE_CORE_URL"))
Session = sessionmaker(bind=engine)
db = Session()

result = db.execute(text("SELECT usuario_id, email, nombre, rol FROM usuarios WHERE email = 'test@example.com'"))
row = result.fetchone()

if row:
    print(f"\n{'='*60}")
    print(f"Usuario ID: {row[0]}")
    print(f"Email: {row[1]}")
    print(f"Nombre: {row[2]}")
    print(f"Rol: {row[3]}")
    print(f"{'='*60}\n")
else:
    print("Usuario no encontrado")

db.close()
