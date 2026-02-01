# 🚪 MODO GUARDIA - FLUJO FUNCIONAL

## 📋 Resumen

El "Modo Guardia" NO es un módulo administrativo. Es el flujo operacional principal del sistema:
- **Propósito:** Permitir entrada de visitantes al condominio
- **Usuario:** Guardia (en la puerta/entrada)
- **Acciones:** Validar identidad, capturar evidencias, autorizar entrada/salida

---

## ✅ FLUJO CORRECTO (Lo que DEBERÍA hacer el Guardia)

```
┌──────────────────────────────────────────────────────────────┐
│                    MODO GUARDIA - FLUJO                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. GUARDIA INICIA SESIÓN                                    │
│     └─ Autenticación: usuario + contraseña                  │
│     └─ Token JWT generado (AUP_SESSION)                     │
│                                                              │
│  2. LEER QR (Scanner)                                        │
│     └─ ¿QR presente y válido?                               │
│        ├─ SÍ → Ir a paso 4 (VALIDAR ENTRADA REGISTRADA)    │
│        └─ NO → Ir a paso 3 (CAPTURAR INFO VISITANTE)       │
│                                                              │
│  3. CAPTURAR INFORMACIÓN VISITANTE (Sin QR)                 │
│     └─ Campos requeridos:                                   │
│        ├─ Nombre completo                                   │
│        ├─ Teléfono                                          │
│        ├─ Casa/Unidad destino                               │
│        ├─ Tipo de visitante (cliente, entrega, consulta)   │
│        ├─ Residente anfitrión                               │
│        └─ Motivo de visita                                  │
│                                                              │
│  4. CAPTURAR EVIDENCIAS (Fotos)                             │
│     └─ Fotos requeridas de ENTRADA:                         │
│        ├─ Foto frontal visitante                            │
│        ├─ Documento ID (frente)                             │
│        ├─ Documento ID (reverso)                            │
│        ├─ Placa de vehículo (si aplica)                    │
│        └─ Foto del vehículo (si aplica)                    │
│                                                              │
│  5. GENERAR QR/TOKEN (AUTORIZACIÓN)                         │
│     └─ Sistema genera:                                      │
│        ├─ QR con token de entrada                           │
│        ├─ Vigencia: 8-12 horas (configurable)              │
│        └─ Mostrar en pantalla al Guardia                    │
│                                                              │
│  6. LIBERAR AL VISITANTE                                    │
│     └─ Visitante escanea QR para SUBIR                      │
│     └─ O Guardia proporciona QR para ingreso interior       │
│                                                              │
│  7. ENTRADA REGISTRADA                                      │
│     └─ Sistema registra:                                    │
│        ├─ Hora de entrada exacta                            │
│        ├─ Guardián que autorizó                             │
│        ├─ Evidencias asociadas                              │
│        └─ AUP_EVENT con todo lo anterior                    │
│                                                              │
│  ─────────────────────────────────────────────────────      │
│  (Visitante dentro del condominio)                          │
│  ─────────────────────────────────────────────────────      │
│                                                              │
│  8. TIEMPO TRANSCURRE (Visitante dentro)                    │
│     └─ Puede acceder a áreas permitidas                     │
│     └─ QR sigue válido                                      │
│                                                              │
│  9. VISITANTE REGRESA A PUERTA/SALIDA                       │
│     └─ Guardia escanea QR nuevamente                        │
│                                                              │
│  10. CAPTURAR EVIDENCIAS DE SALIDA                          │
│      └─ Fotos requeridas de SALIDA:                         │
│         ├─ Foto frontal visitante (saliendo)                │
│         ├─ Placa vehículo (estado al salir)                 │
│         └─ Foto general de salida                           │
│                                                              │
│  11. REGISTRAR SALIDA                                       │
│      └─ Sistema registra:                                   │
│         ├─ Hora de salida exacta                            │
│         ├─ Duración total de visita                         │
│         ├─ Evidencias de salida                             │
│         └─ AUP_EVENT de salida                              │
│                                                              │
│  12. LIBERAR VISITANTE                                      │
│      └─ Visitante abandona condominio                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔴 ESTADO ACTUAL (LO QUE TENEMOS)

### Endpoints Existentes (Verificados en Servidor):

```
✅ IMPLEMENTADO (funcional):
  POST   /auth/login                                → Autenticación ✓
  GET    /qr/validar/{visita_id}/{token}          → Validar QR ✓
  POST   /qr/generar/{visita_id}                  → Generar QR ✓
  POST   /evidencias/cloudinary/entrada/{id}      → Subir fotos entrada ✓
  POST   /evidencias/cloudinary/salida/{id}       → Subir fotos salida ✓
  GET    /evidencias/cloudinary/visita/{id}       → Obtener evidencias ✓
  GET    /evidencias/cloudinary/visita/{id}/thumbnails → Thumbnails ✓
  GET    /visitas/                                 → Listar visitas ✓
  POST   /visitas/                                 → Crear visita ✓
  GET    /visitas/condominio                       → Visitas por condominio ✓
  GET    /visitas/{visita_id}                      → Obtener visita ✓

