#!/usr/bin/env python3
"""
Script para verificar datos en la base de datos
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Obtener URLs de conexión
DATABASE_CORE_URL = os.getenv("DATABASE_CORE_URL")
DATABASE_EVENT_URL = os.getenv("DATABASE_EVENT_URL")
DATABASE_GOV_URL = os.getenv("DATABASE_GOV_URL")

def check_database(db_url, db_name):
    """Verifica el contenido de una base de datos"""
    print(f"\n{'='*70}")
    print(f"📊 VERIFICANDO: {db_name}")
    print(f"{'='*70}")
    
    if not db_url:
        print(f"❌ No hay URL configurada para {db_name}")
        return
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Obtener lista de tablas
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            if not tables:
                print(f"⚠️  No se encontraron tablas en {db_name}")
                return
            
            print(f"✅ Tablas encontradas: {len(tables)}")
            print()
            
            # Verificar contenido de cada tabla
            for table in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    
                    print(f"📋 {table}: {count} registros")
                    
                    # Mostrar algunos datos si los hay
                    if count > 0 and count <= 10:
                        data_result = conn.execute(text(f"SELECT * FROM {table} LIMIT 5"))
                        columns = data_result.keys()
                        print(f"   Columnas: {', '.join(columns)}")
                        
                        for i, row in enumerate(data_result, 1):
                            print(f"   Registro {i}: {dict(zip(columns, row))}")
                    elif count > 10:
                        # Mostrar solo las primeras 3 filas
                        data_result = conn.execute(text(f"SELECT * FROM {table} LIMIT 3"))
                        columns = data_result.keys()
                        print(f"   Columnas: {', '.join(columns)}")
                        print(f"   (Mostrando solo 3 de {count} registros)")
                        
                        for i, row in enumerate(data_result, 1):
                            print(f"   Registro {i}: {dict(zip(columns, row))}")
                    
                    print()
                except Exception as e:
                    print(f"   ⚠️  Error al consultar {table}: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error conectando a {db_name}: {str(e)}")

def check_user_auth():
    """Verifica específicamente el usuario de prueba"""
    print(f"\n{'='*70}")
    print(f"🔐 VERIFICANDO USUARIO DE PRUEBA (test@example.com)")
    print(f"{'='*70}")
    
    try:
        engine = create_engine(DATABASE_CORE_URL)
        with engine.connect() as conn:
            # Buscar usuario
            result = conn.execute(text("""
                SELECT usuario_id, email, nombre, rol, condominio_id, activo 
                FROM usuarios 
                WHERE email = 'test@example.com'
            """))
            user = result.fetchone()
            
            if user:
                print("✅ Usuario encontrado:")
                columns = result.keys()
                user_dict = dict(zip(columns, user))
                for key, value in user_dict.items():
                    print(f"   {key}: {value}")
            else:
                print("❌ Usuario test@example.com NO encontrado en la base de datos")
                
                # Mostrar todos los usuarios
                print("\n📋 Usuarios existentes en la base de datos:")
                all_users = conn.execute(text("SELECT usuario_id, email, nombre, rol FROM usuarios LIMIT 10"))
                for u in all_users:
                    print(f"   - {u[1]} ({u[2]}) - Rol: {u[3]}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("\n🚀 VERIFICACIÓN DE BASE DE DATOS MSP_AXS\n")
    
    # Verificar cada base de datos
    check_database(DATABASE_CORE_URL, "AUP_CORE (Usuarios, Condominios, Visitas)")
    check_database(DATABASE_EVENT_URL, "AUP_EVENT (Eventos de trazabilidad)")
    check_database(DATABASE_GOV_URL, "AUP_GOV (Gobierno y políticas)")
    
    # Verificación específica del usuario
    check_user_auth()
    
    print(f"\n{'='*70}")
    print("✅ VERIFICACIÓN COMPLETADA")
    print(f"{'='*70}\n")
