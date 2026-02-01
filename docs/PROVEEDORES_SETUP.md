# 🔌 CONFIGURACIÓN DE PROVEEDORES EXTERNOS

Guía para configurar los proveedores de terceros necesarios para compartir códigos QR.

---

## 📋 Resumen

| Proveedor | Propósito | Requerido | Costo |
|-----------|-----------|-----------|-------|
| **Twilio** | Enviar SMS | Opcional | Pay-per-use (~$0.01/SMS) |
| **SendGrid** | Enviar Email | Opcional | Free tier 100 emails/día |
| **WhatsApp Business** | Enviar WhatsApp | Opcional | Free (requiere aprobación) |
| **Cloudinary** | Almacenar evidencias | ✅ Sí | Free tier 25GB |

---

## 1️⃣ TWILIO (SMS)

### Paso 1: Crear cuenta
1. Ir a https://www.twilio.com/try-twilio
2. Registrarse (requiere verificación de teléfono)
3. Verificar email

### Paso 2: Obtener credenciales
1. En el Dashboard: https://console.twilio.com
2. Copiar:
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: (clic en "Show" para ver)
3. En "Phone Numbers" → "Buy a number"
   - Seleccionar país (ej: México)
   - Buscar número con SMS capability
   - Comprar (cuesta ~$1.15/mes)
4. Copiar el número comprado: `+52XXXXXXXXXX`

### Paso 3: Configurar en .env
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token-here
TWILIO_PHONE_NUMBER=+52XXXXXXXXXX
```

### Paso 4: Instalar SDK
```bash
pip install twilio
```

### Costo estimado
- **Setup**: $1.15/mes (número de teléfono)
- **Uso**: $0.01 - $0.02 por SMS enviado
- **Free tier**: $15 crédito inicial

### Código de prueba
```python
from twilio.rest import Client

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
message = client.messages.create(
    body="Prueba AXS: Código V-260201-123",
    from_=TWILIO_PHONE_NUMBER,
    to="+52XXXXXXXXXX"  # Tu teléfono de prueba
)
print(f"Mensaje enviado: {message.sid}")
```

---

## 2️⃣ SENDGRID (Email)

### Paso 1: Crear cuenta
1. Ir a https://signup.sendgrid.com
2. Registrarse con email corporativo (mejor aprobación)
3. Verificar email

### Paso 2: Obtener API Key
1. Ir a Settings → API Keys
2. Clic en "Create API Key"
3. Nombre: `AXS-QR-Sharing`
4. Permisos: **Full Access** (o solo Mail Send)
5. Clic en "Create & View"
6. **COPIAR API KEY** (solo se muestra una vez)
   - Formato: `SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Paso 3: Configurar sender
1. Ir a Settings → Sender Authentication
2. Verificar dominio o email individual
3. Para pruebas: Single Sender Verification
   - Email: `seguridad@tudominio.com`
   - Verificar desde tu email

### Paso 4: Configurar en .env
```bash
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=seguridad@tudominio.com
EMAIL_FROM_NAME=AXS Seguridad
```

### Paso 5: Instalar SDK
```bash
pip install sendgrid
```

### Costo estimado
- **Setup**: Gratis
- **Free tier**: 100 emails/día permanentemente
- **Upgrade**: $19.95/mes para 50,000 emails

### Código de prueba
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email=EMAIL_FROM,
    to_emails='tu-email@test.com',
    subject='Prueba AXS',
    html_content='<strong>Código: V-260201-123</strong>'
)

sg = SendGridAPIClient(SENDGRID_API_KEY)
response = sg.send(message)
print(f"Email enviado: {response.status_code}")
```

---

## 3️⃣ WHATSAPP BUSINESS API (Meta)

### ⚠️ Advertencia
- Proceso de aprobación **puede tomar días/semanas**
- Requiere cuenta Meta Business
- Más complejo que Twilio/SendGrid

### Paso 1: Crear Meta Business Account
1. Ir a https://business.facebook.com
2. Crear cuenta de negocio
3. Verificar negocio (documentos oficiales requeridos)

### Paso 2: Crear app en Meta for Developers
1. Ir a https://developers.facebook.com/apps
2. "Create App" → Tipo: **Business**
3. Agregar producto: **WhatsApp**
4. Completar configuración de negocio

### Paso 3: Obtener credenciales
1. En Dashboard de WhatsApp:
   - **Phone Number ID**: `123456789012345`
   - **WhatsApp Business Account ID**
2. En Settings → Basic:
   - **Access Token** (temporal, necesitas permanente)
3. Generar Access Token permanente:
   - Settings → Advanced → System User
   - Crear System User con permisos de WhatsApp
   - Generar token

### Paso 4: Configurar webhook (para recibir respuestas)
1. En WhatsApp → Configuration
2. Callback URL: `https://tudominio.com/webhooks/whatsapp`
3. Verify Token: genera uno aleatorio
4. Suscribirse a eventos: `messages`

