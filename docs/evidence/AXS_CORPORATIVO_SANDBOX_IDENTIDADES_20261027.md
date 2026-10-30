# Preparación de conexiones e identidades — 27 de octubre de 2026

Autorizado por Salvador mediante «adelante» tras configurar Clerk Development y proporcionar dos subjects de prueba. Destino exclusivo: rama br-soft-leaf-b59xcclw del proyecto patient-tree-68362559, endpoint ep-bitter-snow-b5sgxc4h; bases axs_corp_core_sbx, axs_corp_gov_sbx y axs_corp_event_sbx.

## Verificación y certificación
La conexión PostgreSQL directa desde el ejecutor falló con OperationalError. Se utilizó el conector Neon para consultar los catálogos sin extraer datos personales. Se preservó el orden y tipos de cada columna como arrays JSON. Se ejecutaron localmente las funciones originales verify_permissions y snapshot del SHA ba70873b71b56e741548437c4a19f4b61ead26d6 contra los resultados reales: las cuatro cuentas cumplieron el contrato.

Huella CORE/provisioner: 9a4132bc1fa2489c84df6641908bfe9680398a94c9192d5542abab2b0a2a53fe
Huella GOV: 577f36f7ddff60043233800daf62a0269e54d064871e96af4d526d4f73a7d0c1
Huella EVENT: 6d4c5f8a8fe5a6d9c90b257b970afc703078687340bf19a15d303c81521a9fbd

Se registró la constancia inicial en cada base, con bloqueo ACCESS EXCLUSIVE de todas las tablas y nueva comprobación de vaciedad dentro de cada transacción, inspector BYPASSRLS y nombre exacto de base. Los hashes se calcularon antes de esas transacciones; no constituyen una captura atómica de los tres catálogos. Las bases no tenían procesos de aplicación desplegados. No se modificaron DDL ni ACL entre la lectura y la escritura de las constancias.

UUID compartido: 27a43797-2e40-46fb-805b-89dcc8d0c06a.
Issuer: https://vocal-bee-4163.clerk.accounts.dev.
Vencimiento más temprano: 2026-10-28T17:54:09.117Z (28 de octubre, 11:54 CDMX). Se comprueba al arrancar; no detiene por sí solo un proceso en ejecución.

## Siembra y permisos
Después de certificar se registraron solamente:
- Un MSP sintético: axs_corp_sbx_msp.
- Dos identidades CORE vinculadas a los subjects Development proporcionados por Salvador, con nombres y correos sintéticos.
- Una autoridad GLOBAL activa para axs_corp_sbx_global.
- La identidad axs_corp_sbx_owner_a no tiene autoridad GOV ni membresía empresarial todavía. Queda disponible para asignarla al crear una empresa por el flujo Superadmin.

Consultas posteriores verificaron dos usuarios, una coincidencia por cada subject y una sola autoridad GLOBAL; el owner tiene cero autoridades. No se importó el directorio completo de Clerk ni se enviaron invitaciones.

## Conexiones
Se habilitó LOGIN y se generó una contraseña independiente SCRAM-SHA-256 para cada una de las cuatro cuentas, rechazando la operación si alguna ya admitía LOGIN o tenía atributos incompatibles. No se alteraron privilegios, membresías o propiedad.
El conector Neon confirmó current_user y current_database con cada rol dedicado, y cada conexión pudo leer la constancia con UUID e issuer correctos. Esto no sustituye la prueba desde Railway con las URLs staged.
Las cuatro URLs y el alias CORE se guardaron exclusivamente como variables pendientes del servicio axs-corporativo-api-sandbox; los secretos no se incluyen en este registro ni se almacenan en Git.

## Railway: pendiente, sin despliegue
- Fuente fijada a ba70873b71b56e741548437c4a19f4b61ead26d6.
- Predeploy corregido a check_corporate_sandbox_config + check_corporate_sandbox_data; retirado el verificador residencial check_core_rls.
- Añadidos DATABASE_CORE_URL, DATABASE_URL, DATABASE_GOV_URL, DATABASE_EVENT_URL, DATABASE_CORPORATE_PROVISIONING_URL y AXS_CORPORATE_SANDBOX_RUN_ID.
- Se conservaron las variables Clerk y el secreto interno preparados previamente.
- Faltan frontend aislado/CORS definitivo y fase runtime explícita con sus flags. La configuración aún no debe desplegarse.

No se certifica todavía una sesión Clerk real ni un recorrido HTTP end-to-end. Producción, San Luis y las bases heredadas permanecen fuera de estas operaciones. Si la constancia vence antes del primer arranque, no se borra ni se recertifica la base poblada a la fuerza: se requiere resolver el ciclo de ensayo según el procedimiento revisado.
