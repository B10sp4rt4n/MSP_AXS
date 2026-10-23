# Ensayo desplegado ARCO en Development

Resultado: backend y frontend desplegados con estado SUCCESS. Ensayo HTTP aprobado: 32 comprobaciones, dos expedientes sintéticos cerrados, cuatro transiciones por expediente y versión final 5. Verificación posterior en PostgreSQL: cero pendientes y un solo expediente por folio. No habilita ARCO en producción comercial ni acredita atención de una solicitud real.

## Alcance autorizado y aislamiento

Proyecto Railway AXS Development `c04faff4-37ba-4df4-a6ce-a4d5d5ff881b`; entorno técnico `5f5b4e0c-c4ce-457c-96a4-b65ebf723354`, cuyo nombre en Railway es production, distinto del proyecto productivo `532a32f5-6313-4ee3-98de-cfcfc225dbb7`.

Base de desarrollo: proyecto Neon `patient-tree-68362559`, rama `br-blue-frog-b5o2ccsk`, endpoint `ep-withered-resonance-b59tusv3`, base CORE `neondb`. La rama contiene registros previos: no se afirma que toda la base sea sintética. El ensayo se limita a `axs_demo_condo_a` y `axs_demo_condo_b` y a sus operadores ficticios existentes.

La revisión de compatibilidad detectó columnas/tablas de identidad progresiva, Alexa y solicitudes remotas ausentes respecto al modelo actual. Se aplicaron las migraciones aditivas de identidad progresiva (catálogo de proveedores inicial incluye Amazon), Alexa, solicitudes remotas y ARCO en una transacción. Para la tabla ARCO nueva se creó la política sin ejecutar DROP POLICY. No se borraron filas ni se alteraron registros existentes. Se verificó RLS habilitado y forzado en arco_cases.

Servicios backend y frontend de Development fijados al commit `a421ef4640b9937c5e4eb22472c22a5778dfc716`, con los chequeos previos de endpoints de desarrollo y RLS conservados. No se cambiaron credenciales ni endpoints de producción. ARCO se limita por designación a `axs_demo_admin_a:axs_demo_condo_a` y `axs_demo_admin_b:axs_demo_condo_b`.

## Ejecutor

`scripts/development_arco_smoke.ts` se ejecuta una sola vez en el operador existente, sin dominio público ni reinicio automático, reutilizando su referencia privada al secreto de pruebas. Verifica APP_ENV y endpoint de Development antes de llamar a la API; nunca registra tokens o contenido privado.

Actores: identidades locales ficticias existentes. No equivale a sesiones Clerk reales ni a verificación de identidad de una persona. El script recorre recepción, verificación declarada, resolución, ejecución declarada y cierre en dos folios sintéticos. Comprueba anonimato, acceso cruzado, versiones obsoletas, cierre con pendientes e historial. No solicita eliminación de fotos, no envía comunicaciones y no acredita entrega efectiva al titular; las referencias de decisión/ejecución son simuladas.

Al terminar, restaurar la configuración anterior del operador y deshabilitar la activación ARCO de Development cuando el ensayo haya concluido. Mantener el despliegue fijado y la evidencia de resultado. La activación para personal real requiere identificar y designar al operador y repetir el recorrido con sesión real.

## Cierre del ensayo

Se deshabilitó ARCO y se retiraron las designaciones en Development, además de ocultar el enlace de Configuración. Ambos redespliegues confirmaron SUCCESS. Un segundo ensayo autenticado aprobó dos comprobaciones: la API devuelve 404 para cada operador ficticio. Sin sesión se mantiene 401 por el middleware general. Se confirmó también la entrega de diez eventos de auditoría, sin las referencias privadas revisadas en sus payloads. La configuración anterior del ejecutor se restauró sin iniciarlo otra vez; el proceso ARCO terminó y no tiene cron ni reinicio automático.

Evidencia: [resultado estructurado](evidence/arco-development-20261022.json). La prueba valida el registro y seguimiento asistido contra la API desplegada y PostgreSQL; no una sesión real Clerk, una solicitud humana ni la eliminación de datos. Las pruebas de navegador previas usaron transporte simulado, no se presentan como una navegación autenticada en este despliegue.