⚠️  FALTANTES (Críticos para Modo Guardia):
  POST   /visitas/rapida                     → FALTA: Crear visita sin QR previo
  POST   /visitas/{id}/registrar-entrada     → FALTA: Marcar entrada oficial
  POST   /visitas/{id}/registrar-salida      → FALTA: Marcar salida oficial
  GET    /residentes/{condominio_id}        → FALTA: Listar residentes (autocomplete)

❌ NO EXISTE (Futuros):
  GET    /guardia/visitas-activas            → Visitantes activos hoy
  GET    /guardia/historial                  → Historial del guardia
  POST   /guardia/validar-entrada-manual     → Validar sin QR
  GET    /guardia/dashboard                  → Estado actual del guardia
```

---

## 🚨 PROBLEMAS ACTUALES

### 1. **No hay flujo "sin QR" (visitante sorpresa)**
```
Realidad: Muchos visitantes NO tienen QR previo
  - Clientes llegando sin aviso
  - Entregas no programadas
  - Familiares sorpresa

Actual:
  ❌ Solo funciona si ya existe visita preregistrada con QR

Correcto:
  ✅ Guardia CREA la visita IN-SITU
  ✅ Guardia CAPTURA info visitante
  ✅ Sistema genera QR en ese momento
```

### 2. **No hay interfaz de "Modo Guardia"**
```
Actual:
  - Admin.html existe pero es para administración
  - No hay formulario para capturar visitante rápidamente
  - No hay scanner QR integrado

Correcto:
  ✅ Interfaz mobile-first para guardia
  ✅ Scanner QR nativo (cámara)
  ✅ Formulario rápido si no hay QR
  ✅ Captura de fotos automatizada
```

### 3. **La visita DEBE pre-existir**
```
Actual:
  1. Admin crea visita con POST /visitas
  2. Admin genera QR con POST /qr/generar
  3. Admin envía QR al residente
  4. Residente da QR al visitante
  5. Guardia valida QR

Correcto:
  1. Guardia en puerta escanea (sin QR)
  2. Guardia captura info visitante
  3. Guardia toma fotos
  4. Sistema genera QR al instante
  5. Guardia autoriza entrada
```

---

## 🏗️ ARQUITECTURA RECOMENDADA

### Paso 1: Crear Visita Rápida (Sin QR previo)

```
POST /visitas/rapida

Request:
{
  "condominio_id": "cond_123",
  "nombre_visitante": "Juan Pérez",
  "telefono": "5551234567",
  "casa_unidad": "4B",
  "residente_anfitrion": "Carlos López",
  "tipo_visitante": "cliente",  // cliente|entrega|consulta|familia
  "motivo": "Reunión de negocios",
  "placa_vehiculo": "ABC1234"    // opcional
}

Response:
{
  "visita_id": "vis_456",
  "nombre_visitante": "Juan Pérez",
  "estado": "creada_sin_qr",
  "qr_token": null,
  "qr_vigencia": null,
  "fechas_creacion": "2026-01-31T14:30:00Z"
}
```

### Paso 2: Capturar Evidencias (Fotos)

```
POST /evidencias/entrada/{visita_id}

Request: multipart/form-data
{
  "foto_visitante": File,
  "documento_frente": File,
  "documento_reverso": File,
  "placa_vehiculo": File (opcional),
  "foto_vehiculo": File (opcional)
}

Response:
{
  "visita_id": "vis_456",
  "evidencias_registradas": 5,
  "urls_cloudinary": [
    {
      "tipo": "foto_visitante",
      "url": "https://res.cloudinary.com/...",
      "thumbnail": "https://res.cloudinary.com/...?w=200&h=200"
    },
    ...
  ],
  "estado": "evidencias_capturadas"
}
```

### Paso 3: Generar QR y Autorizar

```
POST /qr/generar/{visita_id}

Response:
{
  "visita_id": "vis_456",
  "qr_token": "tok_789abc",
  "qr_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "qr_vigencia": "2026-02-01T02:30:00Z",  // +12 horas
  "link_qr": "https://condominios.local/validar?qr=tok_789abc"
}
```

### Paso 4: Registrar Entrada

```
POST /visitas/{visita_id}/registrar-entrada

Response:
{
  "visita_id": "vis_456",
  "estado": "entrada_registrada",
  "hora_entrada": "2026-01-31T14:35:00Z",
  "autorizado_por": "gua_001",
  "mensaje": "Visitante autorizado - Puede subir"
}

Event Registrado (AUP_EVENT):
{
  "identity": "gua_001",
  "entidad": "VISITA",
  "accion": "REGISTRAR_ENTRADA",
  "resultado": "EXITO",
  "evidencias": 5,
  "duracion_proceso": "5 minutos",
  "metadata": {
    "visitante": "Juan Pérez",
    "residente": "Carlos López",
    "fotos_capturadas": 5
  }
}
```

### Paso 5: Registrar Salida

```
POST /visitas/{visita_id}/registrar-salida

Request:
{
  "foto_salida": File,
  "foto_vehiculo_salida": File (opcional)
}

