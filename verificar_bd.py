#!/usr/bin/env python3
"""
Script para verificar el contenido de la base de datos Neon
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_CORE_URL")

print("=" * 80)
print("VERIFICACIÓN DE BASE DE DATOS NEON")
print("=" * 80)

if not DATABASE_URL:
    print("❌ No se encontró DATABASE_CORE_URL en .env")
    exit(1)

print(f"\n📡 Conectando a: {DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'N/A'}")

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("✅ Conexión exitosa a Neon\n")
        
        # Obtener lista de tablas
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"📋 Tablas encontradas ({len(tables)}):")
        for table in sorted(tables):
            print(f"   - {table}")
        
        print("\n" + "=" * 80)
        print("CONTENIDO DE TABLAS PRINCIPALES")
        print("=" * 80)
        
        # Verificar usuarios
        if "usuarios" in tables:
            result = conn.execute(text("SELECT usuario_id, email, nombre, rol, condominio_id FROM usuarios"))
            usuarios = result.fetchall()
            print(f"\n👤 USUARIOS ({len(usuarios)} registros):")
            for u in usuarios:
                print(f"   ID: {u[0]} | Email: {u[1]} | Nombre: {u[2]} | Rol: {u[3]} | Condominio: {u[4]}")
        
        # Verificar condominios
        if "condominios_exo" in tables:
            result = conn.execute(text("SELECT condominio_id, nombre FROM condominios_exo"))
            condominios = result.fetchall()
            print(f"\n🏢 CONDOMINIOS ({len(condominios)} registros):")
            for c in condominios:
                print(f"   ID: {c[0]} | Nombre: {c[1]}")
        
        # Verificar MSPs
        if "msps_exo" in tables:
            result = conn.execute(text("SELECT msp_id, nombre FROM msps_exo"))
            msps = result.fetchall()
            print(f"\n🏭 MSPs ({len(msps)} registros):")
            for m in msps:
                print(f"   ID: {m[0]} | Empresa: {m[1]}")
        
        # Verificar visitas
        if "visitas" in tables:
            result = conn.execute(text("""
                SELECT visita_id, nombre_visitante, tipo_visita, estado, 
                       entrada_registrada_en, condominio_id 
                FROM visitas 
                ORDER BY created_at DESC 
                LIMIT 10
            """))
            visitas = result.fetchall()
            print(f"\n🚪 VISITAS (últimas 10 registros):")
            for v in visitas:
                print(f"   ID: {v[0]} | Visitante: {v[1]} | Tipo: {v[2]} | Estado: {v[3]} | Entrada: {v[4]} | Condo: {v[5]}")
        
        # Verificar scopes_aup
        if "user_tenant_scope" in tables:
            result = conn.execute(text("SELECT usuario_id, tenant_id, access_level, estado FROM user_tenant_scope LIMIT 5"))
            scopes = result.fetchall()
            print(f"\n🔐 USER_TENANT_SCOPE ({len(scopes)} registros mostrados):")
            for s in scopes:
                print(f"   Usuario: {s[0]} | Tenant: {s[1]} | Level: {s[2]} | Estado: {s[3]}")
        
        # Verificar events_aup
        if "events_aup" in tables:
            result = conn.execute(text("""
                SELECT tipo_evento, entidad, accion, resultado, identity_id, timestamp 
                FROM events_aup 
                ORDER BY timestamp DESC 
                LIMIT 10
            """))
            events = result.fetchall()
            print(f"\n📝 EVENTS_AUP (últimos 10 eventos):")
            for e in events:
                print(f"   Tipo: {e[0]} | Entity: {e[1]} | Action: {e[2]} | Result: {e[3]} | User: {e[4]} | Fecha: {e[5]}")
        
        # Verificar authorities_gov
        if "authorities_gov" in tables:
            result = conn.execute(text("SELECT authority_id, identity_id, tipo, estado FROM authorities_gov"))
            authorities = result.fetchall()
            print(f"\n⚖️ AUTHORITIES_GOV ({len(authorities)} registros):")
            for a in authorities:
                print(f"   ID: {a[0]} | Identity: {a[1]} | Tipo: {a[2]} | Estado: {a[3]}")
        
        # Verificar policies_gov
        if "policies_gov" in tables:
            result = conn.execute(text("SELECT policy_id, nombre, ambito, accion_objetivo, estado FROM policies_gov"))
            policies = result.fetchall()
            print(f"\n📜 POLICIES_GOV ({len(policies)} registros):")
            for p in policies:
                print(f"   ID: {p[0]} | Nombre: {p[1]} | Ámbito: {p[2]} | Acción: {p[3]} | Estado: {p[4]}")
        
        print("\n" + "=" * 80)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("=" * 80)
        
except Exception as e:
    print(f"❌ Error al conectar/consultar la base de datos:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
