#!/usr/bin/env python3
"""Crear usuario guardia para demo"""
import sys
sys.path.insert(0, '/workspaces/MSP_AXS')

from backend.db.core import SessionLocal_CORE, Usuario
from passlib.context import CryptContext
from datetime import datetime
import uuid

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

db = SessionLocal_CORE()

# Eliminar guardia anterior si existe
db.query(Usuario).filter(Usuario.email == 'guardia@condoriente.com').delete()

# Crear guardia
guardia = Usuario(
    usuario_id=f'USR-{uuid.uuid4().hex[:8].upper()}',
    email='guardia@condoriente.com',
    nombre='Guardia Demo',
    password_hash=pwd_context.hash('guardia123'),
    rol='GUARDIA',
    condominio_id='COND-001',
    created_at=datetime.utcnow()
)

db.add(guardia)
db.commit()
print(f'✅ Guardia creado: {guardia.usuario_id} ({guardia.email})')
db.close()
