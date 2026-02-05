#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
SEED AUP_GOV: Bootstrap Inicial de Gobierno
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

El sistema NACE gobernado, no vacío.

Este script crea el estado inicial mínimo de AUP_GOV:
  1. Authority GLOBAL (primer admin del sistema)
  2. Políticas base (límites conservadores para arranque)
  3. (Opcional) First tier de prueba

Axioma: Sin gobierno inicial, el sistema está indefenso.

═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import os
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
# ✅ AUP_CORE y AUP_GOV separados
from backend.db.core import SessionLocal_CORE, Usuario
from backend.db.gov import SessionLocal_GOV, Authority, Policy, AuthorityType, PolicyScope, GovStatus
from backend.core.gov.authority import crear_authority
from backend.core.gov.policy import crear_policy
from datetime import datetime
import uuid


def seed_authority_global(db_core: Session, db_gov: Session) -> Authority:
    """
    Crea AUP_AUTHORITY GLOBAL para el primer admin del sistema.
    
    Requiere: Al menos un usuario con rol MSP_ADMIN en la BD.
    """
    print("\n[1] Creando AUTHORITY GLOBAL...")
    
    # Buscar primer MSP_ADMIN en CORE
    admin_global = db_core.query(Usuario).filter(
        Usuario.rol == "MSP_ADMIN"
    ).first()
    
    if not admin_global:
        print("❌ ERROR: No hay usuarios con rol MSP_ADMIN en la BD.")
        print("   Crear al menos un admin antes de ejecutar este seed.")
        sys.exit(1)
    
    # Verificar si ya existe authority en GOV
    existing = db_gov.query(Authority).filter(
        Authority.identity_id == admin_global.usuario_id,
        Authority.tipo == AuthorityType.GLOBAL
    ).first()
    
    if existing:
        print(f"✓ Authority GLOBAL ya existe para {admin_global.email}")
        return existing
    
    # Crear authority en GOV
    authority = crear_authority(
        db=db_gov,
        identity=admin_global,
        tipo=AuthorityType.GLOBAL,
        tenant_id=None,
        metadata={"bootstrap": True, "created_by": "seed_script"}
    )
    
    print(f"✓ Authority GLOBAL creada para: {admin_global.email}")
    print(f"  Authority ID: {authority.authority_id}")
    
    return authority


def seed_policies_base(db: Session) -> list[Policy]:
    """
    Crea políticas base conservadoras para arranque del sistema.
    
    Políticas creadas:
      1. Límite QR vigencia: 7 días
      2. Límite tenants por first tier: 5
      3. Límite usuarios por tenant: 100
    """
    print("\n[2] Creando POLÍTICAS BASE...")
    
    policies = []
    
    # POLÍTICA 1: Vigencia máxima de QR
    policy_qr = crear_policy(
        db=db,
        nombre="Límite Vigencia QR (Estándar)",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="generar_qr",
        limites={"max_dias_vigencia": 7},
        metadata={
            "bootstrap": True,
            "descripcion": "QR válidos hasta 7 días (seguridad)"
        }
    )
    policies.append(policy_qr)
    print(f"✓ Policy QR vigencia: máximo 7 días")
    
    # POLÍTICA 2: Máximo tenants por first tier
    policy_tenants = crear_policy(
        db=db,
        nombre="Límite Tenants First Tier (Plan Estándar)",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_tenant",
        limites={"max_count": 5},
        metadata={
            "bootstrap": True,
            "descripcion": "Máximo 5 condominios por first tier"
        }
    )
    policies.append(policy_tenants)
    print(f"✓ Policy tenants: máximo 5 por first tier")
    
    # POLÍTICA 3: Máximo usuarios por tenant
    policy_usuarios = crear_policy(
        db=db,
        nombre="Límite Usuarios por Tenant (Plan Estándar)",
        ambito=PolicyScope.GLOBAL,
        accion_objetivo="crear_usuario",
        limites={"max_usuarios": 100},
        metadata={
            "bootstrap": True,
            "descripcion": "Máximo 100 usuarios por condominio"
        }
    )
    policies.append(policy_usuarios)
    print(f"✓ Policy usuarios: máximo 100 por tenant")
    
    return policies


