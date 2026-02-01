#!/usr/bin/env python3
"""
Test de configuración de proveedores externos
Verifica que todas las credenciales estén correctamente configuradas
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def test_twilio():
    """Test configuración Twilio SMS"""
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not all([account_sid, auth_token, phone_number]):
            print("⚠️  Twilio: Variables no configuradas (opcional)")
            return False
        
        # Intentar importar y verificar formato
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        
        # Verificar formato de Account SID
        if not account_sid.startswith("AC"):
            print("❌ Twilio: Account SID inválido (debe empezar con 'AC')")
            return False
        
        print("✅ Twilio: Configurado correctamente")
        print(f"   - Account SID: {account_sid[:10]}...")
        print(f"   - Phone: {phone_number}")
        return True
        
    except ImportError:
        print("❌ Twilio: SDK no instalado (pip install twilio)")
        return False
    except Exception as e:
        print(f"❌ Twilio: Error - {str(e)}")
        return False


def test_sendgrid():
    """Test configuración SendGrid Email"""
    try:
        api_key = os.getenv("SENDGRID_API_KEY")
        email_from = os.getenv("EMAIL_FROM")
        
        if not all([api_key, email_from]):
            print("⚠️  SendGrid: Variables no configuradas (opcional)")
            return False
        
        # Intentar importar
        from sendgrid import SendGridAPIClient
        sg = SendGridAPIClient(api_key)
        
        # Verificar formato de API Key
        if not api_key.startswith("SG."):
            print("❌ SendGrid: API Key inválida (debe empezar con 'SG.')")
            return False
        
        print("✅ SendGrid: Configurado correctamente")
        print(f"   - API Key: {api_key[:15]}...")
        print(f"   - From: {email_from}")
        return True
        
    except ImportError:
        print("❌ SendGrid: SDK no instalado (pip install sendgrid)")
        return False
    except Exception as e:
        print(f"❌ SendGrid: Error - {str(e)}")
        return False


def test_whatsapp():
    """Test configuración WhatsApp Business API"""
    try:
        phone_id = os.getenv("WHATSAPP_BUSINESS_PHONE_ID")
        access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        
        if not all([phone_id, access_token]):
            print("⚠️  WhatsApp: Variables no configuradas (opcional)")
            return False
        
        # Verificar que requests esté instalado
        import requests
        
        # Verificar longitud mínima del token
        if len(access_token) < 50:
            print("❌ WhatsApp: Access Token parece inválido (muy corto)")
            return False
        
        print("✅ WhatsApp Business: Configurado correctamente")
        print(f"   - Phone ID: {phone_id}")
        print(f"   - Token: {access_token[:20]}...")
        return True
        
    except ImportError:
        print("❌ WhatsApp: requests no instalado (pip install requests)")
        return False
    except Exception as e:
        print(f"❌ WhatsApp: Error - {str(e)}")
        return False


def test_cloudinary():
    """Test configuración Cloudinary"""
    try:
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            print("❌ Cloudinary: Variables no configuradas (REQUERIDO)")
            return False
        
        # Intentar importar y configurar
        import cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        print("✅ Cloudinary: Configurado correctamente")
        print(f"   - Cloud Name: {cloud_name}")
        print(f"   - API Key: {api_key[:10]}...")
        return True
        
    except ImportError:
        print("❌ Cloudinary: SDK no instalado (pip install cloudinary)")
        return False
    except Exception as e:
        print(f"❌ Cloudinary: Error - {str(e)}")
        return False


def test_frontend_url():
    """Test configuración Frontend URL"""
    frontend_url = os.getenv("FRONTEND_URL")
    
    if not frontend_url:
        print("⚠️  FRONTEND_URL: No configurada (usar por defecto)")
        return False
    
    if not frontend_url.startswith(("http://", "https://")):
        print("❌ FRONTEND_URL: Debe empezar con http:// o https://")
        return False
    
    print("✅ Frontend URL: Configurada correctamente")
    print(f"   - URL: {frontend_url}")
    return True


def test_slack():
    """Verifica configuración de Slack"""
    print("\n🔔 SLACK (Notificaciones)")
    print("=" * 60)
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    canal = os.getenv("SLACK_CHANNEL", "#seguridad")
    
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL no configurado")
        print("   Instrucciones: docs/PROVEEDORES_SETUP.md sección 4")
        return False
    
    if not webhook_url.startswith("https://hooks.slack.com"):
        print("❌ SLACK_WEBHOOK_URL inválido")
        print(f"   Formato: {webhook_url}")
        return False
    
    print("✅ Webhook configurado")
    print(f"   Canal: {canal}")
    print(f"   URL: {webhook_url[:50]}...")
    return True


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*60)
    print("🔍 VERIFICACIÓN DE PROVEEDORES EXTERNOS")
    print("="*60 + "\n")
    
    results = {
        "Twilio (SMS)": test_twilio(),
        "SendGrid (Email)": test_sendgrid(),
        "WhatsApp Business": test_whatsapp(),
        "Slack (Notificaciones)": test_slack(),
        "Cloudinary (Storage)": test_cloudinary(),
        "Frontend URL": test_frontend_url(),
    }
    
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60 + "\n")
    
    configured = sum(1 for v in results.values() if v)
    total = len(results)
    
    for provider, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {provider}")
    
    print(f"\n📈 {configured}/{total} proveedores configurados correctamente\n")
    
    # Verificar críticos
    if not results.get("Cloudinary (Storage)"):
        print("⚠️  WARNING: Cloudinary NO está configurado (REQUERIDO para evidencias)")
        print("   Sin Cloudinary, el sistema NO podrá guardar fotos de visitas.\n")
        return 1
    
    if configured == total:
        print("🎉 ¡Todos los proveedores están configurados!\n")
        return 0
    elif configured >= 2:  # Al menos Cloudinary + 1 más
        print("✅ Configuración mínima alcanzada (sistema operativo)\n")
        return 0
    else:
        print("⚠️  Configuración insuficiente. Revisa la documentación:\n")
        print("   docs/PROVEEDORES_SETUP.md\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())


def test_slack():
    """Test configuración Slack Webhooks"""
    try:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        slack_channel = os.getenv("SLACK_CHANNEL")
        
        if not webhook_url:
            print("⚠️  Slack: Variables no configuradas (opcional)")
            return False
        
        # Verificar formato de webhook
        if not webhook_url.startswith("https://hooks.slack.com"):
            print("❌ Slack: Webhook URL inválida (debe empezar con 'https://hooks.slack.com')")
            return False
        
        print("✅ Slack: Configurado correctamente")
        print(f"   - Webhook: {webhook_url[:40]}...")
        if slack_channel:
            print(f"   - Channel: {slack_channel}")
        return True
        
    except Exception as e:
        print(f"❌ Slack: Error - {str(e)}")
        return False

def test_slack():
    """Verifica configuración de Slack"""
    print("\n🔔 SLACK (Notificaciones)")
    print("=" * 60)
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    canal = os.getenv("SLACK_CHANNEL", "#seguridad")
    
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL no configurado")
        print("   Instrucciones: docs/PROVEEDORES_SETUP.md sección 4")
        return False
    
    if not webhook_url.startswith("https://hooks.slack.com"):
        print("❌ SLACK_WEBHOOK_URL inválido")
        print(f"   Formato: {webhook_url}")
        return False
    
    print("✅ Webhook configurado")
    print(f"   Canal: {canal}")
    print(f"   URL: {webhook_url[:50]}...")
    return True

