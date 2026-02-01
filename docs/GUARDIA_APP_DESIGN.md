# 📱 GUARDIA APP - DISEÑO ARQUITECTÓNICO

**Fecha:** Febrero 1, 2026  
**Estado:** Especificación de Diseño  
**Versión:** 1.0

---

## 🎯 Decisión Arquitectónica

**Implementar como PWA única con detección automática de dispositivo**

### Rationale:
- ✅ Una sola base de código
- ✅ Responsive automático (PC, Tablet, Móvil)
- ✅ PWA instalable en móvil (como app nativa)
- ✅ Acceso a cámara y APIs del SO
- ✅ Funciona offline
- ✅ Menor costo de desarrollo y mantenimiento

---

## 🏗️ ARQUITECTURA

### 1. Stack Tecnológico

```
Frontend:
├─ React.js (componentes responsivos)
├─ PWA manifest + service workers
├─ getUserMedia API (cámara)
├─ IndexedDB (almacenamiento local)
└─ Responsive CSS (Tailwind/MUI)

Backend:
└─ APIs existentes (no cambios)
```

---

## 📐 DISEÑO POR DISPOSITIVO

### PC (≥ 1024px - Pantalla fija en puerta)

**Arquitectura Visual:**
```
┌────────────────────────────────────────┐
│  NAVBAR: Logo | Usuario | Cerrar Sesión│
├────────────────────────────────────────┤
│                                        │
│  [ÁREA PRINCIPAL - FIJA]               │
│  ┌──────────────────────────────────┐  │
│  │  Scanner QR                      │  │
│  │  • Input/botón "Escanear"        │  │
│  │  • Historial últimas 5 escaneos  │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  INFO VISITANTE ACTUAL           │  │
│  │  • Nombre                        │  │
│  │  • Casa destino                  │  │
│  │  • Teléfono                      │  │
│  │  • Hora entrada                  │  │
│  │  • [Botón] Capturar Fotos ↓      │  │
│  └──────────────────────────────────┘  │
│                                        │
├────────────────────────────────────────┤
│  [ÁREA EXPANDIBLE - SCROLL DOWN]       │
│  (Inicialmente oculta, anima hacia)    │
│  ┌──────────────────────────────────┐  │
│  │  CAPTURA DE FOTOS                │  │
│  │  ┌────────────────────────────┐  │  │
│  │  │  [Camera Preview]          │  │  │
│  │  │  (HTML5 Canvas + Video)    │  │  │
│  │  │  ........                  │  │  │
│  │  │                            │  │  │
│  │  │  [Foto frontal visitante]  │  │  │
│  │  └────────────────────────────┘  │  │
│  │                                  │  │
│  │  [Capturar] [Retomar] [Siguiente]│ │
│  │                                  │  │
│  │  Fotos requeridas:               │  │
│  │  ☐ Frontal visitante            │  │
│  │  ☐ ID frente                    │  │
│  │  ☐ ID reverso                   │  │
│  │  ☐ Placa vehículo (si aplica)   │  │
│  │  ☐ Vehículo general (si aplica) │  │
│  │                                  │  │
│  │  [Completar y Generar QR]        │  │
│  └──────────────────────────────────┘  │
│                                        │
└────────────────────────────────────────┘
```

**Comportamiento:**
- Área principal siempre visible
- Al hacer clic "Capturar Fotos", scroll automático hacia abajo
- Camera preview embebida (HTML5 Canvas)
- Controles accesibles (teclado/mouse)
- No interrumpe flujo principal

**Pantalla QR (Después de generar):**
```
┌────────────────────────────────────────┐
│  NAVBAR: Logo | Usuario | Cerrar Sesión│
├────────────────────────────────────────┤
│                                        │
│  ✅ QR GENERADO EXITOSAMENTE           │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │                                  │  │
│  │        [QR CODE BIG]             │  │  ← 400x400px mínimo
│  │                                  │  │     (visible desde 3m)
│  │                                  │  │
│  │        Ref: VIS-2026-0201-001    │  │
│  │        Vigencia: 8h (hasta 15:30)│  │
│  │                                  │  │
│  │  [Mostrar en pantalla] ← FIJO    │  │
│  │  [Compartir por WhatsApp]        │  │
│  │  [Enviar por Email]              │  │
│  │  [Enviar SMS]                    │  │
│  │  [Código alfanumérico]           │  │
│  │                                  │  │
│  │  [Imprimir] [Volver]             │  │
│  └──────────────────────────────────┘  │
│                                        │
└────────────────────────────────────────┘
```

