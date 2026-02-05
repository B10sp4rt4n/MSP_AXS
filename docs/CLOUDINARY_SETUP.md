# Guía de Configuración: Cloudinary para Evidencias
## Sistema de Evidencias Fotográficas - Fase 1

### ✅ Beneficios de usar Cloudinary

#### Para el Negocio
- 💰 **Reducción de costos**: No pagas por storage en tu servidor
- 🚀 **CDN global**: Imágenes rápidas desde cualquier ubicación
- 📱 **Responsive automático**: Tamaños optimizados para móviles
- ✨ **Calidad profesional**: Compresión inteligente sin pérdida visible
- 🔒 **Backup incluido**: No pierdes evidencias si falla el servidor
- 📊 **Métricas de uso**: Tracking de visualizaciones y ancho de banda

#### Para Desarrollo
- ⚡ **Transformaciones on-the-fly**: Thumbnails, resize, crop sin código
- 🔍 **Búsqueda por metadatos**: Tags, contexto, fechas
- 🌐 **URLs públicas**: Compartir evidencias sin exponer tu servidor
- 🔧 **API completa**: Subida, eliminación, búsqueda programática
- 📦 **Sin gestión de archivos**: Cloudinary maneja todo

---

## 🛠️ Configuración Paso a Paso

### 1. Crear cuenta en Cloudinary