def seed_first_tier_demo(db_core: Session, db_gov: Session, admin_global: Authority) -> Authority | None:
    """
    (OPCIONAL) Crea un first tier de demostración.
    
    Solo si existe un condominio y un usuario para asignar.
    """
    print("\n[3] Verificando posibilidad de first tier demo...")
    
    # Buscar primer condominio en CORE
    from backend.db.core import Condominio
    condominio = db_core.query(Condominio).first()
    
    if not condominio:
        print("⚠ No hay condominios en la BD, omitiendo first tier demo")
        return None
    
    # Buscar primer usuario no-admin en CORE
    usuario = db_core.query(Usuario).filter(
        Usuario.rol != "MSP_ADMIN"
    ).first()
    
    if not usuario:
        print("⚠ No hay usuarios no-admin, omitiendo first tier demo")
        return None
    
    # Verificar si ya existe authority en GOV
    existing = db_gov.query(Authority).filter(
        Authority.identity_id == usuario.usuario_id,
        Authority.tipo == AuthorityType.FIRST_TIER,
        Authority.tenant_id == condominio.condominio_id
    ).first()
    
    if existing:
        print(f"✓ First tier ya existe para {usuario.email} en {condominio.nombre}")
        return existing
    
    # Crear first tier en GOV
    first_tier = crear_authority(
        db=db_gov,
        identity=usuario,
        tipo=AuthorityType.FIRST_TIER,
        tenant_id=condominio.condominio_id,
        metadata={
            "bootstrap": True,
            "demo": True,
            "created_by": "seed_script"
        }
    )
    
    print(f"✓ First tier demo creado:")
    print(f"  Usuario: {usuario.email}")
    print(f"  Tenant: {condominio.nombre}")
    print(f"  Authority ID: {first_tier.authority_id}")
    
    return first_tier


def verificar_migracion(db: Session) -> bool:
    """
    Verifica que las tablas de AUP_GOV existen.
    """
    try:
        # Intentar consulta simple
        db.query(Authority).count()
        db.query(Policy).count()
        return True
    except Exception as e:
        print(f"\n❌ ERROR: Tablas de AUP_GOV no existen")
        print(f"   Ejecutar primero: database/migration_04_gov.sql")
        print(f"   Error: {str(e)}")
        return False


def main():
    """
    Ejecuta seed de gobierno inicial.
    """
    print("═" * 80)
    print("SEED AUP_GOV: Bootstrap de Gobierno")
    print("═" * 80)
    
    # ✅ Sesiones separadas por dominio
    db_core = SessionLocal_CORE()
    db_gov = SessionLocal_GOV()
    
    try:
        # Verificar migración GOV
        if not verificar_migracion(db_gov):
            sys.exit(1)
        
        # [1] Authority Global (necesita CORE para leer usuario)
        admin_global = seed_authority_global(db_core, db_gov)
        
        # [2] Políticas Base (solo GOV)
        policies = seed_policies_base(db_gov)
        
        # [3] First Tier Demo (necesita CORE y GOV)
        first_tier = seed_first_tier_demo(db_core, db_gov, admin_global)
        
        # Resumen
        print("\n" + "═" * 80)
        print("✅ BOOTSTRAP COMPLETADO")
        print("═" * 80)
        print(f"Authorities creadas: 1 GLOBAL{' + 1 FIRST_TIER' if first_tier else ''}")
        print(f"Políticas creadas: {len(policies)}")
        print("\nSistema GOBERNADO. Próximo paso: integrar en routers.")
        print("═" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR durante seed: {str(e)}")
        db_core.rollback()
        db_gov.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        db_core.close()
        db_gov.close()


if __name__ == "__main__":
    main()