---

### Tablet (600px - 1023px)

**Arquitectura Visual:**
```
┌──────────────────────────────┐
│  NAVBAR (comprimido)         │
├──────────────────────────────┤
│                              │
│  [INFO VISITANTE]            │
│  • Nombre                    │
│  • Casa                      │
│  • Hora                      │
│                              │
│  [Botón] "Capturar Foto"     │
│             ↓↓↓              │
│  (Abre cámara nativa)        │  ← INPUT TYPE=FILE + CAPTURE
│                              │
│  [Si hay foto]               │
│  ┌──────────────────────────┐│
│  │  [Preview foto]          ││
│  │  [Usar] [Rechazar]       ││
│  └──────────────────────────┘│
│                              │
│  [Ir a siguiente foto]       │
│                              │
└──────────────────────────────┘
```

**Comportamiento:**
- Cámara nativa del SO (optimizada para batería)
- `<input type="file" accept="image/*" capture="environment">`
- Modal-like (fullscreen en algunos SO)
- Después de capturar, regresa a la app
- Preview antes de confirmar

**Pantalla QR (Después de generar):**
```
┌──────────────────────────────┐
│  NAVBAR (comprimido)         │
├──────────────────────────────┤
│                              │
│  ✅ QR GENERADO               │
│                              │
│  ┌──────────────────────────┐│
│  │   [QR CODE - 250x250]    ││
│  │                          ││
│  │   VIS-2026-0201-001      ││
│  │   Vigencia: 8h           ││
│  │                          ││
│  │  [Mostrar en pantalla]   ││ ← Guardia muestra QR
│  │  [Compartir WhatsApp]    ││
│  │  [Enviar SMS]            ││ ← Visitante recibe
│  │  [Email]                 ││
│  │  [Código: V-2026-001]    ││
│  │                          ││
│  │  [Nuevo]                 ││
│  └──────────────────────────┘│
│                              │
└──────────────────────────────┘
```

---

### Móvil (< 600px)

**Arquitectura Visual:**
```
┌──────────────────┐
│  NAVBAR (icon)   │
├──────────────────┤
│                  │
│  [Datos visitante]
│  • Nombre (↓)    │
│  • Casa (↓)      │
│                  │
│  [Capturar Foto] │
│        ↓         │
│  (Cámara nativa) │
│                  │
│  [Preview +      │
│   Confirmar]     │
│                  │
│  [Siguiente]     │
│                  │
└──────────────────┘
```

**Pantalla QR (Después de generar):**
```
┌──────────────────┐
│  NAVBAR (icon)   │
├──────────────────┤
│  ✅ QR LISTO!     │
│                  │
│  ┌──────────────┐│
│  │ [QR 200x200] ││
│  │              ││
│  │ VIS-001      ││
│  │ 8h vigencia  ││
│  │              ││
│  │ [Mostrar]    ││ ← QR grande pantalla
│  │ [WhatsApp]   ││ ← Enviar al visitante
│  │ [SMS]        ││
│  │ [Email]      ││
│  │ [Código txt] ││ ← Para escribir a mano
│  │              ││
│  │ [Listo]      ││
│  └──────────────┘│
│                  │
└──────────────────┘
```


**Comportamiento:**
- Idéntico a tablet
- Cámara nativa
- Stack vertical puro (scrollable)
- Diseño mobile-first

---

## � COMPARTIR QR - OPCIONES Y FLUJOS

**Este es el paso crítico donde el visitante recibe acceso.**

### Opción 1: Mostrar en Pantalla (PC - Por defecto)

```
Guardia: Muestra QR en pantalla de 24"
Visitante: Lee QR desde pantalla con su teléfono
↓
Visitante escanea → App abre → Acceso otorgado

✅ Más rápido
✅ Sin datos contacto
✅ Privacidad
❌ Requiere QR scanner en teléfono visitante
```

### Opción 2: Compartir por WhatsApp

