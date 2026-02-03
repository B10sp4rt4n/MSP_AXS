"""
Test rápido de notificaciones Slack
"""

from backend.services.notification_service import notification_service

print("🔔 Enviando notificación de prueba a Slack...")
print()

# Test 1: Alerta simple
resultado1 = notification_service.enviar_alerta_seguridad(
    titulo="🧪 TEST: Sistema de Notificaciones MSP_AXS",
    descripcion="Esta es una notificación de prueba del sistema. Si ves este mensaje, ¡todo funciona correctamente! 🎉",
    prioridad="normal"
)

if resultado1:
    print("✅ Notificación de prueba enviada correctamente")
else:
    print("❌ No se pudo enviar la notificación")
    print("   Verifica que SLACK_WEBHOOK_URL esté configurado en .env")

print()
print("📋 Revisa tu canal de Slack configurado (#seguridad por defecto)")
