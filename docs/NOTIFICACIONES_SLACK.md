# 🔔 Guía de Notificaciones Slack

## Configuración

### 1. Crear Webhook en Slack

1. Ve a https://api.slack.com/messaging/webhooks
2. Crea un Workspace App o usa uno existente
3. Activa **Incoming Webhooks**
4. Crea un nuevo webhook para el canal donde quieras recibir notificaciones (ej: `#seguridad`)
5. Copia la URL generada (formato: `https://hooks.slack.com/services/T.../B.../xxx`)

### 2. Configurar en el Sistema

Agrega la URL del webhook en [.env](.env):

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/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
```

### 3. Verificar Configuración

Ejecuta el test de proveedores:

```bash
python test_providers.py
```

Deberías ver:

```
🔔 SLACK (Notificaciones)
✅ Webhook configurado
   URL: https://hooks.slack.com/services/T0ABBTNQL3B...
```

---

## Notificaciones Automáticas Activas

### 1. QR Inválido

**Trigger:** Cuando un vigilante escanea un QR que no coincide con la visita

**Mensaje:**
```
🔔 QR Inválido Escaneado

Se intentó escanear un QR inválido o expirado: abcd1234...

📍 Tenant: condo_torre_mar
Detalles:
• qr_code: abcd1234567890...
• vigilante: vigi-xxxx-xxxxx

🕐 2026-02-03 14:23:45 UTC
```

**Código:** [qr_router.py](backend/routers/qr_router.py#L145)

---

### 2. QR Expirado

**Trigger:** Cuando se intenta usar un QR fuera de su vigencia

**Mensaje:**
```
🔔 QR Expirado Escaneado

Se intentó usar un QR expirado
Visita: Juan Pérez
Expiró: 2026-02-01 18:00

📍 Tenant: condo_torre_mar
Detalles:
• vigilante: vigi-xxxx-xxxxx
• visita_id: visit-xxxxx

🕐 2026-02-03 14:25:12 UTC
```

**Código:** [qr_router.py](backend/routers/qr_router.py#L177)

---

### 3. Múltiples Intentos Fallidos (Próximo)

**Trigger:** Cuando un usuario hace >5 intentos de login fallidos en 10 minutos

**Mensaje:**
```
🚨 POSIBLE ATAQUE DETECTADO

Usuario admin@example.com realizó 7 intentos fallidos en los últimos 10 minutos

📍 Tenant: condo_torre_mar
Detalles:
• usuario: admin@example.com
• intentos: 7
• ventana: 10 min

🕐 2026-02-03 14:30:00 UTC
```

---

## Uso Manual en Código

### Alerta Simple

```python
from backend.services.notification_service import notification_service

notification_service.enviar_alerta_seguridad(
    titulo="Acceso Denegado",
    descripcion="Usuario intentó acceder sin permisos al módulo de configuración",
    tenant_id="condo_a",
    prioridad="alta",  # normal | alta | critica
    metadata={
        "usuario": "juan@example.com",
        "modulo": "configuracion"
    }
)
```

### Notificación de Evento Denegado

```python
notification_service.enviar_evento_denegado(
    usuario_id="user-xxxx",
    accion="generar_qr_visita",
    motivo="Límite de 3 QR por día excedido (Policy DEMO_QR_LIMIT)",
    tenant_id="condo_a"
)
```

### Alerta de Múltiples Intentos

```python
notification_service.enviar_multiples_intentos_fallidos(
    usuario_id="admin@example.com",
    intentos=7,
    ventana_minutos=10,
    tenant_id="condo_a"
)
```

---

## Niveles de Prioridad

| Prioridad | Emoji | Uso |
|-----------|-------|-----|
| `normal` | 🔔 | Eventos informativos (QR inválido, acceso denegado normal) |
| `alta` | ⚠️ | Eventos que requieren atención (múltiples fallos, políticas violadas) |
| `critica` | 🚨 | Eventos de seguridad críticos (posibles ataques, intentos de intrusión) |

---

## Deshabilitar Notificaciones

Para deshabilitar temporalmente las notificaciones:

1. Comenta la línea en [.env](.env):
   ```bash
   # SLACK_WEBHOOK_URL=https://...
   ```

2. O deja el valor vacío:
   ```bash
   SLACK_WEBHOOK_URL=
   ```

El sistema detectará automáticamente que no hay webhook configurado y no intentará enviar notificaciones (solo logueará advertencias).

---

## Logs

Todas las notificaciones se loguean automáticamente:

```
✅ Notificación Slack enviada correctamente
```

Si hay error:

```
❌ Error enviando a Slack: 400 - invalid_payload
```

---

## Testing

### Test Manual

Ejecuta desde Python:

```python
from backend.services.notification_service import notification_service

# Test básico
notification_service.enviar_alerta_seguridad(
    titulo="🧪 TEST: Sistema de Notificaciones",
    descripcion="Esta es una notificación de prueba del sistema MSP_AXS",
    prioridad="normal"
)
```

### Test Integrado

```bash
python test_providers.py
```

---

## Próximas Mejoras

- [ ] Notificaciones por email (alternativa a Slack)
- [ ] Webhooks configurables por tenant
- [ ] Panel de administración de notificaciones
- [ ] Filtros de prioridad por tenant
- [ ] Resumen diario de actividad
- [ ] Integración con Microsoft Teams
- [ ] Rate limiting para evitar spam

---

## Soporte

Si tienes problemas con las notificaciones:

1. Verifica que el webhook esté activo en Slack
2. Revisa los logs del backend: `tail -f logs/app.log`
3. Ejecuta `test_providers.py` para verificar conectividad
4. Comprueba que la URL no tiene espacios ni caracteres especiales

---

**Estado:** ✅ OPERATIVO  
**Última actualización:** 2026-02-03
