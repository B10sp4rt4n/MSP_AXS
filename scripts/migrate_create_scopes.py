"""
Script de migración: Crear scopes iniciales desde usuarios existentes.

Este script crea registros AUP_SCOPE para usuarios existentes
basándose en su campo condominio_id actual.
"""

from sqlalchemy.orm import Session
from backend.db.connection import SessionLocal
from backend.db.models import Usuario, UserTenantScope, AccessLevel, ScopeStatus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration.scope")


def migrar_usuarios_a_scopes(db: Session):
    """
    Crea AUP_SCOPE para usuarios que tienen condominio_id.
    
    Lógica:
      - Si usuario tiene condominio_id → crear scope en ese tenant
      - access_level según rol:
          MSP_ADMIN → msp_admin
          ADMIN_CONDOMINIO → admin_condominio
          GUARDIA → guardia
          RESIDENTE → residente
    """
    usuarios = db.query(Usuario).filter(Usuario.condominio_id.isnot(None)).all()
    
    logger.info(f"Encontrados {len(usuarios)} usuarios con condominio_id")
    
    creados = 0
    for usuario in usuarios:
        # Verificar si ya tiene scope
        scope_existente = db.query(UserTenantScope).filter(
            UserTenantScope.usuario_id == usuario.usuario_id,
            UserTenantScope.tenant_id == usuario.condominio_id
        ).first()
        
        if scope_existente:
            logger.info(f"Scope ya existe para {usuario.usuario_id} en {usuario.condominio_id}")
            continue
        
        # Mapear rol a access_level
        access_level_map = {
            "MSP_ADMIN": AccessLevel.MSP_ADMIN,
            "ADMIN_CONDOMINIO": AccessLevel.ADMIN_CONDOMINIO,
            "GUARDIA": AccessLevel.GUARDIA,
            "RESIDENTE": AccessLevel.RESIDENTE,
        }
        
        access_level = access_level_map.get(usuario.rol, AccessLevel.RESIDENTE)
        
        # Crear scope
        scope = UserTenantScope(
            usuario_id=usuario.usuario_id,
            tenant_id=usuario.condominio_id,
            access_level=access_level,
            estado=ScopeStatus.ACTIVO
        )
        
        db.add(scope)
        creados += 1
        logger.info(
            f"Creado scope: usuario={usuario.usuario_id} "
            f"tenant={usuario.condominio_id} nivel={access_level.value}"
        )
    
    db.commit()
    logger.info(f"Migración completada: {creados} scopes creados")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        migrar_usuarios_a_scopes(db)
    finally:
        db.close()
