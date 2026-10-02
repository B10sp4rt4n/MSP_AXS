# Reglas de acceso por condominio

Dos condiciones independientes, desactivadas por defecto: exigir propósito y exigir autorización previa. El administrador del condominio o su administrador MSP selecciona los tipos de visita y guarda la configuración desde Panel Admin → Reglas de acceso. No existe activación global ni intervención del proveedor AXS para operar las reglas.

Cuando se exige propósito, se captura un texto de hasta 500 caracteres. Capturarlo no prueba que el trabajo se haya realizado ni exige localizar al residente. Cuando se exige autorización, el residente preregistra su propia visita o la administración autoriza una visita pendiente. El servidor obtiene identidad y fecha de autorización de la sesión; el vigilante no puede emitirla ni proporcionar esos campos en un formulario. La autorización usa la ventana existente de la visita (30 minutos antes a 60 minutos después).

Las reglas se evalúan de nuevo al registrar cada entrada, tanto por QR como manualmente. La creación con entrada inmediata también está sujeta a ellas, incluido Otro destino. Un rechazo devuelve un motivo y termina la petición; no crea colas de aprobación, esperas ni escalamiento automático. La caseta continúa atendiendo. Una visita ya registrada conserva su salida disponible. Los cambios y las autorizaciones se conservan en el outbox transaccional con identidad, fecha y condominio.

Los cambios de reglas aplican a las siguientes entradas de visitas existentes. Visitas históricas no reciben autorizaciones retroactivas: si se activa la condición, un residente autorizado para esa vivienda o la administración debe autorizar expresamente la visita pendiente. Si se exige propósito, puede completarlo al autorizar. Un tipo desconocido se rechaza cuando existe una regla activa, para evitar evadir filtros con valores arbitrarios.

## Publicación

1. Aplicar `migrations/20261002_reglas_acceso.sql` en CORE antes de publicar el backend. Es una migración aditiva e idempotente, sin rellenar ni activar reglas en condominios existentes.
2. Publicar backend y frontend de este mismo cambio.
3. Abrir Panel Admin → Reglas de acceso. Mantener ambas opciones desactivadas hasta que cada condominio decida.

CORE serializa los cambios de reglas, las autorizaciones y las entradas mediante bloqueo de la fila del condominio; no se requiere cambiar las políticas RLS existentes de visitas.

## Validación

207 pruebas de backend correctas, incluidas 10 nuevas de reglas, autorización y aislamiento. 14 pruebas PostgreSQL se omitieron en la ejecución local porque requieren un servidor desechable. Frontend: compilación de producción y TypeScript correctos; el componente nuevo pasa ESLint. Los archivos existentes conservan advertencias/errores previos de ESLint sobre efectos y dependencias.

Las 11 pruebas nuevas también pasaron en CI con PostgreSQL 16, incluida la serialización concurrente de una regla y una entrada. Las fixtures de pruebas anteriores incluyen ahora usuarios, dependencia de la nueva referencia de autorización.