Response:
{
  "visita_id": "vis_456",
  "estado": "salida_registrada",
  "hora_entrada": "2026-01-31T14:35:00Z",
  "hora_salida": "2026-01-31T16:45:00Z",
  "duracion_visita": "2 horas 10 minutos",
  "autorizado_por": "gua_001",
  "evidencias_total": 7  // 5 entrada + 2 salida
}
```

---

## 📱 INTERFAZ RECOMENDADA (Modo Guardia)

```
┌─────────────────────────────────────────┐
│  🚪 MODO GUARDIA                       │
├─────────────────────────────────────────┤
│                                         │
│  👤 Conectado: Carlos López (GUARDIA)  │
│  📍 Condominio: Torre del Mar          │
│  🕐 Hora: 14:30                        │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  [📱 ESCANEAR QR] ← Botón grande       │
│        o                                │
│  [✍️  ENTRADA MANUAL]                  │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Últimas 5 Visitas Hoy:                │
│  ├─ ✅ 14:25 Juan Pérez (Entrada)     │
│  ├─ ⏳ 13:50 María García (Dentro)    │
│  ├─ ✅ 13:30 Paco López (Salida)      │
│  ├─ ✅ 11:00 Carlos R. (Entrada)      │
│  └─ ✅ 10:15 Ana Martínez (Entrada)   │
│                                         │
├─────────────────────────────────────────┤
│  [📊 ESTADÍSTICAS] [⚙️ CONFIGURACIÓN]  │
└─────────────────────────────────────────┘
```

---

## 🎯 PLAN DE IMPLEMENTACIÓN (Prioridad)

### Fase 1: MVP Guardia (CRÍTICA - Esta semana)
```
1. POST /visitas/rapida
   └─ Crear visita sin QR previo
   └─ Capturar info básica visitante
   
2. POST /evidencias/entrada/{visita_id}
   └─ YA EXISTE - Solo mejorar UI
   
3. POST /qr/generar/{visita_id}
   └─ YA EXISTE - Integrar en flujo
   
4. POST /visitas/{visita_id}/registrar-entrada
   └─ Crear endpoint nuevo
   
5. POST /visitas/{visita_id}/registrar-salida
   └─ Crear endpoint nuevo
```

### Fase 2: Interfaz Mobile (2 semanas)
```
1. React Native app para Guardia
2. Scanner QR integrado (cámara nativa)
3. Captura de fotos (cámara)
4. Dashboard en vivo
5. Historial de visitas
```

### Fase 3: Optimizaciones (Siguiente mes)
```
1. Reconocimiento facial (opcional)
2. Base de datos de visitantes frecuentes
3. Alertas de seguridad
4. Reportes automatizados
5. Integración con acceso físico (cerraduras)
```

---

## 📊 MÉTRICAS DEL FLUJO GUARDIA

```
Tiempo esperado por visita (Entrada):
  - Escanear QR o capturar info: 1 minuto
  - Capturar fotos (5 fotos): 2 minutos
  - Generar QR y autorizar: 1 minuto
  ─────────────────────────────
  TOTAL: 4 minutos por visitante

Capacidad del Guardia:
  - 4 min/visitante × 60 min/hora = 15 visitantes/hora
  - Jornada 8 horas = 120 visitantes/día (máximo)
  - Promedio realista: 60-80 visitantes/día

Datos Capturados:
  - 5 fotos por entrada
  - 2 fotos por salida
  - 3 metadatos (nombre, hora, residente)
  = 10 campos de datos por ciclo visita
```

---

## 🔐 SEGURIDAD EN MODO GUARDIA

```
Validaciones AUP:
  ✅ AUP_SESSION: Guardia autenticado
  ✅ AUP_SCOPE: Guardia en condominio correcto
  ✅ AUP_EVENT: Registrar TODA acción
  ✅ AUP_GOV: Políticas de límite de visitantes

Immutabilidad:
  ✅ Fotos en Cloudinary (no editable)
  ✅ Eventos en append-only log
  ✅ Hash SHA256 de cada evidencia
  ✅ Cadena de custodia completa
```

---

## ✅ CHECKLIST: Lo que FALTA Implementar

- [ ] POST /visitas/rapida - Crear visita sin QR
- [ ] GET /residentes/{condominio_id} - Listar residentes (autocompletar)
- [ ] POST /visitas/{id}/registrar-entrada - Marcar entrada
- [ ] POST /visitas/{id}/registrar-salida - Marcar salida
- [ ] GET /guardia/visitas-activas - Visitantes activos hoy
- [ ] GET /guardia/historial - Historial de visitantes
- [ ] POST /guardia/validar-entrada-manual - Validar sin QR
- [ ] UI: Formulario captura rápida visitante
- [ ] UI: Scanner QR integrado
- [ ] UI: Interfaz Guardia simplificada
- [ ] Tests: 20+ tests para modo guardia
- [ ] Docs: Manual de usuario para guardias

---

**Documento:** Especificación del Modo Guardia Funcional  
**Actualizado:** 31 Enero 2026  
**Estado:** ⚠️ CRÍTICO - Requiere implementación inmediata