```
Flujo:
1. Guardia presiona [Compartir WhatsApp]
2. App abre WhatsApp pre-llenado:
   ┌──────────────────────────────────┐
   │ 📱 WhatsApp Chat                 │
   │                                  │
   │ Hola, tu QR de acceso es:        │
   │                                  │
   │ [QR CODE - IMAGE]                │
   │                                  │
   │ Ref: VIS-2026-0201-001           │
   │ Vigencia: Hasta las 15:30        │
   │ Residente: Apartamento 304       │
   │                                  │
   │ Escanea y entra. ¡Bienvenido!   │
   │ (Enviado por: AXS Seguridad)     │
   │                                  │
   └──────────────────────────────────┘
3. Guardia envía → Visitante recibe en WhatsApp
4. Visitante escanea código desde el chat

✅ Visitante documentado (WhatsApp + teléfono)
✅ Guardia no toca teléfono visitante
✅ Registro auditable (WhatsApp)
❌ Requiere teléfono + WhatsApp
```

### Opción 3: Enviar SMS

```
Flujo:
1. Guardia ingresa teléfono visitante (si no lo tiene)
2. Presiona [Enviar SMS]
3. Backend envía SMS con:
   - Código alfanumérico (V-2026-0201-001)
   - Link acortado con QR embebido
   - Instrucciones

   Ej: 
   "Acceso AXS: Código V-2026-0201-001
    Enlace: axs.app/qr/v-2026-0201-001
    Vigencia: 8h. Apto: 304"

4. Visitante recibe SMS
5. Abre link → QR directo en navegador
   O entra código manualmente

✅ Más universal (sin apps)
✅ Funciona sin smartphone moderno
❌ Menos seguro (SMS vulnerable)
❌ Requiere teléfono visitante
```

### Opción 4: Enviar Email

```
Similar a SMS, pero vía email
- QR como imagen adjunta
- Código alfanumérico en cuerpo
- Link al dashboard

✅ Formal/Auditable
✅ Guardiano legítimo (email registrado)
❌ Lento (email no instantáneo)
❌ Requiere email visitante
```

### Opción 5: Código Alfanumérico para Escribir

```
Pantalla PC muestra:
┌────────────────────────────────────────┐
│  CÓDIGO PARA ANOTAR A MANO:            │
│                                        │
│  V-2026-0201-001                       │  ← Grande, clara, monospace
│  (Vigencia: 8 horas)                   │
│                                        │
│  Visitante escribe en su papel/app     │
│  Luego entra en: axs.app/acceso       │
│  Ingresa código → Acceso otorgado     │
│                                        │
└────────────────────────────────────────┘

✅ Backup si falla QR scanner
✅ Funciona sin teléfono visitante
✅ Auditable (código en papel)
❌ Lento (escribir manual)
```

### Opción 6: NFC (Futura - No MVP)

```
Guardia presiona [Compartir NFC]
Visitante toca su teléfono a dispositivo NFC
→ Acceso otorgado

✅ Ultra rápido
❌ Requiere hardware especial
❌ No todos los teléfonos tienen NFC
```

---

### Tabla Comparativa - Métodos de Compartir QR

| Método | Rapidez | Privacidad | Datos Contacto | Universal | Auditable | Recomendado |
|--------|---------|-----------|----------------|-----------|-----------|-------------|
| **En Pantalla (PC)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | No | ⭐⭐ | ⭐⭐ | ✅ PC |
| **WhatsApp** | ⭐⭐⭐⭐ | ⭐⭐⭐ | Sí (teléfono) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Tablet/Móvil |
| **SMS** | ⭐⭐⭐ | ⭐⭐⭐ | Sí (teléfono) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ Fallback |
| **Email** | ⭐⭐ | ⭐⭐⭐⭐ | Sí (email) | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Formal |
| **Código Manual** | ⭐⭐ | ⭐⭐⭐⭐⭐ | No | ⭐⭐⭐⭐⭐ | ⭐⭐ | ✅ Backup |
| **NFC** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | No | ⭐ | ⭐⭐⭐ | 🔮 Futuro |

---

### QR Display Component (PC)

```
Mostrar QR GRANDE en pantalla:
- Tamaño: 400x400px mínimo (visible desde 3 metros)
- Código de error: Level H (30% recuperable)
- Posición: Centro pantalla
- Información debajo:
  ├─ Referencia (VIS-2026-0201-001)
  ├─ Vigencia (Hasta 15:30 - 8 horas)
  ├─ Residente/Apto destino
  └─ Visitante (Nombre)

UI Controles:
[Actualizar QR] [Mostrar en Pantalla] 
[Compartir WhatsApp] [SMS] [Email]
[Imprimir] [Copiar Código] [Volver]
```

