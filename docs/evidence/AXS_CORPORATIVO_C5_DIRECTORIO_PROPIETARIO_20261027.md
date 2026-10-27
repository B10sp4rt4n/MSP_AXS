# C5 — Portal del directorio corporativo

## Problema y alcance

El ensayo del 27 de octubre confirmó por interfaz la creación, capacidades y habilitación persistente de Empresa A — Ensayo AXS (`corp_f9e6900162c24716964e5ac190d2960d`). El propietario interno es `axs_corp_sbx_owner_a`; las capacidades configuradas son 2 sedes y 10 destinos por sede. Faltaba una pantalla para usar los endpoints del directorio de C1.

Se añade `/dashboard/corporativo?empresa=<tenant_id>` sobre C3/PR #100, con selección explícita de empresa, consulta y alta de sedes, zona horaria, selección de sede y consulta/alta de destinos. El enlace aparece en Superadmin al habilitar el directorio. La cuenta propietaria debe iniciar sesión con su identidad ya vinculada.

No se cambian tablas, credenciales, permisos, membresías ni backend. La membresía corporativa vigente, modalidad habilitada, función owner/admin, asignación a sede y cuotas GOV siguen comprobándose en los endpoints existentes. Superadmin GLOBAL no implica membresía corporativa. La pantalla no deduce acceso del rol residencial ni del correo. La apertura de una URL no concede permisos. Las funciones de alta visibles son solicitudes sujetas a la autorización del servidor; un lector sin función administrativa recibirá rechazo.

## Recuperación y aislamiento de interfaz

- Cada sesión/empresa monta un estado independiente. Las consultas previas se cancelan al cambiar de empresa o desmontar la sesión.
- El cambio de sede limpia los destinos previos; la respuesta de una consulta cancelada no repuebla la pantalla.
- No se reintentan POST automáticamente. Un error de transporte o servidor bloquea nuevas altas hasta consultar el directorio y revisar el resultado. Los endpoints existentes no tienen clave de idempotencia: la recuperación requiere revisión de la lista, también tras recargar la página.
- Los rechazos 401/403 retiran el directorio visible. El servidor sigue siendo la frontera de autorización, incluyendo cuotas y concurrencia.
- Sin sesión se redirige al acceso conservando la empresa en una ruta interna.

## Verificación

- `npm run build`: aprobado con Next.js 16.3.6.
- `next typegen` y `tsc --noEmit`: aprobados.
- ESLint del portal: aprobado.
- 34 pruebas existentes de roles: aprobadas.
- 4 pruebas existentes de la barrera Superadmin y 3 nuevas de sesión/ruta del propietario: aprobadas.
- Ensayo Chromium sintético nuevo: aprobado localmente con Chromium 133 (binario de prueba alternativo); incluido en CI con Playwright 1.58.2 y su navegador correspondiente. Comprueba membresía denegada, sedes, aislamiento de destinos, respuesta incierta sin reenvío, cuota rechazada, remontaje, cambio de empresa con respuesta retrasada, cierre de sesión y anchos 320/360/1280.

Las capturas de 320/360/1280 fueron inspeccionadas. El ensayo Superadmin ahora carga Tailwind también tras recargar para que su comprobación de ancho mida el diseño real.

La prueba autenticada contra la empresa de ensayo sigue pendiente del recorrido del propietario; las pruebas sintéticas no la sustituyen. Producción, main, San Luis y las bases legadas quedan fuera de este cambio. No se habilitan visitas, QR, hardware, invitaciones ni correo. No se afirma cumplimiento general ARCO ni se sustituye el aviso de prueba por uno real.
