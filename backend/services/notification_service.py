"""
Servicio de notificaciones (Slack, Email, etc.)

Permite enviar notificaciones a diferentes canales configurados por tenant.
"""

import os
import logging
from typing import Optional, Dict, Any
import requests
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio centralizado de notificaciones."""
    
    def __init__(self):
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.enabled = bool(self.slack_webhook)
    
    def enviar_alerta_seguridad(
        self,
        titulo: str,
        descripcion: str,
        tenant_id: Optional[str] = None,
        prioridad: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envía alerta de seguridad a Slack.
        
        Args:
            titulo: Título de la alerta
            descripcion: Descripción detallada
            tenant_id: ID del tenant (opcional)
            prioridad: normal | alta | critica
            metadata: Datos adicionales
        
        Returns:
            True si se envió correctamente
        """
        if not self.enabled:
            logger.warning("Notificaciones Slack deshabilitadas (SLACK_WEBHOOK_URL no configurado)")
            return False
        
        # Determinar emoji según prioridad
        emoji_map = {
            "normal": "🔔",
            "alta": "⚠️",
            "critica": "🚨"
        }
        emoji = emoji_map.get(prioridad, "🔔")
        
        # Construir mensaje
        texto = f"{emoji} *{titulo}*\n\n{descripcion}"
        
        if tenant_id:
            texto += f"\n\n📍 *Tenant:* `{tenant_id}`"
        
        if metadata:
            texto += "\n\n*Detalles:*"
            for key, value in metadata.items():
                texto += f"\n• {key}: `{value}`"
        
        texto += f"\n\n🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        
        return self._enviar_slack(texto)
    
    def enviar_evento_denegado(
        self,
        usuario_id: str,
        accion: str,
        motivo: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Notifica cuando una acción es denegada por AUP.
        
        Args:
            usuario_id: ID del usuario
            accion: Acción intentada
            motivo: Razón del rechazo
            tenant_id: Tenant afectado
        
        Returns:
            True si se envió correctamente
        """
        return self.enviar_alerta_seguridad(
            titulo="Acción Denegada por AUP",
            descripcion=f"Usuario `{usuario_id}` intentó: *{accion}*\n\n❌ *Motivo:* {motivo}",
            tenant_id=tenant_id,
            prioridad="alta",
            metadata={
                "usuario": usuario_id,
                "accion": accion
            }
        )
    
    def enviar_multiples_intentos_fallidos(
        self,
        usuario_id: str,
        intentos: int,
        ventana_minutos: int,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Alerta de múltiples intentos fallidos (posible ataque).
        
        Args:
            usuario_id: ID del usuario
            intentos: Número de intentos
            ventana_minutos: Ventana de tiempo
            tenant_id: Tenant afectado
        
        Returns:
            True si se envió correctamente
        """
        return self.enviar_alerta_seguridad(
            titulo="⚠️ POSIBLE ATAQUE DETECTADO",
            descripcion=(
                f"Usuario `{usuario_id}` realizó *{intentos} intentos fallidos* "
                f"en los últimos {ventana_minutos} minutos"
            ),
            tenant_id=tenant_id,
            prioridad="critica",
            metadata={
                "usuario": usuario_id,
                "intentos": intentos,
                "ventana": f"{ventana_minutos} min"
            }
        )
    
    def enviar_qr_invalido(
        self,
        qr_code: str,
        tenant_id: str,
        vigilante_id: Optional[str] = None
    ) -> bool:
        """
        Notifica intento de escaneo de QR inválido/expirado.
        
        Args:
            qr_code: Código QR intentado
            tenant_id: Tenant donde ocurrió
            vigilante_id: ID del vigilante que escaneó
        
        Returns:
            True si se envió correctamente
        """
        return self.enviar_alerta_seguridad(
            titulo="QR Inválido Escaneado",
            descripcion=f"Se intentó escanear un QR inválido o expirado: `{qr_code[:20]}...`",
            tenant_id=tenant_id,
            prioridad="normal",
            metadata={
                "qr_code": qr_code[:30],
                "vigilante": vigilante_id or "No identificado"
            }
        )
    
    def _enviar_slack(self, texto: str) -> bool:
        """
        Envía mensaje a Slack vía webhook.
        
        Args:
            texto: Mensaje a enviar (formato Markdown Slack)
        
        Returns:
            True si se envió correctamente
        """
        if not self.slack_webhook:
            return False
        
        try:
            payload = {
                "text": texto,
                "mrkdwn": True
            }
            
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("✅ Notificación Slack enviada correctamente")
                return True
            else:
                logger.error(f"❌ Error enviando a Slack: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Excepción enviando notificación Slack: {e}")
            return False


# Singleton global
notification_service = NotificationService()


def enviar_notificacion_seguridad(
    titulo: str,
    descripcion: str,
    tenant_id: Optional[str] = None,
    prioridad: str = "normal",
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Atajo para enviar notificaciones de seguridad.
    
    Uso:
        from backend.services.notification_service import enviar_notificacion_seguridad
        
        enviar_notificacion_seguridad(
            titulo="Acceso Denegado",
            descripcion="Usuario intentó acceder sin permisos",
            tenant_id="condo_a",
            prioridad="alta"
        )
    """
    return notification_service.enviar_alerta_seguridad(
        titulo, descripcion, tenant_id, prioridad, metadata
    )
