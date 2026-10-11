# Invitaciones de alta por correo

En Usuarios del condominio, una cuenta pendiente muestra **Enviar invitación**.
Primero se asigna el personal o residente con los flujos existentes. Después el
administrador solicita el correo al destinatario guardado. Dar de alta por sí
solo no envía correo. No se envían contraseñas.

Configuración del backend:
- `CLERK_SECRET_KEY`: instancia Clerk del mismo ambiente que el frontend.
- `CLERK_INVITATION_REDIRECT_URL`: URL HTTPS de `/sign-up` del frontend de ese ambiente.

Clerk acepta el envío; la aplicación no afirma entrega en bandeja. La invitación
vence en siete días. El scope registra ID, correo, fecha y actor del envío; no
almacena el enlace con token. Un envío vigente se bloquea para evitar duplicados.
Si existe una invitación externa o un timeout, revisar Clerk antes de reintentar.
No se fuerza `ignore_existing`, ni se revocan invitaciones automáticamente.

El endpoint comprueba administración del condominio, asignación activa y cuenta
pendiente. Invitar administradores exige MSP administrador. No toma correo,
rol, condominio de destino ni redirect URL desde el cuerpo de la solicitud.
Los permisos siguen siendo los de AXS; el enlace sólo permite registrar la cuenta.

Aceptación pendiente en producción: configurar la URL, desplegar, usar un correo
de prueba autorizado, aceptar el enlace y comprobar el rol y aislamiento del
condominio. El webhook Clerk debe estar configurado y firmado. Esta entrega no
modifica el mecanismo existente de vinculación de identidad ni envía correos reales.
