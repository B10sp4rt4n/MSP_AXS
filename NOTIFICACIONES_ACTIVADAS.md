# ✅ NOTIFICACIONES SLACK ACTIVADAS

## Estado
🟢 **OPERATIVO** - Sistema de notificaciones completamente funcional

---

## Qué se implementó

### 1. Servicio de Notificaciones
- **Archivo:** [backend/services/notification_service.py](backend/services/notification_service.py)
- **Funcionalidades:**
  - Alertas de seguridad con 3 niveles de prioridad (normal, alta, crítica)
  - Notificaciones específicas para QR inválidos/expirados
  - Alertas de múltiples intentos fallidos
  - Notificaciones de eventos denegados por AUP

### 2. Integración Automática
- **QR Router:** Notificaciones automáticas cuando:
  - Se escanea un QR inválido
  - Se usa un QR expirado
  - Se intenta usar un QR ya utilizado

### 3. Configuración
- Variable `SLACK_WEBHOOK_URL` agregada al [.env](.env)
- Webhook configurado y funcional
- Sistema detecta automáticamente si está habilitado

---

## Cómo funciona

### Notificaciones Automáticas Activas

#### 1. QR Inválido
**Cuándo:** Un vigilante escanea un QR que no coincide
```
🔔 QR Inválido Escaneado
Se intentó escanear un QR inválido o expirado: abcd1234...
📍 Tenant: condo_torre_mar
```

#### 2. QR Expirado  
**Cuándo:** Se intenta usar un QR fuera de vigencia
```
🔔 QR Expirado Escaneado
Se intentó usar un QR expirado
Visita: Juan Pérez
Expiró: 2026-02-01 18:00
```

#### 3. Eventos Denegados por AUP
**Cuándo:** Una política AUP rechaza una acción
```
⚠️ Acción Denegada por AUP
Usuario intentó: generar_qr_visita
❌ Motivo: Límite de 3 QR por día excedido
```

---

## Uso Manual

### En cualquier endpoint o servicio:

```python
from backend.services.notification_service import notification_service

# Alerta simple
notification_service.enviar_alerta_seguridad(
    titulo="Acceso No Autorizado",
    descripcion="Usuario intentó acceder sin permisos",
    tenant_id="condo_a",
    prioridad="alta"
)

# QR Inválido
notification_service.enviar_qr_invalido(
    qr_code="TOKEN_QR",
    tenant_id="condo_a",
    vigilante_id="vigilante_id"
)

# Múltiples intentos fallidos
notification_service.enviar_multiples_intentos_fallidos(
    usuario_id="usuario@example.com",
    intentos=7,
    ventana_minutos=10,
    tenant_id="condo_a"
)
```

---

## Tests Disponibles

### 1. Verificación de Configuración
```bash
python test_providers.py
```

### 2. Test Rápido
```bash
python test_slack_notification.py
```

### 3. Demo Completa (5 casos de uso)
```bash
python demo_notificaciones_completo.py
```

---

## Configuración del Webhook

El webhook está configurado en [.env](.env):
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/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
```

Para obtener un nuevo webhook:
1. Ve a https://api.slack.com/messaging/webhooks
2. Crea una app o usa una existente
3. Activa "Incoming Webhooks"
4. Crea webhook para tu canal (#seguridad recomendado)
5. Copia la URL al .env

---

## Niveles de Prioridad

| Nivel | Emoji | Cuándo usar |
|-------|-------|-------------|
| `normal` | 🔔 | Eventos informativos (QR inválido, acceso denegado) |
| `alta` | ⚠️ | Eventos que requieren atención (violaciones de política) |
| `critica` | 🚨 | Seguridad crítica (posibles ataques, múltiples fallos) |

---

## Documentación Completa

Ver: [docs/NOTIFICACIONES_SLACK.md](docs/NOTIFICACIONES_SLACK.md)

---

## Próximos Pasos Sugeridos

- [ ] Agregar notificación en login fallido (múltiples intentos)
- [ ] Notificar cuando se crea/revoca una Authority
- [ ] Alertas de políticas modificadas
- [ ] Resumen diario de actividad por tenant
- [ ] Panel de administración de notificaciones en frontend

---

## Verificación

✅ Servicio creado  
✅ Integrado en QR router  
✅ Configuración en .env  
✅ Tests funcionando  
✅ Documentación completa  
✅ Demo exitosa  

**Estado:** 🟢 LISTO PARA PRODUCCIÓN