### Paso 5: Configurar en .env
```bash
WHATSAPP_BUSINESS_PHONE_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=your-permanent-access-token
WHATSAPP_VERIFY_TOKEN=your-webhook-verify-token
```

### Paso 6: Instalar SDK (requests es suficiente)
```bash
# No hay SDK oficial, usar requests
pip install requests
```

### Costo estimado
- **Setup**: Gratis
- **Uso**: Gratis para conversaciones iniciadas por usuario
- **Tarifas**: Conversaciones iniciadas por negocio ~$0.01-0.05 según país

### Código de prueba
```python
import requests

url = f"https://graph.facebook.com/v18.0/{WHATSAPP_BUSINESS_PHONE_ID}/messages"
headers = {
    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "messaging_product": "whatsapp",
    "to": "+52XXXXXXXXXX",
    "type": "text",
    "text": {"body": "Prueba AXS: Código V-260201-123"}
}
response = requests.post(url, headers=headers, json=data)
print(response.json())
```

---

## 4️⃣ CLOUDINARY (Evidencias Fotográficas)

### Paso 1: Crear cuenta
1. Ir a https://cloudinary.com/users/register_free
2. Registrarse (gratis)
3. Verificar email

### Paso 2: Obtener credenciales
1. En Dashboard:
   - **Cloud Name**: `your-cloud-name`
   - **API Key**: números
   - **API Secret**: (clic en "Reveal" para ver)

### Paso 3: Configurar en .env
```bash
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=your-api-secret-here
CLOUDINARY_FOLDER=axs-evidencias
```

### Paso 4: Ya está instalado
```bash
# Ya instalado en requirements.txt
# pip install cloudinary
```

### Costo estimado
- **Free tier**: 25 GB storage + 25 GB bandwidth/mes
- **Upgrade**: $99/mes para 100 GB

---

## 🔐 CONFIGURACIÓN DE .ENV

### Archivo .env completo (ejemplo)

```bash
# ═══════════════════════════════════════════════════════════════
# TWILIO
# ═══════════════════════════════════════════════════════════════
TWILIO_ACCOUNT_SID=AC1234567890abcdef1234567890abcdef
TWILIO_AUTH_TOKEN=1234567890abcdef1234567890abcdef
TWILIO_PHONE_NUMBER=+521234567890

# ═══════════════════════════════════════════════════════════════
# SENDGRID
# ═══════════════════════════════════════════════════════════════
SENDGRID_API_KEY=SG.1234567890abcdefghijklmnopqrstuvwxyz
EMAIL_FROM=seguridad@axs.app
EMAIL_FROM_NAME=AXS Seguridad

# ═══════════════════════════════════════════════════════════════
# WHATSAPP BUSINESS
# ═══════════════════════════════════════════════════════════════
WHATSAPP_BUSINESS_PHONE_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_VERIFY_TOKEN=mi-token-secreto-webhook-123

# ═══════════════════════════════════════════════════════════════
# CLOUDINARY
# ═══════════════════════════════════════════════════════════════
CLOUDINARY_CLOUD_NAME=axs-prod
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz
CLOUDINARY_FOLDER=axs-evidencias

# ═══════════════════════════════════════════════════════════════
# FRONTEND
# ═══════════════════════════════════════════════════════════════
FRONTEND_URL=https://app.axs.com
```

---

## 📦 INSTALAR DEPENDENCIAS

Agregar a `requirements.txt`:

```txt
# Proveedores externos
twilio==8.11.0
sendgrid==6.11.0
cloudinary==1.37.0
requests==2.31.0  # Para WhatsApp Business API
```

Instalar:
```bash
pip install -r requirements.txt
```

---

## ✅ TESTING

### Script de prueba completo

```python
# test_providers.py
import os
from dotenv import load_dotenv

load_dotenv()

# Test Twilio SMS
def test_twilio():
    try:
        from twilio.rest import Client
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        print("✅ Twilio: Configurado correctamente")
        return True
    except Exception as e:
        print(f"❌ Twilio: {e}")
        return False

# Test SendGrid Email
def test_sendgrid():
    try:
        from sendgrid import SendGridAPIClient
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        print("✅ SendGrid: Configurado correctamente")
        return True
    except Exception as e:
        print(f"❌ SendGrid: {e}")
        return False

# Test WhatsApp Business
def test_whatsapp():
    try:
        import requests
        phone_id = os.getenv("WHATSAPP_BUSINESS_PHONE_ID")
        token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        if phone_id and token:
            print("✅ WhatsApp: Configurado correctamente")
            return True
        print("⚠️  WhatsApp: Variables no configuradas")
        return False
    except Exception as e:
        print(f"❌ WhatsApp: {e}")
        return False

# Test Cloudinary
def test_cloudinary():
    try:
        import cloudinary
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET")
        )
        print("✅ Cloudinary: Configurado correctamente")
        return True
    except Exception as e:
        print(f"❌ Cloudinary: {e}")
        return False

if __name__ == "__main__":
    print("\n🔍 Verificando configuración de proveedores...\n")
    test_twilio()
    test_sendgrid()
    test_whatsapp()
    test_cloudinary()
    print("\n✅ Verificación completada\n")
```

