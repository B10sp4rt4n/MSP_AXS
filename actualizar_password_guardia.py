#!/usr/bin/env python3
"""
Script para actualizar la contraseña del guardia demo
"""
import sqlite3
import bcrypt

# Conectar a la base de datos
conn = sqlite3.connect('axs_core.db')
cursor = conn.cursor()

# Generar hash de la contraseña
password = "demo123"
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Actualizar contraseña
cursor.execute(
    'UPDATE usuarios SET password_hash = ? WHERE email = ?',
    (password_hash, 'guardia@demo.com')
)

conn.commit()

if cursor.rowcount > 0:
    print('✅ Contraseña actualizada exitosamente')
    print('📧 Email: guardia@demo.com')
    print('🔒 Password: demo123')
else:
    print('❌ No se encontró el usuario guardia@demo.com')

conn.close()
