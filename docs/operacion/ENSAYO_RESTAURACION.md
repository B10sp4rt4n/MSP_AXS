# Ensayo de respaldo y restauración

## Alcance

`tests/smoke/test_restore_drill_postgres.py` ejecuta pg_dump/pg_restore reales sobre
PostgreSQL desechable de CI, con modelos CORE, GOV y EVENT y datos sintéticos.
Acepta únicamente AXS_TEST_POSTGRES_URL local, base/usuario axs_rls_ci y sin
parámetros adicionales. Nunca usa DATABASE_URL ni las conexiones productivas.
Cada ejecución crea y elimina exclusivamente sus esquemas con UUID propio.

El ensayo agrupa los tres dominios en un esquema para obtener una instantánea
consistente con un único pg_dump. No acredita restauración coordinada entre
bases productivas separadas, roles, RLS de producción, Clerk ni archivos de
Cloudinary. La evidencia sintética comprueba referencias y hashes almacenados,
no descarga ni recupera objetos externos.

## Comprobaciones automáticas

1. Sembrar relaciones MSP → condominio → vivienda → usuarios/visitas/evidencias,
   tres vías de autorización (scope, membresía MSP y autoridad global), delegación
   y eventos publicados con el servicio de outbox.
2. Respaldar sólo el esquema del ensayo, registrar SHA-256 y duración.
3. Después del respaldo, consumir un QR, revocar un scope y publicar el evento.
4. Conservar esa fuente más reciente bajo otro nombre; restaurar el archivo en
   un espacio vacío mediante una transacción y con salida inmediata ante error.
5. Comparar todas las filas de todas las tablas con el punto respaldado;
   comprobar integridad de eventos y recuperación de secuencias.
6. Demostrar que el respaldo antiguo devuelve el scope activo y permite consumir
   otra vez el QR. La prueba de consumo se revierte con una transacción externa.
7. Aplicar cuarentena únicamente al esquema restaurado: revocar scopes,
   membresías, autoridades y delegaciones; cancelar visitas pendientes/activas e
   invalidar sus QR. Verificar denegación con los servicios reales, conservar
   visitas ya ingresadas, evidencias, eventos y outbox, y comprobar que la fuente
   posterior al respaldo sigue intacta.

La cuarentena es una medida ensayada dentro del test, no una funcionalidad nueva
ni un bloqueo automático instalado en producción. La aplicación restaurada debe
permanecer desconectada del tráfico y de workers hasta terminar la conciliación.

## Procedimiento para una recuperación real

1. Mantener el destino aislado, sin tráfico de usuarios, tareas programadas ni
   publicación de outbox. Identificar incidente, responsable y hora de corte UTC.
2. Preservar la fuente y la evidencia del incidente. Elegir un punto de recuperación
   y verificar respaldo, checksum, versión de PostgreSQL y disponibilidad de claves.
3. Restaurar en recursos nuevos. Si CORE, GOV y EVENT son bases distintas, acordar
   cortes compatibles; conciliar outbox por event_uid, incluidos los entregados en
   CORE que falten en EVENT. No marcar entrega ni descartar eventos a ciegas.
4. Comparar filas, relaciones, secuencias, hashes, restricciones, roles y políticas
   RLS. Verificar por separado identidades externas y objetos/evidencias.
5. Mantener denegados los accesos hasta reconstruir revocaciones y usos de QR
   posteriores al respaldo desde evidencia independiente confiable. Si no existe,
   invalidar permisos y QR potencialmente obsoletos y reautorizar explícitamente.
   Conservar las personas que figuraban dentro; conciliar físicamente entradas y
   salidas posteriores al corte antes de confiar en la ocupación recuperada.
6. Registrar cada decisión de conciliación y la cuarentena sin reescribir el ledger
   histórico. Validar rechazo de credenciales antiguas y acceso nuevo autorizado.
7. Sólo después de estas comprobaciones conectar aplicación/workers al destino;
   supervisar duplicados y denegaciones. Conservar la fuente anterior para análisis.

## Medición y criterios

El gate emite `AXS_RESTORE` con número de tablas/filas, bytes, checksum y segundos
de dump, restore y validación/cuarentena. Son tiempos del fixture pequeño de CI,
no RTO productivo. El RTO real incluye detección, aprovisionamiento, recuperación,
conciliación y reapertura. La pérdida posterior al corte se demuestra con un uso
de QR, una revocación y su evento; no establece un RPO contratado.

Ejecutar mediante el gate `PostgreSQL RLS gate` o con un PostgreSQL local
desechable con el mismo usuario/base, pg_dump y pg_restore instalados:

```sh
python -m pytest -q --no-cov tests/smoke/test_restore_drill_postgres.py
```

Sin AXS_TEST_POSTGRES_URL la prueba se omite; una omisión no es evidencia de
restauración correcta. Ante cualquier discrepancia, no reabrir el destino.
