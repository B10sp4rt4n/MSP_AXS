# Gate de esquema y ensayo de actualización corporativa

Esta propuesta incorpora un gate de solo lectura antes de `create_all` en el
arranque normal con PostgreSQL. Un esquema incompleto detiene el arranque,
incluso con funciones corporativas desactivadas: los modelos residenciales
también consultan las columnas nuevas de C0. SQLite conserva su flujo local;
el sandbox corporativo conserva sus verificaciones específicas.

## Secuencia de preparación

1. Confirmar el destino CORE efectivo y la identidad del ejecutor, disponer de
   respaldo y acordar la ventana y recuperación antes de cualquier operación remota.
2. Revisar y aplicar explícitamente, con el propietario de esquema, en orden:
   `20261023_tenant_modalidad_c0.sql`, `20261023_corporate_directory_c1.sql`,
   `20261023_corporate_superadmin_c2.sql` y
   `20261023_corporate_reconciliation_c4.sql`.
3. Ejecutar `python -m scripts.check_corporate_schema` con `DATABASE_CORE_URL`
   apuntando al CORE elegido y con la identidad runtime. La salida esperada es
   `{"gate": "PASS", "schema": "public", "corporate_tables": 6}`; el error
   devuelve código 1 y no incluye cadenas de conexión ni datos de filas.
4. Conservar el gate independiente `python scripts/check_core_rls.py` y revisar
   los privilegios efectivos y las conexiones de los otros servicios.
5. Solo después evaluar el despliegue del backend y frontend integrados.

El gate consulta catálogos dentro de una transacción `READ ONLY`. Comprueba
columnas requeridas, tipos/defaults seleccionados de C0/C4, claves primarias y
foráneas validadas, índices únicos y el índice parcial de pendientes, presencia
de CHECK nombrados y validados, RLS forzado y políticas tenant exactas en las
seis tablas corporativas. No compara todas las definiciones CHECK, tipos o
privilegios; no sustituye una auditoría completa de esquema o permisos.
No exige RLS en la tabla raíz residencial `condominios_exo`.

El comando no ejecuta migraciones, no aprovisiona empresas y no importa los
motores ni el arranque del backend. No usa `DATABASE_URL` como destino alterno.
Puede añadirse al predeploy además del gate RLS, pero este cambio de código
no modifica la configuración remota de Railway.

## Ensayo reproducible en CI

`tests/smoke/test_corporate_upgrade_postgres.py` usa únicamente PostgreSQL local
desechable de CI (`axs_rls_ci`), esquemas y roles únicos y datos sintéticos.
Parte de un esquema legado representativo; no es un clon del catálogo completo
de producción ni una prueba de sus datos o de todos los flujos residenciales.

El ensayo ejecuta los cuatro archivos SQL reales, adaptando únicamente el
esquema/roles al aislamiento del test. Verifica:

- rechazo del gate antes de completar cada etapa;
- repetición soportada de C0/C1/C2 y rechazo de la repetición de C4;
- rollback atómico de C4 si falla antes de su `COMMIT`, seguido de aplicación correcta;
- conservación de filas y consultas/INSERT/UPDATE residenciales anteriores;
- valores residenciales predeterminados en INSERT que omite columnas C0;
- rechazo de ocho alteraciones de columnas, defaults, RLS, FK, índice, CHECK y políticas;
- bloqueo de DDL por la transacción de solo lectura y lectura de catálogos por el runtime.

C4 es de una sola aplicación. Si existe el journal o hay duda sobre una ejecución
anterior, inspeccionar el catálogo y el estado transaccional; no repetir a ciegas.
Un fallo del gate después de C4 no autoriza a borrar el journal. Una recuperación
de aplicación debe conservar las columnas y tablas añadidas y sus datos; las
consultas legacy ensayadas toleran esas adiciones.

No se incluye el bootstrap de sandbox, sus grants particulares ni las migraciones
ARCO en esta secuencia CORE. Este ensayo no modifica Neon, Railway, Vercel ni
`main`, y no acredita visitas corporativas ni el procedimiento ARCO completo.
