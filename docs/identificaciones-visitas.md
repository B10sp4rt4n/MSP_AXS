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

Utiliza Vercel Blob PRIVATE mediante el SDK Python `vercel==0.11.6` desde Railway.
No utiliza Cloudinary ni fallback local. Neon conserva referencias opacas, nombre,
hash, capturista y fecha en `evidencias`. No requiere migración.

Crear un Blob store privado de pruebas, por ejemplo `axs-identificaciones-test`.
En el backend de pruebas configurar `BLOB_READ_WRITE_TOKEN` con el token de ese
store (nunca en NEXT_PUBLIC_* ni en frontend) y `AXS_ID_PHOTOS_ENABLED=true`.
Un token de Vercel conectado al frontend no configura automáticamente Railway.
Mantener deshabilitado hasta comprobar una subida/consulta sintética y rechazo
al abrir la URL del objeto sin autenticación. Nunca seleccionar acceso público.
No se han migrado evidencias anteriores: el PR aún no se ha activado.
Definir la política de conservación y su proceso de eliminación antes de usar INEs
reales: esta versión no implementa purga automática.

Solo GUARDIA/ADMIN_CONDOMINIO/MSP_ADMIN con alcance autorizado pueden usar las rutas;
residentes no pueden consultar copias. Cada lectura de foto vuelve a comprobar
sesión y condominio, se audita y responde `private, no-store`. Las URLs de proveedor
no llegan al navegador. No se guardan documentos, nombres ni OCR en logs de aplicación.
El adaptador consulta el contenido privado con el token del backend y sin caché.

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
- Pendientes reales: cámara iOS/Android en caseta, persistencia Vercel Blob, acceso
  anónimo denegado y concurrencia PostgreSQL. No afirmar pruebas reales realizadas.