---



### PC - Flujo Completo:

```
1. Guardia abre: app.miapp.com/guardia
2. Se detecta PC (width ≥ 1024)
3. Carga interfaz PC
4. Área principal fija visible
5. Guardia escanea QR → Busca visitante
6. Valida identidad → Muestra info
7. Guardia presiona "Capturar Fotos"
   └─ Página scroll-down (animate)
   └─ Camera preview aparece
   └─ Canvas inicializa getUserMedia
8. Captura foto 1 (Frontal) → Preview en canvas
9. Confirma → Foto sube a servidor
10. Canvas limpia → Pide foto 2
11. Repite para cada foto requerida
12. Al completar: "Generar QR"
13. Backend genera QR + token
    └─ Almacena en BD
    └─ Retorna JSON con:
       ├─ qr_data (base64 image)
       ├─ qr_url (link escaneable)
       ├─ codigo_alfanumerico (V-2026-001)
       └─ vigencia_hasta (ISO timestamp)
14. Pantalla QR aparece:
    ├─ QR grande (400x400) en pantalla
    ├─ Código + vigencia visible
    └─ Botones: [Mostrar] [WhatsApp] [SMS] [Email] [Imprimir]
15. **GUARDIA ELIGE CÓMO COMPARTIR:**
    
    ESCENARIO A: Visitante está físicamente (IN-SITU)
    ├─ Presiona [Mostrar en Pantalla]
    ├─ QR se expande a pantalla completa
    ├─ Visitante escanea con teléfono
    └─ Backend retorna: ✅ Acceso otorgado
    
    ESCENARIO B: Visitante no está pero llamó
    ├─ Guardia ingresa teléfono visitante
    ├─ Presiona [WhatsApp]
    ├─ WhatsApp Web se abre o app nativa
    ├─ Mensaje pre-llenado con QR image
    ├─ Guardia envía
    └─ Visitante recibe + escanea = ✅ Acceso
    
    ESCENARIO C: No es urgente
    ├─ Presiona [Email]
    ├─ Abre mailto: con QR adjunto
    └─ Registro formal del acceso
    
    ESCENARIO D: Visitante sin smartphone
    ├─ Presiona [Copiar Código]
    ├─ Código V-2026-0201-001 en clipboard
    ├─ Guardia anota en papel o le dicta
    ├─ Visitante ingresa código en: axs.app/acceso
    └─ Backend valida código = ✅ Acceso

16. Visitante accede al condominio
17. Guardia presiona [Volver]
    └─ Scroll-up automático
    └─ Vuelve a área principal
    └─ Estado guardado en historial
```

### Tablet - Flujo Completo:

```
1. Guardia abre: app.miapp.com/guardia
2. Se detecta Tablet (600 ≤ width < 1024)
3. Carga interfaz Tablet
4. Info visitante + botón "Capturar"
5. Presiona "Capturar Foto"
6. Se abre INPUT FILE con capture="environment"
   └─ SO abre cámara nativa
   └─ Guardia captura foto
   └─ Regresa a app
7. App muestra PREVIEW
8. Guardia confirma
   └─ Sube a servidor
   └─ INPUT FILE limpia
9. Repite para siguiente foto
10. Al completar: "Generar QR"
11. Pantalla QR aparece con opciones:
    ├─ Mostrar QR grande en tablet (si visitante está)
    ├─ [WhatsApp] → Abre app + envía
    ├─ [SMS] → Abre app nativa de SMS
    ├─ [Email] → Abre mail
    └─ [Código] → Copiar + compartir
12. Guardia elige método de entrega
13. Backend registra cuál método se usó
14. Visitante recibe acceso
```

### Móvil - Flujo Completo:

Idéntico a tablet (cámara nativa)

---

## 📁 ESTRUCTURA DE COMPONENTES

