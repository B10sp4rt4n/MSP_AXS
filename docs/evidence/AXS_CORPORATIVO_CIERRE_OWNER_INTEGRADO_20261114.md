# Cierre del recorrido owner A — candidato integrado

Fecha: 14 de noviembre de 2026, 06:31–06:34 CDMX.
SHA publicado y ensayado: `a2b88a34f2141b36dcde8d8d5630d5ae2c254c18`, PR #110.

Este registro continúa el estado pendiente de autenticación del informe anterior. Salvador completó el acceso de la cuenta propietaria; el menú de Clerk mostró `salvador.ruiz+pruebas@synappssys.com`. No se copiaron credenciales, códigos, cookies ni tokens.

## Resultado comprobado

| Prueba sobre frontend/API reales | Resultado |
| --- | --- |
| Owner A abre consola Superadmin | Consola no disponible; GET de acceso 403 |
| Owner A abre Empresa A | GET de sedes 200; directorio vacío inicial |
| Crear Oficina Central — Integrado | POST de sede 201 |
| Crear Recepción en Oficina Central | POST de destino 201 |
| Crear un segundo destino en esa sede | POST 403 por capacidad; Recepción conservada y vista utilizable |
| Crear Sucursal Norte — Integrado | POST de sede 201 |
| Seleccionar Sucursal Norte | GET de destinos 200; sin destinos, no hereda Recepción |
| Solicitar una tercera sede | POST 403 por capacidad; permanecen las dos sedes |
| Cambiar a Empresa B con owner A | GET de sedes 403; interfaz retira sedes y formularios |
| Volver a Empresa A y Oficina Central | GET de sedes y destinos 200; dos sedes y Recepción correctas |

Empresa A: `corp_614445133fde465dbc0d14005ccde848`.
Empresa B: `corp_290409a46d4d4a47afb569ae3c1a7635`.

Consulta posterior a CORE con el conector Neon: A conserva **2 sedes / 1 destino**; B conserva **0 sedes / 0 destinos**. Recepción pertenece únicamente a Oficina Central; Sucursal Norte no tiene destinos. Los intentos excedentes no produjeron filas adicionales según esa consulta.

Las cuotas se comprobaron contra las capacidades confirmadas en el recorrido GLOBAL de este mismo SHA: A, 2 sedes y 1 destino por sede; B, 1 y 1. Los rechazos pueden generar hechos de auditoría, como está previsto.

## Evidencia

- [HTTP filtrado del candidato](AXS_CORPORATIVO_HTTP_INTEGRADO_20261114.json): sólo UTC, método, ruta y estado; sin IP, user agent ni cabeceras.
- [Resultado del propietario](images/axs-integrado-owner-a-final-20261114.jpg).
- [Cuota de sedes rechazada](images/axs-integrado-cuota-sedes-20261114.jpg).
- [Cruce a B denegado](images/axs-integrado-cruce-b-denegado-20261114.jpg).

Las capturas muestran datos sintéticos del directorio AXS; no contienen las variables de Railway ni formularios de credenciales. El navegador terminó en el directorio A con Oficina Central seleccionada y sesión del propietario. Los campos de alta quedaron vacíos.

Este cierre, junto con [la publicación y recorrido GLOBAL](AXS_CORPORATIVO_CANDIDATO_PUBLICADO_20261114.md), acredita el recorrido delimitado del candidato integrado en sandbox: alta de empresas, cuotas durables, habilitación, propietario, directorio y rechazo de cruce A→B.

## Límites

No equivale a aprobación productiva integral. No se repitieron con sesión real owner B→A, revocación de memberships, concurrencia/carga, fallos de ACK inyectados, atención ARCO, visitas corporativas ni regresión residencial de producción. La evidencia sintética/PG de CI para otros casos se conserva separada.

Backend sandbox: `37873cf3-4db4-4e47-8e14-b78482582df8`; frontend: `d8009c46-6c25-4db8-b5e8-ad1cf46d978d`, ambos publicados con el SHA indicado. Este ensayo no fusiona main ni publica frontend productivo.

Las constancias del ensayo vencen para nuevos arranques el **15 de noviembre de 2026 a las 06:06 CDMX**. No ampliar sus fechas ni recertificar bases ya pobladas. Un proceso existente no se detiene automáticamente por el vencimiento.

Siguiente etapa: revisión de la entrega y regresión residencial autenticada antes de decidir publicación productiva/fusión y activación de una empresa piloto.
