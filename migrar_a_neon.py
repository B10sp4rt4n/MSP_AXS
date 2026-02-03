"""
Script para migrar todo a Neon PostgreSQL
"""
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from backend.db.core.models import Base_CORE, Usuario, Condominio, MSP, Visita
from backend.db.event.models import Base_EVENT
from backend.db.gov.models import Base_GOV
import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Conectar a Neon
DATABASE_CORE_URL = os.getenv("DATABASE_CORE_URL")
DATABASE_EVENT_URL = os.getenv("DATABASE_EVENT_URL")
DATABASE_GOV_URL = os.getenv("DATABASE_GOV_URL")

print("="*60)
print("MIGRANDO A NEON POSTGRESQL")
print("="*60)

# 1. Crear todas las tablas
print("\n1️⃣ Creando tablas en Neon...")

engine_core = create_engine(DATABASE_CORE_URL, pool_pre_ping=True)
engine_event = create_engine(DATABASE_EVENT_URL, pool_pre_ping=True)
engine_gov = create_engine(DATABASE_GOV_URL, pool_pre_ping=True)

Base_CORE.metadata.create_all(bind=engine_core)
print("   ✅ Tablas CORE creadas")

Base_EVENT.metadata.create_all(bind=engine_event)
print("   ✅ Tablas EVENT creadas")

Base_GOV.metadata.create_all(bind=engine_gov)
print("   ✅ Tablas GOV creadas")

# 2. Crear datos base
print("\n2️⃣ Creando datos de demostración...")

from sqlalchemy.orm import sessionmaker

SessionCore = sessionmaker(bind=engine_core)
db = SessionCore()

try:
    # MSP
    msp = MSP(
        msp_id="msp_neon_demo",
        nombre="MSP Neon Demo"
    )
    db.add(msp)
    db.flush()
    print("   ✅ MSP creado")
    
    # Condominio
    condominio = Condominio(
        condominio_id="cond_neon_demo",
        msp_id="msp_neon_demo",
        nombre="Condominio Demo Neon"
    )
    db.add(condominio)
    db.flush()
    print("   ✅ Condominio creado")
    
    # Usuario guardia con password demo123
    # Hash pre-generado con bcrypt para "demo123"
    password_hash = "$2b$12$LKz8cRXuFhN6Vq9B8CjQyePx.gXOvqm8wZFWxDm3Y0bYJrI1QZ9m6"
    
    guardia = Usuario(
        usuario_id="gua_neon_001",
        msp_id="msp_neon_demo",
        condominio_id="cond_neon_demo",
        nombre="Guardia Demo",
        email="guardia@demo.com",
        rol="GUARDIA",
        password_hash=password_hash
    )
    db.add(guardia)
    db.flush()
    print("   ✅ Usuario guardia creado (email: guardia@demo.com, password: demo123)")
    
    # Usuario residente
    residente = Usuario(
        usuario_id="res_neon_001",
        msp_id="msp_neon_demo",
        condominio_id="cond_neon_demo",
        casa_unidad="A-101",
        nombre="Residente Demo",
        email="residente@demo.com",
        rol="RESIDENTE",
        password_hash=password_hash
    )
    db.add(residente)
    db.flush()
    print("   ✅ Usuario residente creado")
    
    db.commit()
    
    # 3. Crear visitas de demostración
    print("\n3️⃣ Creando visitas de demostración...")
    
    visitas = [
        {
            "nombre": "Juan Pérez",
            "tipo": "INVITADO_REGISTRADO",
            "estado": "creada_sin_qr",
            "horas": 4
        },
        {
            "nombre": "María González",
            "tipo": "INVITADO_REGISTRADO",
            "estado": "entrada_registrada",
            "horas": 3,
            "entrada": -1
        },
        {
            "nombre": "Carlos Rodríguez",
            "tipo": "DELIVERY",
            "estado": "creada_sin_qr",
            "horas": 0.5
        },
        {
            "nombre": "Ana Martínez",
            "tipo": "INVITADO_REGISTRADO",
            "estado": "salida_registrada",
            "horas": -1,
            "entrada": -2,
            "salida": -1
        },
        {
            "nombre": "Roberto Silva",
            "tipo": "SERVICIO",
            "estado": "entrada_registrada",
            "horas": 2,
            "entrada": -0.5
        }
    ]
    
    for v in visitas:
        visita_id = f"vis_{secrets.token_urlsafe(6)}"
        token_qr = f"QR-{secrets.token_urlsafe(8)}"
        vigencia = datetime.utcnow() + timedelta(hours=v['horas'])
        
        visita = Visita(
            visita_id=visita_id,
            condominio_id="cond_neon_demo",
            casa_unidad="A-101",
            nombre_visitante=v['nombre'],
            tipo_visitante=v['tipo'],
            estado=v['estado'],
            qr_token=token_qr,
            vigencia=vigencia,
            qr_vigencia=vigencia
        )
        
        if 'entrada' in v:
            visita.hora_entrada = datetime.utcnow() + timedelta(hours=v['entrada'])
            visita.entrada_registrada_en = visita.hora_entrada
            
        if 'salida' in v:
            visita.hora_salida = datetime.utcnow() + timedelta(hours=v['salida'])
            visita.salida_registrada_en = visita.hora_salida
        
        db.add(visita)
        print(f"   ✅ {v['nombre']} - {v['tipo']} - {v['estado']}")
    
    db.commit()
    
    print("\n" + "="*60)
    print("✅ MIGRACIÓN COMPLETADA A NEON")
    print("="*60)
    print("\n📊 Resumen:")
    print(f"   • MSPs: {db.query(MSP).count()}")
    print(f"   • Condominios: {db.query(Condominio).count()}")
    print(f"   • Usuarios: {db.query(Usuario).count()}")
    print(f"   • Visitas: {db.query(Visita).count()}")
    print("\n🔑 Credenciales:")
    print("   Email: guardia@demo.com")
    print("   Password: demo123")
    print("="*60)
    
except Exception as e:
    db.rollback()
    print(f"\n❌ Error: {e}")
    raise
finally:
    db.close()