```
src/
├─ components/
│  ├─ Layout/
│  │  ├─ Navbar.jsx
│  │  └─ ResponsiveContainer.jsx
│  │
│  ├─ GuardiaApp/
│  │  ├─ GuardiaApp.jsx (router principal)
│  │  ├─ PCView.jsx (≥ 1024)
│  │  ├─ TabletView.jsx (600-1023)
│  │  └─ MobileView.jsx (< 600)
│  │
│  ├─ PC/
│  │  ├─ MainArea.jsx (fija)
│  │  ├─ CaptureArea.jsx (scroll-down)
│  │  ├─ CameraCanvas.jsx (preview canvas)
│  │  └─ QRDisplayLarge.jsx (QR 400x400)
│  │
│  ├─ Mobile/
│  │  ├─ VisitantInfo.jsx
│  │  ├─ CaptureButton.jsx
│  │  ├─ FileInput.jsx (wrapping input type=file)
│  │  └─ PhotoPreview.jsx
│  │
│  └─ Shared/
│     ├─ QRScanner.jsx
│     ├─ QRDisplay.jsx
│     ├─ QRShareModal.jsx         ← NUEVO: Modal con opciones
│     ├─ ShareWhatsApp.jsx        ← NUEVO: Integración WhatsApp
│     ├─ ShareSMS.jsx             ← NUEVO: Integración SMS
│     ├─ ShareEmail.jsx           ← NUEVO: Integración Email
│     ├─ ShareCodeManual.jsx      ← NUEVO: Código para escribir
│     ├─ PhotoCounter.jsx
│     └─ ConfirmDialog.jsx
│
├─ hooks/
│  ├─ useDeviceType.js (PC/Tablet/Mobile detection)
│  ├─ useCamera.js (getUserMedia)
│  ├─ useFileCapture.js (input type=file)
│  ├─ useQRShare.js (NUEVO: manejar compartir)
│  └─ usePWA.js (install prompt)
│
├─ services/
│  ├─ guardiaApi.js (llamadas a backend)
│  ├─ photoUpload.js (Cloudinary)
│  ├─ qrGeneration.js
│  └─ qrShare.js (NUEVO: compartir por WhatsApp/SMS/Email)
│
├─ utils/
│  ├─ deviceDetection.js
│  ├─ canvasUtils.js
│  ├─ offlineSync.js
│  └─ shareLinks.js (NUEVO: generar URLs de compartir)
│
├─ context/
│  └─ GuardiaContext.jsx (estado compartido)
│
└─ App.jsx (PWA setup + routing)
```

---

## � CÓDIGO DE EJEMPLO - COMPARTIR QR

### services/qrShare.js

```javascript
/**
 * Manejar compartir QR por múltiples canales
 */

export const shareQRByWhatsApp = (qrData, visitantName, apartamento) => {
  const message = encodeURIComponent(
    `Hola, tu QR de acceso es:\n\n` +
    `Visitante: ${visitantName}\n` +
    `Apto: ${apartamento}\n` +
    `Vigencia: 8 horas\n\n` +
    `Escanea el código QR abajo y accede a AXS:\n` +
    `[QR IMAGE]`
  );
  
  // WhatsApp Web
  const whatsappUrl = `https://wa.me/?text=${message}`;
  
  // O si ya tiene número:
  // const whatsappUrl = `https://wa.me/+34XXXXXXXXX?text=${message}`;
  
  window.open(whatsappUrl, '_blank');
};

export const shareQRBySMS = (phoneNumber, qrCode, apartamento) => {
  const message = encodeURIComponent(
    `Código de acceso AXS: ${qrCode}\n` +
    `Apto: ${apartamento}\n` +
    `Vigencia: 8h\n` +
    `Link: app.axs.com/qr/${qrCode}`
  );
  
  const smsUrl = `sms:${phoneNumber}?body=${message}`;
  window.location.href = smsUrl;
};

export const shareQRByEmail = (email, qrImage, visitantName) => {
  const mailtoUrl = 
    `mailto:${email}` +
    `?subject=Tu código de acceso AXS` +
    `&body=Hola ${visitantName},%0A%0A` +
    `Tu QR de acceso está en el adjunto.%0A` +
    `Vigencia: 8 horas.%0A%0A` +
    `Escanea y accede.`;
  
  window.location.href = mailtoUrl;
  
  // En servidor: enviar email con QR image
};

export const copyCodeToClipboard = (code) => {
  navigator.clipboard.writeText(code);
  return true;
};

