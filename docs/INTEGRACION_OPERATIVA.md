# Integración automática de PR #30 y #31

Rama de validación conjunta sobre #30, incorporando #31 sin fusionar main. No solicita pruebas visuales ni modifica datos de producción.

- Un turno une visitas, resumen, cola CORE y lectura EVENT. EVENT cae, se conserva el resumen, se recupera y los eventos de entrada/salida coinciden con las cifras. Reentrega sin duplicados.
- Matriz HTTP de dos proveedores y cuatro condominios: cada proveedor accede únicamente a sus dos condominios en visitas, bitácora y resumen (24 combinaciones).
- Revocación del scope de guardia y de membresía MSP: conservar el mismo JWT y comprobar rechazo en la siguiente petición. No exige cerrar sesión; verifica autorización contra permisos actuales. No comprueba revocación de sesión en Clerk.
- PostgreSQL: 24 visitas con ocho workers y conexiones independientes; cada una registra entrada, consulta y salida. Esperados: 24 salidas, 48 eventos únicos, cero errores inesperados. Se emiten duración total, mediana y máximo por ciclo al log de CI como AXS_LOAD.

Carga acotada de servicios y base de datos: no es benchmark de red, cámaras, Clerk, navegador ni capacidad de producción. La prueba de dos guardias usando el mismo QR sigue incluida. La verificación visual de #30 permanece pendiente.
