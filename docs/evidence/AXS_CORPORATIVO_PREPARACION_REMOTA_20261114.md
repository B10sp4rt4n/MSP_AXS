# Preparación remota del ensayo integrado — 14 noviembre 2026

## Estado final: preparado, sin publicar

Código: `a2b88a34f2141b36dcde8d8d5630d5ae2c254c18`, PR #110.
Railway: proyecto AXS Corporativo Sandbox `cf44e5f4-1a41-4d25-a13e-a39211cda7b6`, entorno `cd1b2ff7-509e-4c6b-9ea0-c537295d4cd3`.
Patch pendiente: `9ac8563f-3cc6-415d-8e0a-a678dbf5cdf0`, 19 cambios sobre dos servicios, no destructivo y sin variables compartidas.

Salvador autorizó continuar y posteriormente autorizó aplicar el paquete únicamente en sandbox. Los dos intentos de `accept_deploy` fueron cancelados por el control de aprobación con el mensaje «Cancelled — the user did not approve this action. No changes were made». No se usó CLI, navegador ni otro canal para aplicar el cambio bloqueado. El ensayo autenticado del candidato sigue pendiente.

## Validación de código

- [Tests 43592460216](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43592460216): SUCCESS, 1,214 Python aprobadas / 73 omitidas, cobertura 82 %. Frontend/roles/tipos y navegador aprobados.
- [PostgreSQL 43592460258](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43592460258): SUCCESS, 123 + 12 pruebas PG16 y 3 del catálogo PG18. Incluye perfil nuevo, roles segregados, certificación vacía, rechazo de certificado vencido y rechazo del rol de sandbox fuera de sandbox.
- Pruebas locales dirigidas: 87 aprobadas. No equivalen a ejecución de gates con configuración real de Railway.

## Bases, permisos y constancias

Se crearon sólo tres bases en la rama existente `br-soft-leaf-b59xcclw`, endpoint existente `ep-bitter-snow-b5sgxc4h`. No se crearon proyectos, endpoints ni servicios adicionales.

| Dominio | Base | Huella del catálogo |
| --- | --- | --- |
| CORE | axs_corp_core_sbx_20261114 | a5e70427b827762d98cc56f987ca715367f21ea4df0a05739a1d8c5c0172ff3b |
| GOV | axs_corp_gov_sbx_20261114 | 736652d103f077d5a333aba6cfcb14bdd8283c783db7f9ebf094792c4881504d |
| EVENT | axs_corp_event_sbx_20261114 | e72ee54c47c4e97d6de233d69eea89dee3d6c0ae08dbfaa31059b4ed41747885 |

Se instaló DDL del ORM, C2/C4 y los permisos del bundle revisado. Cuatro roles nuevos, sufijo `_20261114`, sin membresías, propiedad, DDL, INHERIT ni BYPASSRLS. Los verificadores originales `verify_permissions` y `snapshot` se ejecutaron localmente contra un adaptador de catálogos reales obtenidos por el conector Neon, no mediante conexión directa del ejecutor. Los cuatro contratos dieron PASS.

La primera consulta auxiliar de cotejo de certificación falló por número de columnas y su transacción revirtió; se comprobó cero certificados y cero usuarios antes de corregirla. La lectura inicial del catálogo estaba limitada por filas: fue reemplazada por lecturas agregadas completas. La evaluación y huellas finales utilizan esas lecturas completas (CORE: 3,069 filas de metadatos; GOV: 385; EVENT: 226).

La certificación final bloqueó todas las tablas en cada base, cotejó dentro de la misma transacción el catálogo completo esperado y verificó cero filas en todas las tablas antes de insertar la constancia. No es una operación atómica entre las tres bases; las tres quedaron verificadas con el mismo UUID.

- Run ID: `1917d6a4-bd60-499f-b719-1ddc30ea725f`.
- Issuer: `https://vocal-bee-4163.clerk.accounts.dev`.
- CORE: 14-nov 12:06:34.916 UTC → 15-nov 12:06:34.916 UTC.
- GOV: 14-nov 12:06:35.748 UTC → 15-nov 12:06:35.748 UTC.
- EVENT: 14-nov 12:06:36.505 UTC → 15-nov 12:06:36.505 UTC.
- Vencimiento más temprano: **15 de noviembre, 06:06:34 CDMX**.

Se sembraron offline el MSP sintético, tres identidades con los subjects Clerk Development ya utilizados y una autoridad GLOBAL para `axs_corp_sbx_global`. No se copiaron empresas, viviendas, visitas ni evidencias del ensayo anterior. Se habilitó LOGIN con contraseñas independientes sólo en los roles nuevos; URLs nuevas transportadas a variables pendientes del backend. Este expediente no contiene contraseñas, subjects, tokens ni conexiones.

## Paquete pendiente

Ambos servicios fijados al mismo SHA:
- Backend: `e395d483-dd09-4f50-a1e8-415787be5b30`.
- Frontend: `94571cbd-cf97-4487-95ea-0c84054e6428`.

Backend: perfil `integrated-20261114`, run ID nuevo, cinco URLs (alias CORE incluido), fase runtime y funciones corporativas para ensayo. Designaciones ARCO vacías; deberán establecerse explícitamente si se ensaya privacidad con nuevas empresas. Clerk, CORS, dominios y comandos de predeploy existentes se conservan. Los valores secretos están en Railway, no aquí.

No se han ejecutado gates de predeploy reales ni LOGIN desde Railway con las conexiones nuevas, ni se han observado build, healthcheck o HTTP autenticado del nuevo SHA. Esos pasos requieren aplicar el paquete y esperar SUCCESS.

## Servicios que siguen activos

- API sandbox: deploy `78c9d9fe-e09a-4f5a-b6d2-9dceb0401de6`, SUCCESS.
- Web sandbox: deploy `bc92e94c-9251-482d-bd4e-493c445f5142`, SUCCESS.
- Backend productivo: deploy `be9b87a6-8a58-4341-a181-b4fc70ebd808`, SUCCESS; entorno sin cambios preparados.

Las bases/roles/constancias del ensayo anterior permanecen. Su constancia vencida no permite prometer una reversión mediante nuevo arranque del backend anterior.

## Continuación

Resolver la aprobación de publicación del patch de sandbox. Antes de aplicarlo, revisar otra vez alcance, SHA, constancias vigentes y estado actual. Si las constancias nuevas vencen antes de publicar, detener: no ampliar fechas ni recertificar bases sembradas. Requiere otro conjunto fresco revisado.

Después de publicación satisfactoria, repetir el recorrido autenticado del candidato: GLOBAL, alta A/B, cuotas durables, owner por empresa, sedes/destinos y rechazos cruzados. La evidencia autenticada previa corresponde a versiones anteriores del sandbox y no sustituye ese recorrido.
