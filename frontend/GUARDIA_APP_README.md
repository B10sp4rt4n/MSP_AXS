# 📱 App de Guardia - Frontend

PWA moderna para control de acceso de guardias con generación y compartición de códigos QR.

## 🎯 Características

- ✅ **PWA Instalable** - Funciona como app nativa en móviles
- ✅ **Responsive** - Adaptado a PC (≥1024px), Tablet (600-1023px), Móvil (<600px)
- ✅ **Detección automática** de dispositivo
- ✅ **Generación QR** instantánea para visitantes
- ✅ **Múltiples canales** de compartición:
  - WhatsApp (Meta Business API)
  - SMS (Twilio)
  - Email (SendGrid)
  - Slack (Notificaciones al equipo)
  - Descarga/Impresión directa
  - Código manual alfanumérico

## 🏗️ Arquitectura

```
frontend/src/
├── components/
│   └── guardia/
│       ├── GuardiaApp.jsx       # Componente principal
│       ├── VisitaForm.jsx       # Formulario de registro
│       ├── QRDisplay.jsx        # Visualización de QR
│       └── ShareOptions.jsx     # Modal de compartición
├── hooks/
│   └── useDeviceDetection.js    # Hook para detectar dispositivo
├── services/
│   └── guardiaApi.js            # Cliente API con Axios
├── styles/
│   └── guardia.css              # Estilos específicos
└── utils/
    └── pwa.js                   # Utilidades PWA
```

## 🚀 Uso

### 1. Iniciar en modo desarrollo

```bash
npm run dev
```

La app estará disponible en `http://localhost:5173`

### 2. Acceder a la app

- Abrir el navegador
- En el menú principal, clic en **"App Guardia PRO"**
- La app detectará automáticamente el tipo de dispositivo

### 3. Flujo de registro

1. **Completar formulario**:
   - Nombre y apellido del visitante
   - Teléfono (requerido para compartir)
   - Email (opcional)
   - Apartamento destino
   - Tipo de visita (Visitante/Proveedor/Delivery/Mantenimiento)
   - ¿Tiene vehículo? → Placa

2. **Generar QR**:
   - El sistema genera automáticamente el código QR
   - Se crea código alfanumérico de respaldo (formato: V-YYMMDD-NNN)

3. **Compartir**:
   - Clic en "📤 Compartir"
   - Seleccionar método: WhatsApp, SMS, Email o Slack
   - El visitante recibe el código inmediatamente

## 📐 Diseño Responsive

### PC (≥1024px)
- Layout de 2 columnas (formulario + sidebar)
- Sidebar con instrucciones y estadísticas
- Acciones rápidas disponibles

### Tablet (600-1023px)
- Layout de 1 columna
- Grid de 2 columnas para métodos de compartición
- Formulario en filas individuales

### Móvil (<600px)
- Layout vertical completo
- Botones full-width
- Grid de 1 columna para compartición
- Header compacto

## 🔧 Configuración

### Variables de entorno

Crear archivo `.env` en `/frontend`:

```bash
VITE_API_URL=http://localhost:8000
```

En producción:

```bash
VITE_API_URL=https://tu-backend.railway.app
```

### PWA

La app se puede instalar como PWA:

1. En Chrome móvil: "Agregar a pantalla de inicio"
2. En Chrome desktop: Icono de instalación en barra de direcciones
3. La app funcionará offline con cache de Service Worker

## 📦 Dependencias

```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "axios": "^1.6.0"
}
```

## 🎨 Estilos

- CSS vanilla con variables CSS para theming
- Sin dependencias de UI libraries (Tailwind/MUI)
- Animaciones suaves y transiciones
- Dark mode ready (variables preparadas)

## 🔐 Integración con Backend

Todos los endpoints están abstraídos en `guardiaApi.js`:

```javascript
import guardiaApi from './services/guardiaApi';

// Registrar visita
const result = await guardiaApi.registrarVisita(visitaData);

// Generar QR
const qr = await guardiaApi.generarQR(visitaId);

// Compartir por WhatsApp
const compartido = await guardiaApi.compartirWhatsApp(visitaId, telefono);
```

## 🧪 Testing

Para probar localmente:

1. Backend corriendo en `http://localhost:8000`
2. Frontend corriendo en `http://localhost:5173`
3. Providers configurados (ver `/docs/PROVEEDORES_SETUP.md`)

## 📱 PWA Features

- ✅ Manifest.json configurado
- ✅ Service Worker con estrategia Network First
- ✅ Iconos en múltiples tamaños (72px - 512px)
- ✅ Funciona offline (cache de assets estáticos)
- ✅ Instalable en iOS y Android
- ✅ Splash screen automático

## 🚢 Despliegue

### Build de producción

```bash
npm run build
```

Esto genera la carpeta `/dist` lista para deployment.

### Opciones de hosting

1. **Vercel** (recomendado para frontend)
2. **Netlify**
3. **Railway** (junto con backend)
4. **GitHub Pages**

Configurar variable de entorno `VITE_API_URL` apuntando al backend en producción.

## 📚 Documentación relacionada

- [Diseño Arquitectónico](/docs/GUARDIA_APP_DESIGN.md) - Especificación completa del diseño
- [Setup de Proveedores](/docs/PROVEEDORES_SETUP.md) - Configuración de Twilio, SendGrid, WhatsApp, Slack
- [Backend API](/backend/routers/qr_router.py) - Endpoints disponibles

## 🐛 Troubleshooting

### Service Worker no se registra
- Verificar que estás en HTTPS o localhost
- Revisar consola del navegador
- Limpiar cache y recargar

### QR no se genera
- Verificar que backend está corriendo
- Revisar token JWT en localStorage
- Comprobar Network tab para errores 401/403

### Compartir no funciona
- Verificar providers configurados (test_providers.py)
- Revisar logs del backend
- Confirmar que telefono/email están bien formateados

## 📄 Licencia

Parte del proyecto MSP_AXS - Sistema de Control de Acceso