Ejecutar:
```bash
python test_providers.py
```

---

## 🚀 MODO DE OPERACIÓN

El sistema funciona **de forma degradada** si no están configurados:

- ✅ **Sin Twilio**: No envía SMS, pero WhatsApp/Email funcionan
- ✅ **Sin SendGrid**: No envía Email, pero SMS/WhatsApp funcionan
- ✅ **Sin WhatsApp**: No envía WhatsApp, pero SMS/Email funcionan
- ❌ **Sin Cloudinary**: NO pueden subirse evidencias (crítico)

**Recomendación MVP:**
1. ✅ Configurar **Cloudinary** (obligatorio)
2. ✅ Configurar **Twilio** (SMS es más universal)
3. ⚠️  Configurar **SendGrid** (opcional)
4. ⏳ Configurar **WhatsApp** (cuando se apruebe cuenta)

---

## 📊 COSTOS MENSUALES ESTIMADOS

Para **1000 visitas/mes**:

| Proveedor | Uso estimado | Costo/mes |
|-----------|--------------|-----------|
| Twilio SMS | 500 SMS | ~$10 |
| SendGrid | 500 emails | Gratis |
| WhatsApp | 500 mensajes | Gratis |
| Cloudinary | 10 GB | Gratis |
| **TOTAL** | | **~$10/mes** |

---

## ❓ FAQ

**Q: ¿Puedo usar alternativas?**  
A: Sí. Puedes usar:
- Amazon SNS en lugar de Twilio
- Mailgun en lugar de SendGrid
- AWS S3 en lugar de Cloudinary

**Q: ¿Qué pasa si no configuro nada?**  
A: El sistema generará códigos QR pero solo se podrán mostrar en pantalla (no enviar por canal digital).

**Q: ¿Cómo pruebo sin gastar dinero?**  
A: Twilio y SendGrid tienen free tiers generosos. Para WhatsApp, usa el modo sandbox de Meta.

**Q: ¿Es seguro poner credenciales en .env?**  
A: Sí, si:
1. `.env` está en `.gitignore`
2. No lo commits a git
3. En producción usas secrets manager (AWS Secrets, Railway vars, etc.)

---

## 📝 CHECKLIST DE CONFIGURACIÓN

- [ ] Cuenta Twilio creada
- [ ] Número de teléfono Twilio comprado
- [ ] API Key SendGrid generada
- [ ] Sender Email verificado en SendGrid
- [ ] Meta Business Account creada (WhatsApp)
- [ ] WhatsApp Business API configurada
- [ ] Cuenta Cloudinary creada
- [ ] Todas las variables en `.env`
- [ ] `pip install -r requirements.txt` ejecutado
- [ ] `python test_providers.py` ejecutado con éxito

---

## 4️⃣ SLACK (Notificaciones al equipo)

### Paso 1: Crear Slack Workspace (si no tienes)
1. Ir a https://slack.com/create
2. Crear workspace para tu empresa/condominio
3. Crear canal `#seguridad` o similar

### Paso 2: Crear Incoming Webhook
1. Ir a https://api.slack.com/apps
2. Clic en "Create New App" → "From scratch"
3. Nombre: `AXS Notificaciones`
4. Seleccionar workspace
5. En "Incoming Webhooks":
   - Activar "Activate Incoming Webhooks"
   - Clic en "Add New Webhook to Workspace"
   - Seleccionar canal (ej: #seguridad)
   - Autorizar
6. **COPIAR WEBHOOK URL**
   - Formato: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`

### Paso 3: Configurar en .env
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
SLACK_CHANNEL=#seguridad
```

### Paso 4: No requiere SDK adicional
```bash
# Solo requiere requests (ya instalado)
```

### Costo estimado
- **Setup**: Gratis
- **Uso**: Gratis (ilimitado)
- **Plan Pro**: $8/usuario/mes (opcional, más funciones)

### Código de prueba
```python
import requests

webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"

payload = {
    "text": "🔐 Nuevo código de acceso AXS",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Visitante:* Juan Pérez\n*Código:* `V-260201-123`\n*Apt:* 304"
            }
        }
    ]
}

response = requests.post(webhook_url, json=payload)
print(f"Mensaje enviado: {response.text}")  # Debe retornar 'ok'
```

### Características
- ✅ **Notificaciones en tiempo real** al equipo de seguridad
- ✅ **Formato rico** con bloques y markdown
- ✅ **Canal dedicado** para mantener organizado
- ✅ **Ilimitado** sin costos por mensaje
- ✅ **Auditoría** mensajes quedan registrados en Slack

### Uso recomendado
Slack es ideal para:
- Notificar al **equipo de seguridad** cuando se genera un código
- Alertas de **incidentes críticos**
- **Reportes automáticos** de visitas del día
- **Backup** de notificaciones (si SMS/WhatsApp fallan)

---

