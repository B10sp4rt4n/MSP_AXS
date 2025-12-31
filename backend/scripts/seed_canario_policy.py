"""
═══════════════════════════════════════════════════════════════════════════════
Seed de Política AUP para Endpoint Canario
═══════════════════════════════════════════════════════════════════════════════

PROPÓSITO:
  Cargar política de prueba para que el endpoint canario pueda demostrar:
    - GOV PERMITE (cuando dias_vigencia <= 3)
    - GOV DENIEGA (cuando dias_vigencia > 3)

POLÍTICA CARGADA:
  accion: generar_qr
  limite: max_qr_dias = 3
  ambito: GLOBAL
  estado: ACTIVO

USO:
  python -m backend.scripts.seed_canario_policy

═══════════════════════════════════════════════════════════════════════════════
"""

from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from backend.db.gov import get_gov_db, Authority, Policy
from backend.db.core import get_core_db, Usuario


def seed_canario_policy():
    """
    Carga política de prueba para endpoint canario.
    """
    db_gov: Session = next(get_gov_db())
    db_core: Session = next(get_core_db())
    
    try:
        # ─────────────────────────────────────────────────────────────────
        # 1. Buscar o crear Authority (poder que gobierna)
        # ─────────────────────────────────────────────────────────────────
        # Buscar usuario admin para asignar como identity
        admin = db_core.query(Usuario).filter(Usuario.rol == "SUPERADMIN").first()
        
        if not admin:
            print("⚠️  No existe SUPERADMIN. Buscando primer usuario...")
            admin = db_core.query(Usuario).first()
        
        if not admin:
            print("❌ No hay usuarios en el sistema. Crear usuario primero.")
            return
        
        # Buscar authority existente para este usuario
        from backend.db.gov.models import AuthorityType
        
        authority = db_gov.query(Authority).filter(
            Authority.identity_id == admin.usuario_id,
            Authority.tipo == AuthorityType.GLOBAL
        ).first()
        
        if not authority:
            authority = Authority(
                authority_id=str(uuid.uuid4()),
                identity_id=admin.usuario_id,
                tipo=AuthorityType.GLOBAL,
                tenant_id=None,  # GLOBAL no tiene tenant
                estado="ACTIVO",
                metadata_json={"descripcion": "Authority para gobierno de endpoint canario"}
            )
            db_gov.add(authority)
            db_gov.commit()
            print(f"✅ Authority creada: {authority.authority_id} (identity={admin.usuario_id})")
        else:
            print(f"✅ Authority existente: {authority.authority_id} (identity={admin.usuario_id})")
        
        # ─────────────────────────────────────────────────────────────────
        # 2. Crear política de prueba
        # ─────────────────────────────────────────────────────────────────
        existing_policy = db_gov.query(Policy).filter(
            Policy.nombre == "LIMITE_QR_CANARIO"
        ).first()
        
        if existing_policy:
            print(f"⚠️  Política ya existe: {existing_policy.policy_id}")
            print(f"    Límites: {existing_policy.limites}")
            return
        
        policy = Policy(
            policy_id=str(uuid.uuid4()),
            nombre="LIMITE_QR_CANARIO",
            descripcion="Política de prueba para endpoint canario: max 3 días de vigencia QR",
            accion_objetivo="generar_qr",
            ambito="GLOBAL",  # Aplica a todos los tenants
            target_tenant_id=None,
            limites={
                "max_qr_dias": 3,  # ← Restricción: máximo 3 días
                "descripcion": "Limita vigencia de QR a 3 días para demostración AUP"
            },
            estado="ACTIVO",
            valida_desde=datetime.utcnow(),
            valida_hasta=None  # Sin fecha de expiración
        )
        
        db_gov.add(policy)
        db_gov.commit()
        
        print("═══════════════════════════════════════════════════════════════")
        print("✅ Política de canario cargada exitosamente")
        print("═══════════════════════════════════════════════════════════════")
        print(f"Policy ID: {policy.policy_id}")
        print(f"Nombre: {policy.nombre}")
        print(f"Acción: {policy.accion_objetivo}")
        print(f"Límites: {policy.limites}")
        print(f"Ambito: {policy.ambito}")
        print("═══════════════════════════════════════════════════════════════")
        print("")
        print("🧪 CASOS DE PRUEBA:")
        print("")
        print("✅ DEBE PERMITIR:")
        print("  POST /qr/generar_gobernado")
        print('  {"visitante_nombre": "Juan", "tenant_id": "condo_a", "dias_vigencia": 2}')
        print("")
        print("🚫 DEBE DENEGAR:")
        print("  POST /qr/generar_gobernado")
        print('  {"visitante_nombre": "Juan", "tenant_id": "condo_a", "dias_vigencia": 7}')
        print("")
        print("Axioma validado: Gobierno precede a operación")
        print("═══════════════════════════════════════════════════════════════")
    
    except Exception as e:
        print(f"❌ Error cargando política: {e}")
        db_gov.rollback()
        raise
    
    finally:
        db_gov.close()
        db_core.close()


if __name__ == "__main__":
    seed_canario_policy()
