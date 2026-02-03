"""
Demostración completa del sistema de notificaciones
"""

from backend.services.notification_service import notification_service
import time

print("=" * 70)
print("🔔 DEMO: Sistema de Notificaciones MSP_AXS")
print("=" * 70)
print()

# Test 1: Alerta Normal
print("📤 Test 1: Alerta de seguridad (normal)...")
notification_service.enviar_alerta_seguridad(
    titulo="Acceso Denegado - Política AUP",
    descripcion="Usuario juan.perez@example.com intentó generar un QR de visita pero excedió el límite diario (3 QR máximo)",
    tenant_id="condo_torre_mar",
    prioridad="normal",
    metadata={
        "usuario": "juan.perez@example.com",
        "accion": "generar_qr_visita",
        "limite": "3 QR/día",
        "intentos_hoy": "4"
    }
)
print("✅ Enviada\n")
time.sleep(2)

# Test 2: QR Inválido
print("📤 Test 2: QR Inválido escaneado...")
notification_service.enviar_qr_invalido(
    qr_code="abcd1234567890-TOKEN-INVALIDO",
    tenant_id="condo_torre_mar",
    vigilante_id="vigilante.garcia@example.com"
)
print("✅ Enviada\n")
time.sleep(2)

# Test 3: Evento Denegado
print("📤 Test 3: Evento denegado por AUP...")
notification_service.enviar_evento_denegado(
    usuario_id="admin@example.com",
    accion="eliminar_tenant",
    motivo="No tienes AUTHORITY de tipo GLOBAL requerida para esta operación",
    tenant_id="sistema"
)
print("✅ Enviada\n")
time.sleep(2)

# Test 4: Múltiples Intentos Fallidos (Crítico)
print("📤 Test 4: Posible ataque detectado (crítico)...")
notification_service.enviar_multiples_intentos_fallidos(
    usuario_id="hacker@suspicious.com",
    intentos=12,
    ventana_minutos=5,
    tenant_id="condo_torre_mar"
)
print("✅ Enviada\n")
time.sleep(2)

# Test 5: Alerta de Alta Prioridad
print("📤 Test 5: Alerta de alta prioridad...")
notification_service.enviar_alerta_seguridad(
    titulo="Intento de Acceso no Autorizado",
    descripcion="Se detectó un intento de acceso a evidencias de otro tenant sin scope válido",
    tenant_id="condo_torre_mar",
    prioridad="alta",
    metadata={
        "usuario": "residente@example.com",
        "recurso_solicitado": "evidencias_tenant_B",
        "scope_actual": "condo_torre_mar",
        "ip": "192.168.1.42"
    }
)
print("✅ Enviada\n")

print("=" * 70)
print("✅ Demo completada - Revisa tu canal de Slack (#seguridad)")
print("=" * 70)