export const generateShareLinks = (qrCode) => {
  return {
    // Link directo para usar código sin escanear QR
    codeLink: `${process.env.REACT_APP_BASE_URL}/acceso?code=${qrCode}`,
    
    // Link para incrustar QR en web
    qrWebLink: `${process.env.REACT_APP_BASE_URL}/qr/${qrCode}`,
    
    // Para compartir en redes
    shareURL: `${process.env.REACT_APP_BASE_URL}/share/${qrCode}`,
  };
};
```

### components/Shared/QRShareModal.jsx

```jsx
import React, { useState } from 'react';
import { shareQRByWhatsApp, shareQRBySMS, copyCodeToClipboard } from '../../services/qrShare';

export const QRShareModal = ({ qrData, visitantName, phone, email, apartamento }) => {
  const [copiedCode, setCopiedCode] = useState(false);

  const handleCopyCode = () => {
    copyCodeToClipboard(qrData.codigo);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="qr-share-modal">
      <h2>✅ QR Generado</h2>
      
      {/* QR Grande */}
      <div className="qr-display">
        <img src={qrData.qr_image} alt="QR Code" width={400} />
        <p>Ref: {qrData.codigo}</p>
        <p>Vigencia: {qrData.vigencia_hasta}</p>
      </div>

      {/* Opciones de Compartir */}
      <div className="share-options">
        
        {/* Opción 1: Mostrar en Pantalla */}
        <button 
          className="btn-share btn-display"
          onClick={() => setFullscreenQR(true)}
        >
          📺 Mostrar en Pantalla
        </button>

        {/* Opción 2: WhatsApp */}
        <button
          className="btn-share btn-whatsapp"
          onClick={() => shareQRByWhatsApp(qrData, visitantName, apartamento)}
        >
          💬 Compartir WhatsApp
        </button>

        {/* Opción 3: SMS */}
        {phone && (
          <button
            className="btn-share btn-sms"
            onClick={() => shareQRBySMS(phone, qrData.codigo, apartamento)}
          >
            📱 Enviar SMS
          </button>
        )}

        {/* Opción 4: Email */}
        {email && (
          <button
            className="btn-share btn-email"
            onClick={() => shareQRByEmail(email, qrData.qr_image, visitantName)}
          >
            ✉️ Enviar Email
          </button>
        )}

        {/* Opción 5: Código Manual */}
        <button
          className="btn-share btn-code"
          onClick={handleCopyCode}
        >
          {copiedCode ? '✅ Copiado!' : '📋 Copiar Código'}
        </button>
      </div>

      {/* Info Código Manual */}
      <div className="code-info">
        <h4>Código para escribir:</h4>
        <code>{qrData.codigo}</code>
        <p className="small">Si visitante no puede escanear QR, comparte este código</p>
      </div>

      <button className="btn-primary" onClick={onClose}>
        ✅ Listo
      </button>
    </div>
  );
};
```

### hooks/useQRShare.js

```javascript
import { useState } from 'react';
import { shareQRByWhatsApp, shareQRBySMS, copyCodeToClipboard } from '../services/qrShare';

export const useQRShare = (qrData) => {
  const [shareMethod, setShareMethod] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleWhatsApp = (visitantName, apartamento) => {
    shareQRByWhatsApp(qrData, visitantName, apartamento);
    setShareMethod('whatsapp');
  };

  const handleSMS = (phone, apartamento) => {
    shareQRBySMS(phone, qrData.codigo, apartamento);
    setShareMethod('sms');
  };

  const handleCopyCode = () => {
    copyCodeToClipboard(qrData.codigo);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShowFullscreen = () => {
    setShareMethod('fullscreen');
  };

  return {
    handleWhatsApp,
    handleSMS,
    handleCopyCode,
    handleShowFullscreen,
    shareMethod,
    copied,
  };
};
```

---

## �🔌 PWA SETUP

### manifest.json
```json
{
  "name": "AXS Guardia",
  "short_name": "Guardia",
  "description": "App de control de acceso para guardias",
  "start_url": "/guardia",
  "display": "fullscreen",
  "orientation": "portrait",
  "scope": "/guardia",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshots/mobile.png",
      "sizes": "540x720",
      "type": "image/png",
      "form_factor": "narrow"
    }
  ],
  "theme_color": "#1a1a1a",
  "background_color": "#ffffff"
}
```

### Service Worker
- Cache-first para assets estáticos
- Network-first para APIs
- Offline queue para fotos (IndexedDB)

---

## 🎬 INTERACTIVIDAD DETALLES

### PC: Scroll-down Animation

```javascript
// Cuando usuario presiona "Capturar Fotos"
const expandCapture = () => {
  const captureArea = document.getElementById('capture-area');
  captureArea.classList.add('expand'); // CSS animation
  
  // Scroll suave
  captureArea.scrollIntoView({ 
    behavior: 'smooth',
    block: 'start'
  });
  
  // Inicializar camera
  initializeCamera();
};

