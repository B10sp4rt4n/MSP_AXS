# Candidato integrado publicado — 14 noviembre 2026

Este registro continúa la preparación anterior; no borra los rechazos históricos de aprobación. Salvador aplicó el patch desde la pantalla de Railway. Los dos servicios ejecutan el SHA `a2b88a34f2141b36dcde8d8d5630d5ae2c254c18`.

| Servicio | Deploy | Resultado |
| --- | --- | --- |
| Backend sandbox | 37873cf3-4db4-4e47-8e14-b78482582df8 | SUCCESS / Online, 06:18:06 CDMX |
| Frontend sandbox | d8009c46-6c25-4db8-b5e8-ad1cf46d978d | SUCCESS / Online, 06:17:24 CDMX |

Gates reales del backend:
- 06:17:33 CDMX: configuración del sandbox verificada.
- 06:17:42 CDMX: deployment gate PASS sobre la fase seleccionada.
- 06:18:00 CDMX: startup completo y worker de auditoría durable iniciado.
- 06:18:03 CDMX: GET /health 200.

Los gates se ejecutaron en Railway con sus conexiones nuevas; esta evidencia supera el límite previo de revisión local por adaptador. No se publicaron servicios productivos ni se fusionó main.

## Recorrido autenticado del mismo SHA

Login Clerk Development del GLOBAL completado en captura segura. No contiene credenciales este expediente. A través de la interfaz real se verificaron los dos owners existentes, se crearon las dos empresas deshabilitadas, se guardaron cuotas durables con revisión 1 y se habilitó cada directorio después de consultar confirmación CORE/GOV.

| Empresa | Tenant | Owner | Capacidades confirmadas |
| --- | --- | --- | --- |
| A — Ensayo integrado 20261114 | corp_614445133fde465dbc0d14005ccde848 | axs_corp_sbx_owner_a | 2 sedes; 1 destino por sede |
| B — Ensayo integrado 20261114 | corp_290409a46d4d4a47afb569ae3c1a7635 | axs_corp_sbx_owner_b | 1 sede; 1 destino por sede |

Ambas operaciones de cuotas aparecen `confirmed` en el journal CORE. Las cuatro políticas GOV activas coinciden con esas capacidades. Estas consultas corroboran ambos dominios; no se afirma transacción distribuida atómica.

HTTP real del backend:
- GET de verificación de cada owner: 200.
- POST de alta de A y B: 201.
- PUT de capacidades y GET de consulta de cada empresa: 200.
- POST de habilitación de cada directorio: 200.
- GLOBAL sin membresía, GET de sedes de A y B: 403 en ambos.

Una espera de selector de la automatización venció mientras se guardaban cuotas de B. La lectura posterior mostró confirmación satisfactoria; no se repitió el PUT ni se creó una segunda operación.

## Pendiente de completar

El acceso del propietario de A quedó en Clerk: dos entradas en la captura segura recibieron `Couldn't find your account`. No se verificó qué valor secreto fue presentado ni se creó una cuenta alternativa. La cuenta usada con éxito en el ensayo anterior fue `salvador.ruiz+pruebas@synappssys.com`; las referencias anteriores no sustituyen autenticación actual.

Se ofrece control manual del formulario para resolverlo. En este candidato siguen pendientes el recorrido positivo del owner, altas de sedes/destinos, cuotas por rechazo y cruce A→B. No trasladar a este SHA resultados de la sesión anterior sobre otras versiones.

Las constancias nuevas vencen el 15-nov-2026 a las 06:06 CDMX para futuros arranques. Su vencimiento no detiene automáticamente procesos iniciados. No ampliar fechas ni recertificar bases pobladas. La evidencia sintética de CI se conserva separada: 1,214 Python / 138 PostgreSQL, frontend y navegador aprobados.
