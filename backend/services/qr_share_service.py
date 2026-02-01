"""
Servicio para compartir QR por múltiples canales
- WhatsApp
- SMS
- Email
"""

import logging
import os
import requests
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from ..core.config import settings
from ..db.core.models import QRCode

logger = logging.getLogger("axs.qr_share")


class QRShareService:
    """Manejar compartir QR por diferentes canales"""
    
    def __init__(self, db: Session):
        self.db = db
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        self.whatsapp_business_phone_id = os.getenv("WHATSAPP_BUSINESS_PHONE_ID")
        self.whatsapp_access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.email_from = os.getenv("EMAIL_FROM", "seguridad@axs.app")
    
    def compartir_por_whatsapp(
        self, 
        phone_number: str, 
        visitant_name: str, 
        qr_image_base64: str,
        codigo: str,
        apartamento: str,
        vigencia: str
    ) -> dict:
        """
        Compartir QR por WhatsApp usando Meta's WhatsApp Business API
        
        Args:
            phone_number: Número del visitante (formato: +34XXXXXXXXX)
            visitant_name: Nombre del visitante
            qr_image_base64: QR en base64
            codigo: Código alfanumérico
            apartamento: Número/letra del apartamento
            vigencia: Vigencia del QR
        
        Returns:
            {"success": bool, "message_id": str, "error": Optional[str]}
        """
        try:
            # Implementación con Meta WhatsApp Business API
            # TODO: Implementar cuando se tenga acceso a API
            logger.info(f"Compartiendo QR por WhatsApp a {phone_number}")
            
            mensaje = (
                f"Hola {visitant_name},\n\n"
                f"Tu código de acceso a AXS es:\n\n"
                f"Código: {codigo}\n"
                f"Apartamento: {apartamento}\n"
                f"Vigencia: {vigencia}\n\n"
                f"[QR Image attached]\n\n"
                f"Escanea el código o ingresa el número en app.axs.com/acceso"
            )
            
            # Aquí iría la llamada real a Twilio/Meta API
            # Por ahora retornamos simulado
            return {
                "success": True,
                "message_id": "wha_123456",
                "channel": "whatsapp",
                "phone": phone_number
            }
        
        except Exception as e:
            logger.error(f"Error compartiendo por WhatsApp: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "channel": "whatsapp"
            }
    
    def compartir_por_sms(
        self, 
        phone_number: str,
        codigo: str,
        apartamento: str,
        vigencia_horas: int = 8
    ) -> dict:
        """
        Compartir código QR por SMS usando Twilio
        
        Args:
            phone_number: Número del visitante
            codigo: Código alfanumérico
            apartamento: Número/letra del apartamento
            vigencia_horas: Horas de vigencia
        
        Returns:
            {"success": bool, "message_sid": str, "error": Optional[str]}
        """
        try:
            if not self.twilio_account_sid:
                return {
                    "success": False,
                    "error": "Twilio no configurado",
                    "channel": "sms"
                }
            
            # Construir mensaje
            mensaje = (
                f"AXS: Tu código de acceso es {codigo}\n"
                f"Apt: {apartamento}\n"
                f"Vigencia: {vigencia_horas}h\n"
                f"Link: app.axs.com/acceso"
            )
            
            # Llamada a Twilio (simulada)
            logger.info(f"Compartiendo SMS a {phone_number}: {codigo}")
            
            # En producción:
            # from twilio.rest import Client
            # client = Client(self.twilio_account_sid, self.twilio_auth_token)
            # message = client.messages.create(
            #     body=mensaje,
            #     from_=self.twilio_phone,
            #     to=phone_number
            # )
            
            return {
                "success": True,
                "message_sid": "sm_123456",
                "channel": "sms",
                "phone": phone_number
            }
        
        except Exception as e:
            logger.error(f"Error compartiendo por SMS: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "channel": "sms"
            }
    
    def compartir_por_email(
        self,
        email: str,
        visitant_name: str,
        codigo: str,
        qr_image_base64: str,
        apartamento: str,
        vigencia: str
    ) -> dict:
        """
        Compartir QR por Email usando SendGrid
        
        Args:
            email: Email del visitante
            visitant_name: Nombre del visitante
            codigo: Código alfanumérico
            qr_image_base64: QR en base64
            apartamento: Número/letra del apartamento
            vigencia: Vigencia del QR
        
        Returns:
            {"success": bool, "message_id": str, "error": Optional[str]}
        """
        try:
            if not self.sendgrid_api_key:
                return {
                    "success": False,
                    "error": "SendGrid no configurado",
                    "channel": "email"
                }
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Código de Acceso AXS</h2>
                <p>Hola {visitant_name},</p>
                <p>Tu código de acceso al condominio es:</p>
                
                <div style="background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h1 style="text-align: center; margin: 0;">{codigo}</h1>
                </div>
                
                <p><strong>Detalles:</strong></p>
                <ul>
                    <li>Apartamento: {apartamento}</li>
                    <li>Vigencia: {vigencia}</li>
                </ul>
                
                <p>Escanea el QR adjunto o ingresa el código en:</p>
                <p><a href="{settings.FRONTEND_URL}/acceso" style="color: #0066cc;">app.axs.com/acceso</a></p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    Este es un correo automático del sistema AXS. No responda este correo.
                </p>
            </body>
            </html>
            """
            
            logger.info(f"Compartiendo Email a {email}")
            
            # En producción:
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
            # ...
            
            return {
                "success": True,
                "message_id": "em_123456",
                "channel": "email",
                "email": email
            }
        
        except Exception as e:
            logger.error(f"Error compartiendo por Email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "channel": "email"
            }
    
    def registrar_comparticion(self, db_session, qr_codigo: str, canal: str, destinatario: str):
        """
        Registrar que el QR fue compartido (para auditoría)
        
        Args:
            db_session: Sesión de base de datos
            qr_codigo: Código del QR
            canal: Canal de compartición (whatsapp, sms, email, pantalla)
            destinatario: A quién se envió (teléfono, email, etc)
        """
        try:
            logger.info(f"Registrando compartición: {qr_codigo} via {canal} a {destinatario}")
            # TODO: Crear tabla QR_COMPARTICION si no existe
            # Insertar registro de compartición para auditoría
        except Exception as e:
            logger.error(f"Error registrando compartición: {str(e)}")


# No instanciar automáticamente - se instancia en el router con db


def crear_codigo_en_bd(db_session, codigo: str, visita_id: str, condominio_id: str, 
                       vigencia_hasta: datetime, compartido_via: str = None, 
                       compartido_a: str = None, compartido_por: str = None):
    """
    Crear registro de código QR en base de datos
    
    Args:
        db_session: Sesión de base de datos
        codigo: Código alfanumérico (V-260201-123)
        visita_id: ID de la visita
        condominio_id: ID del condominio
        vigencia_hasta: Fecha/hora de expiración
        compartido_via: Canal (whatsapp, sms, email, pantalla)
        compartido_a: Destinatario
        compartido_por: usuario_id que compartió
    
    Returns:
        QRCode record creado
    """
    from backend.db.core import QRCode
    from datetime import datetime
    
    qr_code = QRCode(
        codigo=codigo,
        visita_id=visita_id,
        condominio_id=condominio_id,
        vigencia_hasta=vigencia_hasta,
        compartido_via=compartido_via,
        compartido_a=compartido_a,
        compartido_por=compartido_por,
        compartido_en=datetime.utcnow() if compartido_via else None,
        usado=0
    )
    
    db_session.add(qr_code)
    db_session.commit()
    db_session.refresh(qr_code)
    
    logger.info(f"Código QR creado en BD: {codigo} para visita {visita_id}")
    return qr_code


def marcar_codigo_usado(db_session, codigo: str):
    """Marcar un código como usado"""
    from backend.db.core import QRCode
    from datetime import datetime
    
    qr_code = db_session.query(QRCode).filter(QRCode.codigo == codigo).first()
    if qr_code:
        qr_code.usado = 1
        qr_code.usado_en = datetime.utcnow()
        db_session.commit()
        logger.info(f"Código QR marcado como usado: {codigo}")
        return True
    return False

    def compartir_por_slack(
        self,
        webhook_url: str,
        visitant_name: str,
        codigo: str,
        apartamento: str,
        vigencia: str,
        channel: str = None
    ) -> dict:
        """
        Compartir código QR por Slack usando Incoming Webhooks
        
        Args:
            webhook_url: URL del webhook de Slack
            visitant_name: Nombre del visitante
            codigo: Código alfanumérico
            apartamento: Número/letra del apartamento
            vigencia: Vigencia del QR
            channel: Canal de Slack (opcional, override)
        
        Returns:
            {"success": bool, "message_id": str, "error": Optional[str]}
        """
        try:
            if not webhook_url:
                return {
                    "success": False,
                    "error": "Slack webhook no configurado",
                    "channel": "slack"
                }
            
            # Construir mensaje para Slack
            payload = {
                "text": f"🔐 Nuevo código de acceso AXS",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔐 Código de Acceso AXS",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Visitante:*\n{visitant_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Código:*\n`{codigo}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Apartamento:*\n{apartamento}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Vigencia:*\n{vigencia}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Ingresa el código en: `app.axs.com/acceso`"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"🕒 Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                            }
                        ]
                    }
                ]
            }
            
            # Agregar canal si se especifica
            if channel:
                payload["channel"] = channel
            
            # Enviar a Slack
            logger.info(f"Enviando notificación a Slack para código: {codigo}")
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code == 200 and response.text == "ok":
                return {
                    "success": True,
                    "message_id": "slack_msg",
                    "channel": "slack"
                }
            else:
                logger.error(f"Error de Slack: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Slack respondió: {response.text}",
                    "channel": "slack"
                }
        
        except Exception as e:
            logger.error(f"Error compartiendo por Slack: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "channel": "slack"
            }

    def compartir_por_slack(
        self,
        visita_id: int,
        visitante: str,
        apartamento: str,
        codigo: str,
        vigencia_hasta: datetime,
        compartido_por_usuario_id: int
    ) -> Dict:
        """
        Envía notificación a canal de Slack
        """
        try:
            webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            canal = os.getenv("SLACK_CHANNEL", "#seguridad")
            
            if not webhook_url:
                return {
                    "success": False,
                    "error": "SLACK_WEBHOOK_URL no configurado"
                }
            
            # Crear mensaje con Slack Block Kit
            fecha_vigencia = vigencia_hasta.strftime("%d/%m/%Y %H:%M")
            
            payload = {
                "text": f"🔐 Nuevo código de acceso AXS",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔐 Código de Acceso Generado"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Visitante:*\n{visitante}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Código:*\n`{codigo}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Apartamento:*\n{apartamento}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Válido hasta:*\n{fecha_vigencia}"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Generado por sistema AXS • {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code == 200 and response.text == "ok":
                # Registrar en BD
                self.crear_codigo_en_bd(
                    codigo=codigo,
                    visita_id=visita_id,
                    vigencia_hasta=vigencia_hasta,
                    compartido_via="slack",
                    compartido_a=canal,
                    compartido_por=compartido_por_usuario_id
                )
                
                return {
                    "success": True,
                    "canal": canal,
                    "codigo": codigo,
                    "message": f"Notificación enviada a {canal}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Error en Slack: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

