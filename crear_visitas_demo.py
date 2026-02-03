"""
Script para crear visitas de demostración en modo guardia
"""
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.db.core import get_core_db
from backend.db.core.models import Visita, Condominio, Usuario
import secrets

# Datos de demostración
VISITAS_DEMO = [
    {
        "nombre_visitante": "Juan Pérez",
        "cedula_visitante": "1234567890",
        "telefono_visitante": "+593991234567",
        "tipo_visita": "INVITADO_REGISTRADO",
        "estado": "PENDIENTE",
        "vigencia_desde": datetime.now(),
        "vigencia_hasta": datetime.now() + timedelta(hours=4)
    },
    {
        "nombre_visitante": "María González",
        "cedula_visitante": "0987654321",
        "telefono_visitante": "+593987654321",
        "tipo_visita": "INVITADO_REGISTRADO",
        "estado": "ACTIVA",
        "vigencia_desde": datetime.now() - timedelta(hours=1),
        "vigencia_hasta": datetime.now() + timedelta(hours=3)
    },
    {
        "nombre_visitante": "Carlos Rodríguez",
        "cedula_visitante": "1122334455",
        "telefono_visitante": "+593998877665",
        "tipo_visita": "DELIVERY",
        "estado": "PENDIENTE",
        "vigencia_desde": datetime.now(),
        "vigencia_hasta": datetime.now() + timedelta(minutes=30)
    },
    {
        "nombre_visitante": "Ana Martínez",
        "cedula_visitante": "5544332211",
        "telefono_visitante": "+593991122334",
        "tipo_visita": "INVITADO_REGISTRADO",
        "estado": "COMPLETADA",
        "vigencia_desde": datetime.now() - timedelta(hours=2),
        "vigencia_hasta": datetime.now() - timedelta(hours=1),
        "fecha_entrada": datetime.now() - timedelta(hours=2),
        "fecha_salida": datetime.now() - timedelta(hours=1)
    },
    {
        "nombre_visitante": "Roberto Silva",
        "cedula_visitante": "6677889900",
        "telefono_visitante": "+593996655443",
        "tipo_visita": "SERVICIO",
        "estado": "ACTIVA",
        "vigencia_desde": datetime.now() - timedelta(minutes=30),
        "vigencia_hasta": datetime.now() + timedelta(hours=2),
        "fecha_entrada": datetime.now() - timedelta(minutes=30)
    }
]

def crear_visitas():
    db = next(get_core_db())
    
    try:
        # Obtener primer condominio disponible
        condominio = db.query(Condominio).first()
        
        if not condominio:
            print("❌ No hay condominios en la BD")
            return
        
        condominio_id = condominio.condominio_id
        print(f"📍 Usando condominio: {condominio_id}\n")
        
        # Obtener primer usuario residente
        usuario = db.query(Usuario).filter(Usuario.rol == 'RESIDENTE').first()
        
        if not usuario:
            print("❌ No hay usuarios residentes en la BD")
            return
        
        usuario_id = usuario.usuario_id
        casa_unidad = usuario.casa_unidad
        print(f"🏠 Usando residente: {usuario_id} - Casa {casa_unidad}\n")
        
        print("="*60)
        print("CREANDO VISITAS DE DEMOSTRACIÓN")
        print("="*60)
        
        for i, visita_data in enumerate(VISITAS_DEMO, 1):
            token_qr = f"QR-{secrets.token_urlsafe(8)}"
            visita_id = f"vis_{secrets.token_urlsafe(6)}"
            
            visita = Visita(
                visita_id=visita_id,
                condominio_id=condominio_id,
                casa_unidad=casa_unidad or "A-101",
                qr_token=token_qr,
                tipo_visitante=visita_data['tipo_visita'],
                estado=visita_data['estado'],
                nombre_visitante=visita_data['nombre_visitante'],
                telefono=visita_data.get('telefono_visitante'),
                vigencia=visita_data['vigencia_hasta'],
                qr_vigencia=visita_data['vigencia_hasta'],
                hora_entrada=visita_data.get('fecha_entrada'),
                hora_salida=visita_data.get('fecha_salida'),
                entrada_registrada_en=visita_data.get('fecha_entrada'),
                salida_registrada_en=visita_data.get('fecha_salida')
            )
            
            db.add(visita)
            
            print(f"{i}. {visita_data['nombre_visitante']}")
            print(f"   Tipo: {visita_data['tipo_visita']}")
            print(f"   Estado: {visita_data['estado']}")
            print(f"   Token: {token_qr}")
            print()
        
        db.commit()
        
        # Verificar
        total = db.query(Visita).count()
        
        print("="*60)
        print(f"✅ {len(VISITAS_DEMO)} visitas creadas exitosamente")
        print(f"📊 Total de visitas en BD: {total}")
        print("="*60)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    crear_visitas()
