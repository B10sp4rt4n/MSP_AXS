#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
Verificador de Migraciones AUP
═══════════════════════════════════════════════════════════════════════════

Valida que las 3 bases de datos AUP tienen las tablas correctas:
- AUP_CORE: Identidad, Alcance, Negocio
- AUP_EVENT: Verdad Histórica
- AUP_GOV: Poder Explícito

Uso:
    python scripts/verify_migration.py

Salida:
    0 si todas las tablas existen
    1 si faltan tablas o hay errores
"""

import sys
import os

# Asegurar que el path incluye el directorio raíz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import inspect
from backend.db.core import engine_core
from backend.db.event import engine_event
from backend.db.gov import engine_gov


def verificar_core() -> bool:
    """
    Verifica tablas en AUP_CORE.
    
    Returns:
        True si todas las tablas esperadas existen
    """
    try:
        inspector = inspect(engine_core)
        tablas = inspector.get_table_names()
        
        # Tablas esperadas en CORE
        esperadas = [
            "usuarios_exo",
            "msps_exo",
            "condominios_exo",
            "user_tenant_scope",
            "visitas",
            "evidencias",
            "casetas"
        ]
        
        print("\n[AUP_CORE]")
        print(f"  URL: {str(engine_core.url).split('@')[-1] if '@' in str(engine_core.url) else str(engine_core.url)}")
        print(f"  Tablas encontradas: {len(tablas)}")
        
        for tabla in esperadas:
            status = "✓" if tabla in tablas else "✗"
            print(f"    {status} {tabla}")
        
        todas_existen = all(t in tablas for t in esperadas)
        
        if todas_existen:
            print("  → Estado: OK")
        else:
            print("  → Estado: INCOMPLETO")
        
        return todas_existen
        
    except Exception as e:
        print(f"\n[AUP_CORE]")
        print(f"  ❌ ERROR al conectar: {str(e)}")
        return False


def verificar_event() -> bool:
    """
    Verifica tablas en AUP_EVENT.
    
    Returns:
        True si la tabla events_aup existe
    """
    try:
        inspector = inspect(engine_event)
        tablas = inspector.get_table_names()
        
        print("\n[AUP_EVENT]")
        print(f"  URL: {str(engine_event.url).split('@')[-1] if '@' in str(engine_event.url) else str(engine_event.url)}")
        print(f"  Tablas encontradas: {len(tablas)}")
        
        status = "✓" if "events_aup" in tablas else "✗"
        print(f"    {status} events_aup")
        
        existe = "events_aup" in tablas
        
        if existe:
            # Contar eventos existentes
            from sqlalchemy import text
            with engine_event.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM events_aup"))
                count = result.scalar()
                print(f"  → Eventos registrados: {count}")
                print("  → Estado: OK")
        else:
            print("  → Estado: FALTA TABLA")
        
        return existe
        
    except Exception as e:
        print(f"\n[AUP_EVENT]")
        print(f"  ❌ ERROR al conectar: {str(e)}")
        return False


def verificar_gov() -> bool:
    """
    Verifica tablas en AUP_GOV.
    
    Returns:
        True si todas las tablas esperadas existen
    """
    try:
        inspector = inspect(engine_gov)
        tablas = inspector.get_table_names()
        
        # Tablas esperadas en GOV
        esperadas = [
            "authorities_gov",
            "policies_gov",
            "delegations_gov"
        ]
        
        print("\n[AUP_GOV]")
        print(f"  URL: {str(engine_gov.url).split('@')[-1] if '@' in str(engine_gov.url) else str(engine_gov.url)}")
        print(f"  Tablas encontradas: {len(tablas)}")
        
        for tabla in esperadas:
            status = "✓" if tabla in tablas else "✗"
            print(f"    {status} {tabla}")
        
        todas_existen = all(t in tablas for t in esperadas)
        
        if todas_existen:
            print("  → Estado: OK")
        else:
            print("  → Estado: INCOMPLETO")
        
        return todas_existen
        
    except Exception as e:
        print(f"\n[AUP_GOV]")
        print(f"  ❌ ERROR al conectar: {str(e)}")
        return False


def main():
    """
    Ejecuta verificación completa de las 3 bases AUP.
    """
    print("═" * 80)
    print("VERIFICACIÓN DE MIGRACIONES AUP")
    print("═" * 80)
    
    # Verificar cada base
    core_ok = verificar_core()
    event_ok = verificar_event()
    gov_ok = verificar_gov()
    
    # Resumen final
    print("\n" + "═" * 80)
    print("RESUMEN")
    print("═" * 80)
    
    print(f"AUP_CORE:  {'✅ OK' if core_ok else '❌ INCOMPLETO'}")
    print(f"AUP_EVENT: {'✅ OK' if event_ok else '❌ INCOMPLETO'}")
    print(f"AUP_GOV:   {'✅ OK' if gov_ok else '❌ INCOMPLETO'}")
    
    print("═" * 80)
    
    if core_ok and event_ok and gov_ok:
        print("\n✅ TODAS LAS BASES ESTÁN CORRECTAS")
        print("   Sistema AUP listo para operar.")
        print("\nPróximos pasos:")
        print("  1. Ejecutar seeds: python scripts/seed_gov_bootstrap.py")
        print("  2. Crear scopes: python scripts/migrate_create_scopes.py")
        print("  3. Iniciar backend: uvicorn backend.main:app --reload")
        print("═" * 80)
        return 0
    else:
        print("\n❌ FALTAN TABLAS - Ejecutar migraciones faltantes")
        print("\nAcciones requeridas:")
        
        if not core_ok:
            print("  • AUP_CORE:")
            print("      psql $DATABASE_CORE_URL < database/schema_axs.sql")
        
        if not event_ok:
            print("  • AUP_EVENT:")
            print("      psql $DATABASE_EVENT_URL < database/migration_event.sql")
        
        if not gov_ok:
            print("  • AUP_GOV:")
            print("      psql $DATABASE_GOV_URL < database/migration_04_gov.sql")
        
        print("\n  Luego ejecutar de nuevo: python scripts/verify_migration.py")
        print("═" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
