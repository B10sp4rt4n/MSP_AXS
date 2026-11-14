# AXS Corporativo — validación autenticada del sandbox

Fecha: 14 de noviembre de 2026, 05:35–05:44 CDMX (11:35–11:44 UTC).

## Resultado

Se usó el frontend real publicado, autenticación Clerk Development con verificación de dispositivo y el backend del sandbox. No se sustituyeron respuestas ni dependencias. El operador introdujo sus credenciales mediante la captura segura; no forman parte de este expediente.

| Cuenta / operación | Evidencia de interfaz | HTTP observado en Railway |
| --- | --- | --- |
| GLOBAL: entrada a Superadmin | Formulario de consola disponible | GET /plataforma/corporativo/acceso 200 |
| GLOBAL: consultar Empresa A y B | Directorios habilitados y owners A/B correspondientes | GET de cada empresa 200 |
| GLOBAL: abrir directorios A y B sin membresía | Mensaje de permiso denegado, sin sedes | GET /corporativo/{A,B}/sedes 403 |
| Owner A: intentar Superadmin | Consola no disponible; exige GLOBAL | GET /plataforma/corporativo/acceso 403 |
| Owner A: abrir Empresa A | Oficina Central — Ensayo y Sucursal Norte — Ensayo | GET /corporativo/{A}/sedes 200 |
| Owner A: Oficina Central | Destino Recepción | GET de destinos 200 |
| Owner A: Sucursal Norte | Esta sede todavía no tiene destinos | GET de destinos 200 |
| Owner A: cambiar a Empresa B | Sin sedes y mensaje de permiso denegado | GET /corporativo/{B}/sedes 403 |
| Owner A: solicitar tercera sede sintética | Rechazo específico por capacidad; permanecen las dos sedes | POST /corporativo/{A}/sedes 403 |
| Owner A: volver a consultar Empresa A | Dos sedes; Recepción sigue en Oficina Central | GET sedes y destinos 200 |

Solicitud de cuota: nombre sintético `Sede excedente — Verificación 20261114`. No se creó una tercera sede según la respuesta y la consulta posterior; se vació el campo local al terminar. Las consultas y denegaciones pueden producir registros de auditoría. No se modificaron cuotas, memberships ni designaciones.

A = `corp_f9e6900162c24716964e5ac190d2960d`.
B = `corp_cbf1b8df457d43d0bef55ec0d7deb6e6`.

La sesión GLOBAL corresponde a `axs_corp_sbx_global`; propietario de A: `axs_corp_sbx_owner_a`. Se confirmó la distinción mediante los controles del backend y los owners devueltos en pantalla. El ensayo terminó en el directorio de A con sesión propietaria; no se dejó una sesión GLOBAL activa.

## Versiones efectivamente observadas

| Superficie | Fuente observada |
| --- | --- |
| Frontend sandbox | SHA `3ba15f70ec890544e95bd50438f5a6b03c34b878`; deploy `bc92e94c-9251-482d-bd4e-493c445f5142` |
| Backend sandbox | Pin `3e10e1f597a7d4201c68b3dc7739205ab0c44094`; deploy `78c9d9fe-e09a-4f5a-b6d2-9dceb0401de6`, SUCCESS |
| Backend productivo (consulta de infraestructura previa al ensayo) | Pin `a68d1149242dd0b16cd0e363df3ccda917199423`; deploy `be9b87a6-8a58-4341-a181-b4fc70ebd808` |
| Frontend productivo (alias consultado) | `app.axs-mx.com` conserva `dpl_Dcd9Rw6L9FWn1PQBXRhjS9L2q17t` |
| Simulación del PR #109 | SHA `89556950cfe29feede067eb9e4a8ab48b5eeba38`; Tests y PostgreSQL RLS aprobados en CI |

El pin real del backend sandbox se tomó de Railway y prevalece para esta observación sobre los nombres históricos de las ramas/documentos. No atribuir el ensayo autenticado al candidato integrado de #104/#109: el sandbox no ejecuta ese árbol. Los resultados de CI del candidato son evidencia diferente.

## Evidencia conservada

Los [registros HTTP filtrados](AXS_CORPORATIVO_HTTP_SANDBOX_20261114.json) contienen únicamente hora UTC, método, ruta y estado. No incluyen IP, user agent, cabeceras, cuerpos, cookies ni tokens.

- [Superadmin autenticado](images/axs-superadmin-autenticado-20261114.jpg).
- [Directorio autorizado y Recepción](images/axs-owner-a-directorio-20261114.jpg).
- [Cruce Owner A → Empresa B rechazado](images/axs-owner-a-empresa-b-denegada-20261114.jpg).
- [Tercera sede rechazada por capacidad](images/axs-cuota-real-rechazada-20261114.jpg).

Las capturas son del navegador del ensayo; los estados HTTP se corroboraron mediante el conector Railway sobre el servicio API del sandbox.

## Límites y siguiente preparación

Esta sesión no verifica el recorrido inverso B→A con owner B, un alta empresarial nueva, altas exitosas de sedes/destinos, revocación de membership real, fallos de confirmación inyectados ni un ciclo ARCO real. Algunos de esos casos tienen evidencia histórica o sintética separada; no se dan por repetidos hoy.

Tampoco equivale a regresión autenticada de caseta residencial ni a aceptación productiva. No se fusionaron PR, cambiaron flags, ejecutaron migraciones o desplegaron servicios durante esta validación.

Siguiente paso: preparar el procedimiento para ejecutar el candidato integrado en un entorno de ensayo compatible. El contrato de arranque del sandbox contiene una constancia inicial con vencimiento histórico para nuevos arranques; revisar el ciclo de ensayo antes de redeplegar, sin renovar artificialmente vaciedad ni relajar los gates. Publicación frontend y activación piloto requieren su preparación y autorización correspondientes.
