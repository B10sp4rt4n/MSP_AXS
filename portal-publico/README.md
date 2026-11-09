# Portal público AXS

Portal comercial estático para `axs-mx.com`, separado de la aplicación
`app.axs-mx.com`. Fuente preparada el 9 de noviembre de 2026.

No modifica backend, autenticación, datos, QR, permisos ni despliegue del proyecto
Vercel `frontend-next`. La contingencia offline figura como desarrollo en validación;
no se ofrecen apertura automática, biometría o modalidad corporativa activada.

## Publicación

Proyecto previsto: `axs-portal-publico`, mismo equipo Vercel que aloja la aplicación.
Directorio de fuente: `portal-publico`. HTML/CSS/JS sin build ni dependencias.
Los assets provienen de `frontend-next/public/brand` en main, sin rediseñar la marca.
Se publica una copia exacta de los archivos de entrega, con referencia al commit.
No se fusiona main para publicar ni se cambian dominios de la aplicación.

## Contacto y datos

Los selectores preparan un enlace WhatsApp; no envían mensajes automáticamente ni
guardan datos en servidor, cookies o localStorage. No se añade analítica, píxeles,
fuentes remotas ni integraciones. Los datos de la demo son explícitamente ficticios.
La privacidad del portal tiene su propia página; el enlace ARCO apunta al portal AXS.

## Verificación de esta entrega

- Sintaxis `node --check portal.js`: aprobada.
- Navegador Chrome: perspectivas por rol y recorrido revisión → entrada → salida.
- WhatsApp: selección de administradora y varias casetas refleja el mensaje preparado;
  no se envió ningún mensaje.
- Vista móvil en iframe de 390 px: menú abre, navega y se cierra; ancho de documento
  375 px y scrollWidth 375 px (scrollbar interior), sin desbordamiento horizontal.
- Inspección visual de portada de escritorio y móvil; la demo no llama APIs.
- Deben verificarse HTTPS, respuesta pública y assets en el dominio tras publicación.

No es una prueba de acceso físico, piloto productivo de caseta ni de O0/O1/O2a.
