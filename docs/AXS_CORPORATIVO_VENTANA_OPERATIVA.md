# Ventana operativa del sandbox C5

La constancia inicial de vaciado y catálogo (`corporate_sandbox_attestation`)
conserva sus valores originales y su límite histórico de 24 horas. No se vuelve
a certificar una base con datos, no se modifica su expiración y no se cambian
permisos, RLS, esquema, usuarios ni visitas para prolongar el ensayo.

## Autorización independiente y explícita

Un manifiesto versionado en `sandbox_authorizations/<UUID>.json` identifica la
aprobación del operador, motivo, run, emisor Clerk de pruebas, inicio y fin UTC.
El fin debe estar dentro de los siete días desde la aprobación registrada.
El manifiesto vincula las tres constancias originales: base, huella del catálogo,
fecha de certificación y vencimiento original. No contiene credenciales.

Solo se carga mediante `AXS_CORPORATE_SANDBOX_AUTHORIZATION_ID=<UUID>` en el API
del sandbox, con fase `runtime`, perfil `visits-20261115` y bandera sandbox activa.
Sin selección explícita se conserva el contrato anterior de 24 horas. Un archivo
ausente, revocado, futuro, vencido, de otro run o de otra identidad impide arrancar.
No hay generación, ampliación ni selección automática de autorizaciones.

## Validaciones

En cada arranque/predeploy se comprueban las cuatro conexiones CORE/GOV/EVENT y
PROVISIONER, endpoint, nombres y roles fijos, privilegios mínimos, RLS forzado,
catálogo completo y esquema de visitas. La autorización no evita ningún control
de integridad ni otorga privilegios adicionales. La verificación solo lee.

El proceso conserva el vencimiento verificado. Cada petición se bloquea con 503
y `Cache-Control: private, no-store` al llegar a ese instante, sin necesidad de
reiniciar. Los healthchecks `/` y `/health` siguen disponibles para diagnóstico;
no implican que el ensayo siga autorizado. El middleware solo se instala en el
sandbox y queda dentro de CORS. Los sockets también se cierran al vencer.

## Cierre y nueva habilitación

Para cierre anticipado inmediato, detener el deployment del API en Railway
(o escalar sus réplicas a cero). Después retirar la selección de autorización y
registrar el cierre mediante un commit. Un despliegue rechazado durante predeploy
no detiene por sí solo el proceso anterior: no debe usarse como mecanismo de cierre.

Una nueva habilitación exige nueva aprobación, nuevo UUID y revisión del catálogo
y las constancias antes de publicar/seleccionar otro manifiesto. No modificar el
manifiesto original ni sus fechas para simular una aprobación nueva.

Esto habilita únicamente pruebas con datos sintéticos; no autoriza producción,
datos de clientes, nuevos permisos ni cambios en la política de conservación.

## Evidencia de aceptación

Pruebas de ventana UTC, frontera exacta de siete días, zona sin sufijo rechazada,
run/emisor equivocado, revocación, selección ausente, rutas arbitrarias, huella o
constancia alterada; bloqueo de una petición tras vencer con el mismo proceso.
El ensayo PostgreSQL existente verifica CORE/GOV/EVENT/PROVISIONER con una
autorización separada, constancias expiradas intactas y rechazo de deriva de catálogo.


## Precisión en la captura de evidencia

Exportar `certified_at::text` y `expires_at::text` directamente desde PostgreSQL.
No usar la serialización de fechas JavaScript del conector: puede recortar los
microsegundos a milisegundos e impedir la coincidencia exacta con la constancia.
Una corrección de captura se registra con otro UUID y referencia `supersedes`,
conservando aprobación, inicio y fin operativos. El manifiesto anterior se
conserva como evidencia del intento fallido; no se rebaja la comparación exacta.
