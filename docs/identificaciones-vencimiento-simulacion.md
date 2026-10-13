# Simulación de vencimiento de identificaciones

Panel Admin → Reportes → Vencimiento de identificaciones. Seleccionar fecha de corte y «Simular vencimiento».

La simulación aplica un plazo propuesto de 30 días a los datos actuales. Con salida registrada y consistente, usa la fecha de salida. Sin salida, usa la última fecha de captura del par. El corte incluye la fecha seleccionada hasta el inicio del día siguiente en America/Mexico_City; una expiración exactamente en ese inicio pertenece al siguiente día.

Clasifica: vencería, vigente, posterior al corte o revisión manual. Los pares incompletos, orígenes de almacenamiento distintos, capturas no coincidentes, tenants inconsistentes, ausencia de fecha de salida y capturas posteriores a la salida requieren revisión. No infiere retenciones por incidentes ni reconstruye estados históricos.

Acceso: alcance administrativo del condominio. Residentes, guardias sin alcance administrativo y cuentas de otro tenant reciben rechazo. Respuesta private, no-store. No devuelve nombres transcritos, identificadores de evidencia ni rutas de objetos.

Ruta: GET /reportes/{condominio_id}/identificaciones-vencimiento?fecha_corte=YYYY-MM-DD. La fecha por defecto es hoy en Ciudad de México. Hasta 10,000 filas de fotos; si se supera el límite rechaza la consulta sin emitir un resumen parcial.

No descarga imágenes, no llama al proveedor, no elimina archivos, no cambia metadatos/estados y no activa un trabajo de purga. La interfaz pagina los resultados en grupos de 25. Cambiar la fecha exige volver a simular; el corte del resultado anterior permanece visible.

Validación local: 19 pruebas del simulador, 18 de fotografías y 5 del reporte operativo existente; TypeScript y lint de ambos componentes aprobados. La validación en Development se registra aparte después del despliegue.
