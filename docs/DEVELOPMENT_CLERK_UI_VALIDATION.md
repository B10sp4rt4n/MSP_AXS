# Validación UI / Clerk en development — 3 octubre 2026

Entorno: Railway AXS Development, frontend/backend fijados a 2bc5cef4e44331c82b898e36a910caaee6dad9b7. CORE/EVENT: patient-tree-68362559, rama br-blue-frog-b5o2ccsk. Horas UTC; restar seis horas para Ciudad de México. No se cambiaron producción, roles, credenciales ni scopes.

## Residente y administración

- Sesión Clerk real de RESIDENTE: preregistro UI VIS-9c7676578e (AXS UI Clerk 20261003), proveedor A/101. Propósito persistido; autorizada_por 8cc2f1dc-de70-4413-a3a0-3b70008e65af a 23:02:53.451Z. QR generado. Cancelación por UI; sin entrada ni salida.
- RESIDENTE abrió Panel Admin por ruta; guardar reglas fue rechazado: Sólo la administración configura las reglas. Relectura confirmó reglas apagadas.
- Admin A activó propósito/autorización por UI en A. Registro inmediato quedó deshabilitado. Fixture nueva axs_ui_rules_20261003 preparada por SQL sólo en development, sin QR/autorización, proveedor A/101; no se alteraron fixtures originales.
- Portal Guardia, sesión Admin A: entrada sin autorización rechazada. Admin A autorizó por UI a 23:13:12.329Z; entrada 23:13:36.162Z y salida 23:13:46.893Z. Estado final salida_registrada.
- Admin A restauró ambas reglas a false mediante UI. B conserva NULL. Nueve eventos operativos entregados, attempts=1, last_error=NULL, una copia de cada UID en EVENT.

## GUARDIA con Clerk real

Sesión user_e958ee085354, rol GUARDIA, scope existente ACTIVO exclusivo condo_949cea591f0d (Condominio Sistema Solar). Clerk completó contraseña y verificación de dispositivo por canal seguro. Sin valores de credenciales en evidencia.

- Con reglas originales NULL, GUARDIA creó por UI VIS-48cb97f61a, proveedor/Mantenimiento, propósito ficticio. Entrada inmediata 23:21:26.040Z; salida UI 23:21:36.778Z. Estado salida_registrada, autorización NULL, comportamiento permitido cuando la regla está apagada.
- SQL preparó fixture descartable axs_ui_guard_denial_20261003 copiando sólo destino/condominio de la visita anterior; vigente, pendiente, sin QR/autorización/entrada. Se activaron temporalmente ambas reglas por SQL en Sistema Solar.
- GUARDIA intentó entrada por UI: Sin autorización previa: entrada no permitida. La visita siguió sin entrada.
- En Panel Admin por ruta directa, GUARDIA intentó autorizar esta fixture: El vigilante no puede autorizar visitas.
- GUARDIA intentó guardar la misma configuración: Sólo la administración configura las reglas.
- Limpieza SQL condicionada: reglas de Sistema Solar restauradas exactamente a NULL; fixture pendiente pasó a cancelada, sin autorización/entrada. No se modificaron otras visitas ni permisos.
- Auditoría: tres eventos operativos y dos de seguridad, todos entregados en un intento sin error y exactamente una copia por UID en events_aup:
  evt_9b354db44068460c9b1b381801794673 (creación/entrada inmediata),
  evt_74afa414ca624eafafcdf22f90cd75f1 (salida),
  evt_cb677fe68dba4ce89e0a17b6eaea5e30 (entrada denegada),
  sec_2c29ed9da7804a90a0fe9a76c96d0c0c (autorización denegada),
  sec_c92140e53a4f4000b201743b74df8f12 (configuración denegada).

## Alcance y pendientes

Se acreditan autenticación Clerk real, preregistro/QR de residente, configuración/autorización de Admin A, operación GUARDIA con reglas apagadas y rechazos GUARDIA con reglas activas. La entrada positiva con reglas activas se hizo como Admin A; la equivalente con GUARDIA + Clerk aún requiere una visita autorizada por administración de Sistema Solar. El ensayo API anterior sí cubrió ese caso con JWT local y guardia sintético.

La UI permite abrir rutas administrativas y presenta botones de mutación a RESIDENTE/GUARDIA; el backend las rechaza correctamente. Conviene ocultar o deshabilitar esos controles según permisos y explicar la restricción antes del envío. No se acreditan escaneo por cámara, biometría ni hardware.

Capturas guardadas: axs-clerk-residente-20261003.jpg, axs-clerk-acceso-20261003.jpg, axs-clerk-guardia-permisos-20261003.jpg. Ninguna captura incluye contraseñas, códigos OTP ni tokens QR.
