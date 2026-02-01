#!/usr/bin/env python3
"""
Script para inicializar datos de prueba en Neon
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime
import uuid
import bcrypt

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_CORE_URL")

print("=" * 80)
print("INICIALIZANDO DATOS DE PRUEBA EN NEON")
print("=" * 80)

if not DATABASE_URL:
    print("❌ No se encontró DATABASE_CORE_URL en .env")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

# Generar IDs únicos
msp_id = f"msp_{uuid.uuid4().hex[:8]}"
condominio_id = f"condo_{uuid.uuid4().hex[:8]}"
usuario_id = f"user_{uuid.uuid4().hex[:8]}"
caseta_id = f"caseta_{uuid.uuid4().hex[:8]}"

# Hash de la contraseña "test123"
password = "test123"
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print(f"\n🔑 Generando datos con:")
print(f"   MSP ID: {msp_id}")
print(f"   Condominio ID: {condominio_id}")
print(f"   Usuario ID: {usuario_id}")
print(f"   Password: {password}")

with engine.connect() as conn:
    try:
        # 1. Crear MSP
        print("\n1️⃣ Creando MSP...")
        conn.execute(text("""
            INSERT INTO msps_exo (msp_id, nombre)
            VALUES (:msp_id, :nombre)
        """), {
            "msp_id": msp_id,
            "nombre": "MSP Demo Security"
        })
        print("   ✅ MSP creado")
        
        # 2. Crear Condominio
        print("\n2️⃣ Creando Condominio...")
        conn.execute(text("""
            INSERT INTO condominios_exo (condominio_id, msp_id, nombre)
            VALUES (:condominio_id, :msp_id, :nombre)
        """), {
            "condominio_id": condominio_id,
            "msp_id": msp_id,
            "nombre": "Residencial Las Palmas"
        })
        print("   ✅ Condominio creado")
        
        # 3. Crear Usuario test@example.com
        print("\n3️⃣ Creando Usuario test@example.com...")
        conn.execute(text("""
            INSERT INTO usuarios (
                usuario_id, msp_id, condominio_id, casa_unidad,
                nombre, email, rol, password_hash, creado
            ) VALUES (
                :usuario_id, :msp_id, :condominio_id, :casa_unidad,
                :nombre, :email, :rol, :password_hash, :creado
            )
        """), {
            "usuario_id": usuario_id,
            "msp_id": msp_id,
            "condominio_id": condominio_id,
            "casa_unidad": "A-101",
            "nombre": "Usuario Test",
            "email": "test@example.com",
            "rol": "RESIDENTE",
            "password_hash": password_hash,
            "creado": datetime.utcnow()
        })
        print("   ✅ Usuario creado")
        
        # 4. Crear Caseta
        print("\n4️⃣ Creando Caseta...")
        conn.execute(text("""
            INSERT INTO casetas (caseta_id, condominio_id, nombre, created_at)
            VALUES (:caseta_id, :condominio_id, :nombre, :created_at)
        """), {
            "caseta_id": caseta_id,
            "condominio_id": condominio_id,
            "nombre": "Caseta Principal",
            "created_at": datetime.utcnow()
        })
        print("   ✅ Caseta creada")
        
        # 5. Crear Scope para el usuario
        print("\n5️⃣ Creando Scope (AUP)...")
        conn.execute(text("""
            INSERT INTO user_tenant_scope (
                usuario_id, tenant_id, access_level, estado, created_at
            ) VALUES (
                :usuario_id, :tenant_id, :access_level, :estado, :created_at
            )
        """), {
            "usuario_id": usuario_id,
            "tenant_id": condominio_id,
            "access_level": "RESIDENTE",
            "estado": "ACTIVO",
            "created_at": datetime.utcnow()
        })
        print("   ✅ Scope creado")
        
        # 6. Crear algunas visitas de ejemplo
        print("\n6️⃣ Creando visitas de ejemplo...")
        for i in range(3):
            visita_id = f"visita_{uuid.uuid4().hex[:8]}"
            conn.execute(text("""
                INSERT INTO visitas (
                    visita_id, condominio_id, nombre_visitante, casa_unidad,
                    tipo_visita, estado, created_at
                ) VALUES (
                    :visita_id, :condominio_id, :nombre_visitante, :casa_unidad,
                    :tipo_visita, :estado, :created_at
                )
            """), {
                "visita_id": visita_id,
                "condominio_id": condominio_id,
                "nombre_visitante": f"Visitante {i+1}",
                "casa_unidad": "A-101",
                "tipo_visita": ["PROVEEDOR", "FAMILIAR", "INVITADO"][i],
                "estado": "PENDIENTE",
                "created_at": datetime.utcnow()
            })
        print("   ✅ 3 visitas creadas")
        
        # Commit de todos los cambios
        conn.commit()
        
        print("\n" + "=" * 80)
        print("✅ DATOS INICIALIZADOS EXITOSAMENTE")
        print("=" * 80)
        print(f"\n🔐 Credenciales de acceso:")
        print(f"   Email: test@example.com")
        print(f"   Password: test123")
        print(f"\n📊 Datos creados:")
        print(f"   1 MSP: MSP Demo Security")
        print(f"   1 Condominio: Residencial Las Palmas")
        print(f"   1 Usuario: test@example.com (RESIDENTE)")
        print(f"   1 Caseta: Caseta Principal")
        print(f"   3 Visitas de ejemplo")
        print("\n" + "=" * 80)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error al crear datos:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
