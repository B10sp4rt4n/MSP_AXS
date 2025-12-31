"""
═══════════════════════════════════════════════════════════════════════════════
Seed de Micro-Piloto AUP — Casos Exhaustivos
═══════════════════════════════════════════════════════════════════════════════

PROPÓSITO:
  Cargar datos de prueba para verificar que AUP responde automáticamente
  sin intervención humana.

ESCENARIO:
  - 1 condominio: "Torre del Mar"
  - 1 residente: María (tiene scope en el condominio)
  - 1 vigilante: Carlos (tiene scope en el condominio)
  - 1 política: QR máximo 3 días

CASOS A PROBAR:
  1. ✅ Permitido: Residente genera QR 2 días
  2. 🚫 Denegado por política: Residente genera QR 7 días
  3. 🚫 Denegado por scope: Residente intenta generar QR en otro condominio
  4. 🚫 Denegado por sesión: Request sin token
  5. 🚫 Intento de bypass: Ejecutar negocio sin GOV

OBJETIVO:
  Confirmar que AUP responde solo, sin necesitar que el desarrollador piense.

═══════════════════════════════════════════════════════════════════════════════
"""

from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import bcrypt

from backend.db.core import get_core_db, Usuario, Condominio, UserTenantScope, AccessLevel, ScopeStatus
from backend.db.gov import get_gov_db, Authority, Policy, AuthorityType, GovStatus, PolicyScope