// CSS
#capture-area {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.5s ease-in-out;
}

#capture-area.expand {
  max-height: 800px;
}
```

### Mobile: File Input Handling

```javascript
const handleCaptureClick = () => {
  fileInputRef.current.click(); // Abre cámara nativa
};

const handlePhotoCapture = (event) => {
  const file = event.target.files[0];
  if (file) {
    // Preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);
  }
};
```

---

## 🌐 API ENDPOINTS (Sin cambios)

Usa los endpoints existentes:
- `POST /visitas/rapida` - Crear visita rápida
- `POST /evidencias/cloudinary/entrada/{id}` - Subir foto
- `POST /qr/generar/{visita_id}` - Generar QR
- `GET /qr/validar/{visita_id}/{token}` - Validar QR

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Setup PWA + Detección
- [ ] Crear manifest.json
- [ ] Configurar service worker
- [ ] Implementar useDeviceType hook
- [ ] Routing PC/Tablet/Mobile

### Fase 2: PC Interface
- [ ] MainArea component (fija)
- [ ] CaptureArea component (scroll-down)
- [ ] CameraCanvas (getUserMedia)
- [ ] Animaciones

### Fase 3: Mobile Interface
- [ ] FileInput wrapper
- [ ] PhotoPreview
- [ ] Same workflow

### Fase 4: Integración Backend + Compartir QR
- [ ] API calls para generar QR
- [ ] Upload fotos a Cloudinary
- [ ] QR generation endpoint
- [ ] Compartir por WhatsApp (webhook)
- [ ] Compartir por SMS (Twilio/similar)
- [ ] Compartir por Email
- [ ] Código alfanumérico generado
- [ ] Validar acceso por código (no solo QR)
- [ ] Offline queue (IndexedDB)

### Fase 5: Testing
- [ ] PC (24")
- [ ] Tablet (10")
- [ ] Móvil (5")
- [ ] Offline scenarios

---

## 🎨 DISEÑO VISUAL (Próximo paso)

- [ ] Figma wireframes
- [ ] Color scheme
- [ ] Typography
- [ ] Icons/Assets
- [ ] Animations (Framer Motion)

---

## ⚠️ CONSIDERACIONES TÉCNICAS

### QR Share - Requisitos Backend

```
Nuevos endpoints necesarios:
- POST /qr/generar/{visita_id}
  Response:
  {
    qr_image: "base64_png",
    qr_url: "https://...",
    codigo: "V-2026-0201-001",
    vigencia_hasta: "2026-02-01T15:30:00Z"
  }

- POST /qr/compartir/whatsapp
  Body: {
    visitant_phone: "+34...",
    qr_code: "V-2026-...",
    message_template: "default" | "custom"
  }
  → Envía SMS + QR image via WhatsApp Business API

- POST /qr/compartir/sms
  Body: {
    phone: "+34...",
    code: "V-2026-..."
  }
  → Envía SMS con código + link

- POST /qr/compartir/email
  Body: {
    email: "guest@...",
    qr_code: "V-2026-...",
    subject: "..."
  }
  → Envía email con QR adjunto

- GET /acceso?code={CODE}
  → Página pública para validar por código
  → Si válido: ✅ Acceso otorgado

- GET /qr/{CODE}
  → Página pública para ver QR grande
```

### Permisos Requeridos

```html
<!-- En manifest.json -->
"permissions": {
  "camera": {},
  "storage": {}
}
```

### Navegadores Soportados
- ✅ Chrome/Edge 90+
- ✅ Safari 14.1+ (limitado getUserMedia)
- ✅ Firefox 90+
- ✅ Samsung Internet

### Seguridad
- ✅ HTTPS obligatorio (PWA requirement)
- ✅ JWT en localStorage (con cuidado)
- ✅ Validación servidor para fotos
- ✅ Cifrado offline (IndexedDB)

---

## 📝 NOTAS

- Documento NO viene en especificación anterior
- Decisión basada en reunión de UX 2026-02-01
- Pendiente: Diseño visual en Figma
- Pendiente: Definir política offline (cómo sincronizar fotos)

