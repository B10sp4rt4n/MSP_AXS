# Turno y bitácora administrativa

Se simula un turno con cinco visitas y reloj controlado: tres ingresos (personal, entrega, proveedor), dos salidas, una cancelación y un permiso vencido. Se verifica reutilización del QR, publicación CORE → EVENT, lectura administrativa, entrega repetida sin duplicados y separación de datos entre condominios.

La API nueva GET /bitacora/{condominio_id} exige acceso ADMIN_CONDOMINIO antes de consultar EVENT. Filtra explícitamente tenant y entidades visita/qr, usa paginación por ID de recepción y devuelve únicamente campos permitidos, sin token QR ni hash de sesión. Puede filtrarse por visita_id. El contador de pendientes comprende toda la cola del condominio.

El panel Admin incorpora Bitácora con actor, autorización, motivo, estado, fecha con zona de Ciudad de México y aviso de entrega pendiente. El guardia ve el total dentro/salida pendiente. Se corrige el título «Visitas de hoy»: la consulta existente devuelve visitas del condominio sin filtro diario. Un fallo de carga del guardia ya no aparece como cero visitas; se descartan respuestas de selecciones anteriores.

Validación local: 37 pruebas backend aprobadas (turno, rechazos, outbox, reloj), 17 pruebas de roles/renderizado aprobadas y TypeScript correcto. Pruebas de renderizado con límites de autenticación simulados; no equivalen a navegación real con Clerk ni a una validación visual móvil. No se aplicaron migraciones ni datos de prueba a producción.

La visita vencida conserva su estado persistido pendiente: el vencimiento de su permiso está demostrado por el rechazo y el evento correspondiente. Este cambio no incorpora un proceso para renombrar automáticamente ese estado.
