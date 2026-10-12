# Fotografías de identificación en AXS

Alcance: frente, reverso y nombre confirmado manualmente. No OCR ni validación
de autenticidad. El nombre se conserva en la evidencia sin sustituir al invitado.
Capturar no modifica autorizaciones ni estados de entrada/salida.

## Operación

En Portal Guardia, abrir una visita y «Identificación: fotos y nombre». También
está disponible después de validar un QR (el flujo QR existente ya registra entrada).
Tomar ambas fotos, revisar nombre y legibilidad, guardar. La cámara nativa móvil
solicita lente trasera; escritorio permite elegir archivos. Vista previa y repetición.
Las capturas pendientes solo viven en memoria; cerrar/recargar descarta lo pendiente.
Ante error, reintentar o consultar estado guardado. Una pareja por visita; no sobrescribe
evidencias. El mismo identificador y contenido se pueden reintentar sin duplicar.

## Almacenamiento y activación

Reutiliza la dependencia/configuración Cloudinary existente, con una ruta nueva
`type=authenticated` para originales y derivados. NO utiliza el antiguo servicio
de evidencias públicas ni su fallback local. No introduce Vercel Blob ni S3.
Neon conserva referencias opacas, nombre, hash, capturista y fecha en `evidencias`.
No requiere migración. No se asume que las credenciales Cloudinary estén configuradas.

Variables del backend: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`,
`CLOUDINARY_API_SECRET`, y `AXS_ID_PHOTOS_ENABLED=true` para habilitar subidas/lectura.
Por defecto está deshabilitado. Mantener deshabilitado hasta comprobar en staging
una subida/consulta con imágenes sintéticas y rechazo de la URL sin firma.
Definir la política de conservación y su proceso de eliminación antes de usar INEs
reales: esta versión no implementa purga automática.

Solo GUARDIA/ADMIN_CONDOMINIO/MSP_ADMIN con alcance autorizado pueden usar las rutas;
residentes no pueden consultar copias. Cada lectura de foto vuelve a comprobar
sesión y condominio, se audita y responde `private, no-store`. Las URLs de proveedor
no llegan al navegador. No se guardan documentos, nombres ni OCR en logs de aplicación.
El adaptador utiliza URLs firmadas internamente durante 60 segundos.

JPEG/PNG/WebP hasta 8 MB y 25 MP; mínimo 480 px en el lado menor. Normalización
de orientación, JPEG hasta 2048 px y eliminación de EXIF. No se garantiza legibilidad
automática: la confirma el operador. El nombre no acredita autenticidad.

Las dos filas y el evento se confirman en una transacción; PostgreSQL bloquea la
visita para serializar reintentos. Si falla una subida/transacción, se intenta
eliminar los objetos privados creados. Una falla de limpieza genera alerta de log
con la clave del objeto para conciliación; no hay cola automática de limpieza aún.

## Verificación previa a producción

- Pruebas backend con almacenamiento simulado: alcance, rechazo de residentes,
  archivos inválidos, tamaño, falta de reverso, reintentos y rollback.
- TypeScript y lint de los archivos nuevos/modificados.
- Pendientes reales: cámara iOS/Android en caseta, persistencia Cloudinary, acceso
  anónimo denegado y concurrencia PostgreSQL. No afirmar pruebas reales realizadas.
