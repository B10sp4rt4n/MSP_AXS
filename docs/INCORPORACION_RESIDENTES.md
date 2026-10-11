# Incorporación de residentes

Integra los PR #45 (invitaciones individuales) y #46 (Excel) en una rama de revisión, sin modificar main.

Usuarios muestra un bloque de incorporación con búsqueda por nombre, correo o vivienda, filtros y selección explícita de hasta 20 residentes por envío. Se revisan los destinatarios antes de confirmar. Los envíos son secuenciales y se detienen ante el primer error o al salir del condominio; una petición ya enviada puede completarse. Resultado individual, sin reintentos automáticos.

Estados derivados de evidencia local:
- Precargado: pendiente de Clerk y con vivienda válida.
- Registrado: cuenta vinculada con Clerk y vivienda válida.
- Vivienda pendiente: falta un destino habitacional válido, independientemente del registro.
- Invitación solicitada: Clerk aceptó la solicitud y está dentro de siete días.
- Invitación vencida: transcurrieron siete días sin registro local.
- Revisar invitación: metadata incompleta o inválida; no se reenvía automáticamente.

Los contadores de registro y vivienda son dimensiones distintas y pueden coincidir. Solicitud no equivale a entrega, lectura o aceptación por el destinatario. AXS no consulta el estado remoto en esta versión. Los cambios de correo entre revisión y envío se rechazan usando expected_email; cada envío vuelve a autorizar el condominio y la cuenta en backend.

Pruebas: 32 casos backend aprobados sobre estados, permisos, duplicados, proveedor y Excel; Next typegen/TypeScript y ESLint del componente aprobados. Prueba Chromium añadida a CI con transporte sintético. No se enviaron correos reales.

Para producción siguen pendientes la configuración y aceptación descritas en CLERK_INVITACIONES.md, CI del candidato integrado y revisión visual. Sin migración de esquema.