def seed_micropiloto():
    """
    Carga datos para micro-piloto AUP.
    """
    db_core: Session = next(get_core_db())
    db_gov: Session = next(get_gov_db())
    
    try:
        print("═══════════════════════════════════════════════════════════════")
        print("🚀 SEED MICRO-PILOTO AUP")
        print("═══════════════════════════════════════════════════════════════\n")
        
        # ─────────────────────────────────────────────────────────────────
        # 1. Crear condominio ficticio
        # ─────────────────────────────────────────────────────────────────
        condominio_id = str(uuid.uuid4())
        condominio = Condominio(
            condominio_id=condominio_id,
            nombre="Torre del Mar",
            msp_id="msp_test"
        )
        db_core.add(condominio)
        db_core.commit()
        print(f"✅ Condominio creado: {condominio.nombre} (id={condominio_id})")
        
        # ─────────────────────────────────────────────────────────────────
        # 2. Crear residente (verificar si ya existe)
        # ─────────────────────────────────────────────────────────────────
        residente_existing = db_core.query(Usuario).filter(Usuario.email == 'maria@torredelmar.com').first()
        
        if residente_existing:
            print(f"⚠️  Residente ya existe, usando existente: {residente_existing.email}")
            residente = residente_existing
            residente_id = residente.usuario_id
        else:
            password_hash = bcrypt.hashpw('residente123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            residente_id = str(uuid.uuid4())
            residente = Usuario(
                usuario_id=residente_id,
                nombre='María López',
                email='maria@torredelmar.com',
                password_hash=password_hash,
                rol='RESIDENTE',
                msp_id='msp_test',
                condominio_id=condominio_id,
                casa_unidad='101'
            )
            db_core.add(residente)
            db_core.commit()
            print(f"✅ Residente creado: {residente.nombre} (email={residente.email})")
        
        # ─────────────────────────────────────────────────────────────────
        # 3. Crear vigilante (verificar si ya existe)
        # ─────────────────────────────────────────────────────────────────
        vigilante_existing = db_core.query(Usuario).filter(Usuario.email == 'carlos@torredelmar.com').first()
        
        if vigilante_existing:
            print(f"⚠️  Vigilante ya existe, usando existente: {vigilante_existing.email}")
            vigilante = vigilante_existing
            vigilante_id = vigilante.usuario_id
        else:
            password_hash_vigilante = bcrypt.hashpw('vigilante123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            vigilante_id = str(uuid.uuid4())
            vigilante = Usuario(
                usuario_id=vigilante_id,
                nombre='Carlos Ramírez',
                email='carlos@torredelmar.com',
                password_hash=password_hash_vigilante,
                rol='GUARDIA',
                msp_id='msp_test',
                condominio_id=condominio_id
            )
            db_core.add(vigilante)
            db_core.commit()
            print(f"✅ Vigilante creado: {vigilante.nombre} (email={vigilante.email})")
        
        # ─────────────────────────────────────────────────────────────────
        # 4. Crear scopes (alcances en el condominio)
        # ─────────────────────────────────────────────────────────────────
        # Scope para residente
        scope_residente = UserTenantScope(
            usuario_id=residente_id,
            tenant_id=condominio_id,
            access_level=AccessLevel.RESIDENTE,
            estado=ScopeStatus.ACTIVO
        )
        db_core.add(scope_residente)
        
        # Scope para vigilante
        scope_vigilante = UserTenantScope(
            usuario_id=vigilante_id,
            tenant_id=condominio_id,
            access_level=AccessLevel.GUARDIA,
            estado=ScopeStatus.ACTIVO
        )
        db_core.add(scope_vigilante)
        
        db_core.commit()
        print(f"✅ Scopes creados: Residente y Vigilante en {condominio.nombre}")
        
        # ─────────────────────────────────────────────────────────────────
        # 5. Crear authority y política restrictiva
        # ─────────────────────────────────────────────────────────────────
        # Authority GLOBAL (admin del sistema ya existe, lo buscamos)
        admin = db_core.query(Usuario).filter(Usuario.rol == "SUPERADMIN").first()
        
        if admin:
            authority = Authority(
                authority_id=str(uuid.uuid4()),
                identity_id=admin.usuario_id,
                tipo=AuthorityType.GLOBAL,
                tenant_id=None,
                estado=GovStatus.ACTIVO,
                metadata_json={"descripcion": "Authority para micro-piloto"}
            )
            db_gov.add(authority)
            db_gov.commit()
            print(f"✅ Authority creada para admin: {admin.email}")
        
        # Política: QR máximo 3 días
        policy_id = str(uuid.uuid4())
        policy = Policy(
            policy_id=policy_id,
            nombre="LIMITE_QR_MICROPILOTO",
            descripcion="Micro-piloto: QR máximo 3 días de vigencia",
            accion_objetivo="generar_qr",
            ambito=PolicyScope.GLOBAL,
            target_tenant_id=None,
            limites={
                "max_qr_dias": 3,
                "descripcion": "QR no puede tener más de 3 días de vigencia"
            },
            estado=GovStatus.ACTIVO,
            valida_desde=datetime.utcnow(),
            valida_hasta=None
        )
        db_gov.add(policy)
        db_gov.commit()
        print(f"✅ Política creada: {policy.nombre} (max_qr_dias=3)")
        
        # ─────────────────────────────────────────────────────────────────
        # 6. Crear segundo condominio para test de scope
        # ─────────────────────────────────────────────────────────────────
        condominio2_id = str(uuid.uuid4())
        condominio2 = Condominio(
            condominio_id=condominio2_id,
            nombre="Edificio Los Pinos",
            msp_id="msp_test"
        )
        db_core.add(condominio2)
        db_core.commit()
        print(f"✅ Condominio 2 creado: {condominio2.nombre} (sin scope para residente)")
        
        print("\n═══════════════════════════════════════════════════════════════")
        print("✅ SEED COMPLETADO")
        print("═══════════════════════════════════════════════════════════════\n")
        
        print("📋 DATOS DEL MICRO-PILOTO:\n")
        print(f"Condominio 1: {condominio.nombre}")
        print(f"  ID: {condominio_id}")
        print()
        print(f"Condominio 2: {condominio2.nombre}")
        print(f"  ID: {condominio2_id}")
        print(f"  (Residente NO tiene scope aquí)")
        print()
        print(f"Residente: {residente.nombre}")
        print(f"  Email: {residente.email}")
        print(f"  Password: residente123")
        print(f"  Scope: ✅ {condominio.nombre} (RESIDENTE)")
        print()
        print(f"Vigilante: {vigilante.nombre}")
        print(f"  Email: {vigilante.email}")
        print(f"  Password: vigilante123")
        print(f"  Scope: ✅ {condominio.nombre} (GUARDIA)")
        print()
        print(f"Política: {policy.nombre}")
        print(f"  Límite: max_qr_dias = 3")
        print(f"  Ámbito: GLOBAL")
        print()
        
        print("═══════════════════════════════════════════════════════════════")
        print("🧪 CASOS DE PRUEBA PREPARADOS:")
        print("═══════════════════════════════════════════════════════════════\n")
        
        print("1️⃣  CASO PERMITIDO:")
        print(f"   Residente genera QR 2 días en {condominio.nombre}")
        print(f"   → Debe permitir (< 3 días)")
        print()
        
        print("2️⃣  CASO DENEGADO POR POLÍTICA:")
        print(f"   Residente genera QR 7 días en {condominio.nombre}")
        print(f"   → Debe denegar (> 3 días)")
        print()
        
        print("3️⃣  CASO DENEGADO POR SCOPE:")
        print(f"   Residente genera QR en {condominio2.nombre}")
        print(f"   → Debe denegar (sin scope en ese condominio)")
        print()
        
        print("4️⃣  CASO DENEGADO POR SESIÓN:")
        print(f"   Request sin token JWT")
        print(f"   → Debe denegar (AUP-01 bloquea)")
        print()
        
        print("5️⃣  CASO BYPASS:")
        print(f"   Endpoint sin evaluar GOV")
        print(f"   → Debe fallar (AUP-02 bloquea)")
        print()
        
        print("═══════════════════════════════════════════════════════════════")
        print("✅ Ejecutar: python -m backend.scripts.test_micropiloto")
        print("═══════════════════════════════════════════════════════════════")
        
        return {
            "condominio1_id": condominio_id,
            "condominio1_nombre": condominio.nombre,
            "condominio2_id": condominio2_id,
            "condominio2_nombre": condominio2.nombre,
            "residente_email": residente.email,
            "vigilante_email": vigilante.email,
            "policy_id": policy_id
        }
    
    except Exception as e:
        print(f"❌ Error en seed: {e}")
        db_core.rollback()
        db_gov.rollback()
        raise
    
    finally:
        db_core.close()
        db_gov.close()


if __name__ == "__main__":
    seed_micropiloto()