1. Ve a [cloudinary.com/users/register/free](https://cloudinary.com/users/register/free)
2. Crea cuenta gratuita (incluye 25 GB storage + 25 GB bandwidth/mes)
3. Confirma tu email

### 2. Obtener credenciales

Desde el dashboard de Cloudinary:

```
Cloud Name:  msp-axs-prod
API Key:     123456789012345
API Secret:  abcdefghijklmnopqrstuvwxyz1234
```

> ⚠️ **IMPORTANTE**: Nunca expongas el API Secret en el frontend o en commits de Git.

### 3. Configurar variables de entorno

#### Para desarrollo local (`.env`):

```bash
# Cloudinary Configuration
USE_CLOUDINARY=true
CLOUDINARY_CLOUD_NAME=msp-axs-prod
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz1234

# Opcional
CLOUDINARY_UPLOAD_PRESET=axs_evidencias
MAX_UPLOAD_SIZE_MB=15
```

#### Para Railway/Producción:

1. Ve a tu proyecto en Railway
2. Settings → Variables
3. Agrega las mismas variables:

```
USE_CLOUDINARY=true
CLOUDINARY_CLOUD_NAME=msp-axs-prod
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz1234
```

### 4. Instalar dependencia

```bash
pip install cloudinary
```

O si usas requirements.txt (ya incluido):

```bash
pip install -r requirements.txt
```

### 5. Verificar configuración

Ejecuta este test rápido:

```python
# test_cloudinary.py
import os
from backend.utils.cloudinary_service import CloudinaryService

# Cargar variables de entorno
os.environ["CLOUDINARY_CLOUD_NAME"] = "tu-cloud-name"
os.environ["CLOUDINARY_API_KEY"] = "tu-api-key"
os.environ["CLOUDINARY_API_SECRET"] = "tu-api-secret"

# Probar conexión
try:
    service = CloudinaryService()
    print("✅ Cloudinary configurado correctamente")
    print(f"   Cloud: {service.cloud_name}")
except Exception as e:
    print(f"❌ Error: {e}")
```

---

## 📁 Estructura de Organización en Cloudinary

Las evidencias se organizan jerárquicamente por carpetas:

```
cloudinary://msp-axs-prod/
├── evidencias/
│   ├── entrada/
│   │   ├── visitante/
│   │   │   ├── vis_abc123_foto1.jpg
│   │   │   └── vis_xyz789_foto2.jpg
│   │   ├── ine_frente/
│   │   │   └── vis_abc123_ine_f.jpg
│   │   ├── ine_reverso/
│   │   │   └── vis_abc123_ine_r.jpg
│   │   ├── placas/
│   │   │   └── vis_abc123_placa.jpg
│   │   └── vehiculo/
│   │       └── vis_abc123_auto.jpg
│   └── salida/
│       ├── visitante_salida/
│       └── vehiculo_salida/
```

### Tags automáticos para búsqueda:

- `visita:vis_abc123` → Todas las fotos de esta visita
- `guardia:usr_456` → Fotos tomadas por este guardia
- `tipo:entrada` → Fotos de entrada vs salida
- `sub_tipo:ine_frente` → Tipo específico de evidencia

---

## 🔧 Uso en el Sistema

### Backend: Subir evidencias

```python
# backend/routers/evidencias_router.py
from fastapi import UploadFile
from backend.utils.cloudinary_service import get_cloudinary_service

@router.post("/evidencias/entrada/{visita_id}")
def subir_evidencias(
    visita_id: str,
    foto_visitante: UploadFile,
    cloudinary = Depends(get_cloudinary_service)
):
    # Subir a Cloudinary
    result = cloudinary.upload_evidencia(
        file_bytes=foto_visitante.file.read(),
        filename=foto_visitante.filename,
        folder=f"evidencias/entrada/visitante",
        metadata={"visita_id": visita_id}
    )
    
    # result["secure_url"] = URL pública de la foto
    return {"url": result["secure_url"]}
```

### Frontend: Mostrar thumbnails

```javascript
// Obtener evidencias con thumbnails 200x200
const response = await fetch(`/evidencias/visita/${visitaId}/thumbnails`, {
    headers: { 'Authorization': `Bearer ${token}` }
});

const data = await response.json();

// Mostrar thumbnails
data.thumbnails.forEach(thumb => {
    const img = document.createElement('img');
    img.src = thumb.thumbnail_url;  // URL optimizada por Cloudinary
    img.alt = thumb.sub_tipo;
    container.appendChild(img);
});
```

### Transformaciones on-the-fly

Cloudinary permite transformar imágenes en la URL:

```javascript
// Original (full resolution)
https://res.cloudinary.com/msp-axs-prod/image/upload/evidencias/visitante/foto.jpg

// Thumbnail 200x200
https://res.cloudinary.com/msp-axs-prod/image/upload/w_200,h_200,c_thumb/evidencias/visitante/foto.jpg

// Preview 800px ancho, calidad 80%
https://res.cloudinary.com/msp-axs-prod/image/upload/w_800,q_80/evidencias/visitante/foto.jpg

// WebP automático (más ligero)
https://res.cloudinary.com/msp-axs-prod/image/upload/f_auto/evidencias/visitante/foto.jpg
```

---

## 🎯 Casos de Uso

### 1. Guardia toma fotos en entrada

```bash
POST /evidencias/entrada/vis_abc123
Content-Type: multipart/form-data

foto_visitante: [binary]
ine_frente: [binary]
placas: [binary]
```

**Resultado:**
- 3 archivos subidos a Cloudinary
- URLs públicas guardadas en BD
- Metadatos: visita_id, guardia_id, timestamp
- Tags automáticos para búsqueda

### 2. Admin revisa evidencias de una visita

```bash
GET /evidencias/visita/vis_abc123/thumbnails?size=300
```

**Resultado:**
- Lista de thumbnails 300x300
- Cloudinary genera imágenes optimizadas
- Sin procesamiento en el servidor

### 3. Auditoría: Buscar todas las fotos de un guardia

```python
cloudinary_service = get_cloudinary_service()
evidencias = cloudinary_service.search_evidencias(
    guardia_id="usr_456",
    tipo="entrada",
    max_results=100
)
```

---

## 📊 Límites del Plan Gratuito

| Recurso | Límite Gratuito | Costo Extra |
|---------|----------------|-------------|
| Storage | 25 GB | $0.10/GB/mes |
| Bandwidth | 25 GB/mes | $0.10/GB |
| Transformaciones | 25 créditos/mes | $0.002/crédito |
| Imágenes | Sin límite | - |

### Estimaciones para MSP_AXS:

**Año 1 (10K scans/día, 30% con foto):**
- 3K fotos/día × 30 días = 90K fotos/mes
- Tamaño promedio: 500 KB/foto
- Storage: ~45 GB/mes → **$2/mes** (sobrepasa plan gratuito)
- Bandwidth: ~50 GB/mes → **$2.50/mes**
- **Total: ~$5/mes**

**Año 2 (500K scans/día, 40% con foto):**
- 200K fotos/día × 30 días = 6M fotos/mes
- Storage: ~3 TB → **$300/mes**
- Bandwidth: ~500 GB/mes → **$50/mes**
- **Total: ~$350/mes** (justifica upgrade a plan Pro)

> 💡 **Recomendación**: Usar Cloudinary desde Fase 1 y migrar a plan pago cuando sea necesario.

---

## 🔒 Seguridad

### URLs firmadas (opcional, para fotos sensibles)

```python
# Generar URL que expira en 1 hora
from cloudinary.utils import cloudinary_url

url, options = cloudinary_url(
    "evidencias/visitante/foto_123.jpg",
    sign_url=True,
    type="authenticated",
    expires_at=int(time.time() + 3600)  # 1 hora
)
```

### Restricciones de acceso

En Cloudinary Dashboard → Security:
- ✅ Habilitar "Restrict media access"
- ✅ Validar firmas en URLs
- ✅ Configurar dominios permitidos (CORS)

---

## 🧪 Testing

### Test manual:

```bash
# Subir foto de prueba
curl -X POST http://localhost:8000/evidencias/entrada/test_123 \
  -H "Authorization: Bearer $TOKEN" \
  -F "foto_visitante=@/path/to/test.jpg"

# Respuesta esperada:
{
  "status": "ok",
  "evidencias": [{
    "evidencia_id": "ev_xyz",
    "sub_tipo": "visitante",
    "url": "https://res.cloudinary.com/msp-axs-prod/image/upload/.../test.jpg"
  }]
}
```

### Test con Python:

```python
# tests/test_cloudinary_integration.py
import requests

def test_upload_evidencia():
    url = "http://localhost:8000/evidencias/entrada/test_123"
    files = {"foto_visitante": open("test.jpg", "rb")}
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(url, files=files, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "evidencias" in data
    assert data["evidencias"][0]["url"].startswith("https://res.cloudinary.com")
```

---

## 🚨 Troubleshooting

### Error: "Cloudinary no configurado"

**Causa:** Variables de entorno no definidas.

**Solución:**
```bash
export CLOUDINARY_CLOUD_NAME=tu-cloud-name
export CLOUDINARY_API_KEY=tu-api-key
export CLOUDINARY_API_SECRET=tu-api-secret
```

### Error: "Invalid signature"

**Causa:** API Secret incorrecto.

**Solución:** Verifica credenciales en Cloudinary Dashboard.

### Error: "Quota exceeded"

**Causa:** Límite del plan gratuito excedido.

**Solución:**
1. Revisar uso en Cloudinary Dashboard
2. Considerar upgrade a plan pago
3. Implementar compresión previa

### Fallback a almacenamiento local

Si Cloudinary falla, el sistema usa almacenamiento local automáticamente:

```python
# backend/services/evidencia_service.py
# Línea 27
USE_CLOUDINARY = os.getenv("USE_CLOUDINARY", "true").lower() == "true"

# Si falla Cloudinary:
except Exception as e:
    logger.warning("⚠️ Cloudinary no disponible, usando almacenamiento local")
    archivo_url = guardar_archivo(filename, contenido)
```

---

## 📚 Referencias

- [Cloudinary Documentation](https://cloudinary.com/documentation)
- [Python SDK](https://cloudinary.com/documentation/django_integration)
- [Image Transformations](https://cloudinary.com/documentation/image_transformations)
- [Upload API](https://cloudinary.com/documentation/upload_images)

---

## ✅ Checklist de Implementación

- [x] Crear cuenta en Cloudinary
- [x] Obtener credenciales (cloud_name, api_key, api_secret)
- [x] Agregar variables de entorno
- [ ] Instalar dependencia: `pip install cloudinary`
- [ ] Probar conexión con test rápido
- [ ] Subir foto de prueba desde Postman/curl
- [ ] Verificar foto en Cloudinary Dashboard
- [ ] Integrar en frontend (formulario de evidencias)
- [ ] Configurar backup/disaster recovery
- [ ] Documentar flujo para equipo de soporte

---

## 🎉 Resultado Final

Con Cloudinary configurado, el sistema de evidencias:

✅ **Escala automáticamente** (sin límites de storage en servidor)  
✅ **URLs públicas** (compartibles, con CDN global)  
✅ **Transformaciones on-the-fly** (thumbnails, resize, calidad)  
✅ **Backup incluido** (no pierdes evidencias)  
✅ **Métricas de uso** (tracking de visualizaciones)  
✅ **Búsqueda por metadatos** (tags, contexto, fechas)  
✅ **Fallback a local** (si falla, usa almacenamiento local)  

**¡Sistema de evidencias listo para producción!** 🚀
