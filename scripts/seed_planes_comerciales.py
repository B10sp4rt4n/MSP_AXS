#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
SEED: Planes Comerciales Iniciales
═══════════════════════════════════════════════════════════════════════════════

Crea usuarios de ejemplo con diferentes planes asignados para demostración.

Axioma: Un usuario sin plan explícito = denegado (safe by default).
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from backend.db.connection import SessionLocal
from backend.db.models import Usuario
from backend.core.gov.plans import (
    PlanType,
    asignar_plan_con_evento,
    obtener_plan_actual
)
from datetime import datetime


def seed_planes_demo(db: Session):
    """
    Asigna planes de demostración a usuarios existentes.
    """
    print("\n═══════════════════════════════════════════════════════════════════")
    print("SEED: Planes Comerciales Demo")
    print("═══════════════════════════════════════════════════════════════════\n")
    
    # Buscar admin global para ejecutar asignaciones
    admin = db.query(Usuario).filter(
        Usuario.rol_base == "MSP_ADMIN"
    ).first()
    
    if not admin:
        print("❌ ERROR: No hay MSP_ADMIN para ejecutar asignaciones")
        print("   Ejecutar primero seed_gov_bootstrap.py")
        return
    
    # Token mock (en producción vendría de login)
    mock_token = "mock_token_for_seed"
    
    print(f"[Admin ejecutor]: {admin.email}\n")
    
    # ═══════════════════════════════════════════════════════════════════════
    # PLAN FREE: Asignar a primer usuario no-admin
    # ═══════════════════════════════════════════════════════════════════════
    usuario_free = db.query(Usuario).filter(
        Usuario.rol_base != "MSP_ADMIN"
    ).first()
    
    if usuario_free:
        print("[1] Asignando Plan FREE...")
        _, summary = asignar_plan_con_evento(
            db=db,
            ejecutor=admin,
            session_token=mock_token,
            target_user=usuario_free,
            plan_type=PlanType.FREE
        )
        
        print(f"  ✓ Usuario: {usuario_free.email}")
        print(f"  ✓ Plan: FREE")
        print(f"  ✓ Límites: {summary['limites']}")
        print(f"  ✓ Políticas creadas: {summary['politicas_creadas']}\n")
    else:
        print("⚠ No hay usuarios para asignar Plan FREE\n")
    
    # ═══════════════════════════════════════════════════════════════════════
    # PLAN PRO: Asignar a segundo usuario
    # ═══════════════════════════════════════════════════════════════════════
    usuarios = db.query(Usuario).filter(
        Usuario.rol_base != "MSP_ADMIN"
    ).all()
    
    if len(usuarios) > 1:
        usuario_pro = usuarios[1]
        print("[2] Asignando Plan PRO...")
        _, summary = asignar_plan_con_evento(
            db=db,
            ejecutor=admin,
            session_token=mock_token,
            target_user=usuario_pro,
            plan_type=PlanType.PRO
        )
        
        print(f"  ✓ Usuario: {usuario_pro.email}")
        print(f"  ✓ Plan: PRO")
        print(f"  ✓ Límites: {summary['limites']}")
        print(f"  ✓ Políticas creadas: {summary['politicas_creadas']}\n")
    else:
        print("⚠ No hay segundo usuario para Plan PRO\n")
    
    # ═══════════════════════════════════════════════════════════════════════
    # PLAN ENTERPRISE: Asignar al admin (self-upgrade)
    # ═══════════════════════════════════════════════════════════════════════
    print("[3] Asignando Plan ENTERPRISE al admin...")
    _, summary = asignar_plan_con_evento(
        db=db,
        ejecutor=admin,
        session_token=mock_token,
        target_user=admin,
        plan_type=PlanType.ENTERPRISE
    )
    
    print(f"  ✓ Usuario: {admin.email}")
    print(f"  ✓ Plan: ENTERPRISE")
    print(f"  ✓ Límites: {summary['limites']}")
    print(f"  ✓ Políticas creadas: {summary['politicas_creadas']}\n")
    
    # ═══════════════════════════════════════════════════════════════════════
    # RESUMEN
    # ═══════════════════════════════════════════════════════════════════════
    print("═══════════════════════════════════════════════════════════════════")
    print("✅ PLANES COMERCIALES ASIGNADOS")
    print("═══════════════════════════════════════════════════════════════════")
    
    # Contar políticas por plan
    from backend.db.models import Policy
    
    free_count = db.query(Policy).filter(
        Policy.metadata["plan_type"].astext == "free"
    ).count()
    
    pro_count = db.query(Policy).filter(
        Policy.metadata["plan_type"].astext == "pro"
    ).count()
    
    enterprise_count = db.query(Policy).filter(
        Policy.metadata["plan_type"].astext == "enterprise"
    ).count()
    
    print(f"Plan FREE:       {free_count} políticas activas")
    print(f"Plan PRO:        {pro_count} políticas activas")
    print(f"Plan ENTERPRISE: {enterprise_count} políticas activas")
    print("\nSistema listo para validar restricciones por plan.")
    print("═══════════════════════════════════════════════════════════════════\n")


def main():
    db = SessionLocal()
    
    try:
        seed_planes_demo(db)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
