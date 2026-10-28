# Ensayo de actualización sobre catálogo CORE objetivo

## Procedencia y alcance

Se capturó por consultas SELECT a catálogos, el 28 de octubre de 2026, la
estructura pública de `patient-tree-68362559`, rama `br-empty-firefly-b5ob1gsg`,
base `neondb`. La versión observada fue PostgreSQL **18.6**.
Railway oculta las conexiones efectivas: esta captura no demuestra por sí sola
que el servicio esté conectado a ese host/base; esa correspondencia sigue
siendo una condición previa a una liberación remota.

El fixture `tests/fixtures/corporate_upgrade/core_catalog_20261028.json` contiene
17 tablas, 162 columnas, 53 índices, 133 constraints (74 NOT NULL), 9 secuencias
y dos enums. Incluye defaults, claves, CHECK, RLS, políticas, grants de tabla y
columna y parámetros/propiedad de secuencias. La consulta reproducible queda
en `capture_core_catalog.sql`. No incluye filas, valores actuales de secuencias,
contraseñas, cadenas de conexión ni registros de titulares.

La inspección adicional encontró únicamente el esquema público de aplicación,
sin vistas, particiones, funciones propias, triggers propios, collations de
columna especiales ni opciones de tabla no predeterminadas; `plpgsql` es la
única extensión observada. Los enums son `accesslevel` y `scopestatus`.

## Reproducción y comprobaciones

El job `corporate-target-catalog` de PostgreSQL RLS gate utiliza un contenedor
PostgreSQL 18 independiente del job histórico en PostgreSQL 16. Cada prueba
crea una base local vacía y roles únicos sin LOGIN. Las guardas rechazan hosts
remotos, bases diferentes de `postgres` para el administrador y otra versión
mayor. No recibe secretos de Neon ni credenciales productivas.

Antes de insertar datos o aplicar migraciones, cada prueba vuelve a capturar
los catálogos y compara todos los objetos estructurales del fixture. Solo
normaliza el propietario local y excluye contexto del proveedor. Si la
restauración pierde una columna, constraint, índice, policy o grant, falla.

Después siembra dos tenants residenciales ficticios con viviendas, usuarios,
casetas, visitas, evidencias y outbox. Ejecuta los archivos SQL reales
C0→C1→C2→C4, cambiando únicamente los nombres de los roles para aislar tests.
La comparación antes/después exige conservar filas y controles de las tablas
anteriores, exceptuando las adiciones explícitas de C0 y grants del provisioner.

El ensayo añade tres escenarios:

1. Consultas/INSERT/UPDATE con los modelos CORE exactos de `main@76bc9d6`,
   actualización completa, modelos integrados y regreso a modelos anteriores
   conservando las adiciones de esquema. Se consultan tenant, usuario, vivienda,
   visita y evidencia; todos los tenants previos y nuevos siguen residencial/false.
2. Excepción antes del COMMIT de C4: catálogo y filas deben quedar idénticos a
   C0/C1/C2; el gate rechaza el estado incompleto. Luego C4 debe completar y
   su repetición debe fallar con 42P07 sin perder los registros anteriores.
3. Gates corporativo y RLS vigentes bajo el rol runtime, aislamiento de visitas,
   casetas, evidencias y outbox, ACK permitido, modificación de payload y
   escritura cruzada rechazadas, sin DDL ni lectura del journal privilegiado.

Los modelos antiguos se obtienen en CI mediante `git show` del SHA productivo
fijado. Se cargan en registros SQLAlchemy separados y sin importar sus motores;
no se ejecuta `create_all` para rellenar huecos del catálogo.

## Límites de interpretación

Se reproduce el catálogo público capturado y los permisos de aplicación; el
propietario local es PostgreSQL de CI. No se recrean `cloud_admin`,
`neon_superuser`, sus membresías o default ACLs administrados por Neon; tampoco
se habilitan LOGIN ni credenciales de provisión. Los default ACLs observados
pertenecen a `cloud_admin`; las tablas capturadas pertenecen a `neondb_owner`.
El comportamiento del ejecutor de migraciones y sus permisos efectivos debe
validarse en el destino elegido antes de aplicar cambios remotos.

La prueba con los modelos anteriores/integrados no equivale al arranque de
ambos servicios completos ni a una regresión HTTP de todos sus endpoints.
Las suites existentes cubren sus propios flujos por separado. Tampoco ensaya
volumen, tiempos de bloqueo, concurrencia productiva o datos reales; esos
factores pueden afectar una ventana de cambio.

El resultado de CI y el SHA final se registran en el PR #103 para conservar
el mismo commit después de verificarlo. Este trabajo no aplica SQL remoto,
no altera despliegues y no fusiona a `main`.

## Condiciones concretas para liberar

1. Confirmar conexiones efectivas CORE/EVENT/GOV con la configuración del
   servicio y fijar los SHAs anterior y nuevo, sin publicar credenciales.
2. Acordar ventana, cuenta de migración, respaldo recuperable, límites de
   bloqueo/espera y control de despliegues automáticos de Railway/Vercel.
3. Revisar los SQL propuestos y su autorización de uso remoto: los encabezados
   de C1/C2/C4 los delimitan a ensayo. No ejecutar los grants/bootstrap de sandbox.
4. Aplicar C0→C1→C2→C4 con el ejecutor separado del runtime. Verificar
   preservación residencial y correr ambos gates bajo la identidad efectiva.
   Si C4 está presente o su resultado es incierto, inspeccionar; no repetirlo.
5. Publicar backend y verificar regresión HTTP residencial con el esquema ya
   preparado; después frontend. Mantener las funciones corporativas/provisión
   apagadas hasta completar la habilitación específica.
6. Si se necesita revertir aplicación, volver a los SHAs anteriores conservando
   las adiciones compatibles y todas las escrituras. No ejecutar DROP ni una
   restauración global automática. Verificar los endpoints tras la reversión.
