# Entrada corporativa por cuenta

Después de iniciar sesión, el inicio residencial podía mostrar «casa sin asignar»
a un propietario corporativo. Entrar por Superadmin tampoco resolvía el acceso:
esa consola exige autoridad GLOBAL, independiente de la membresía empresarial.
Los formularios de inicio de sesión y alta ahora fijan `/dashboard` como destino
alternativo, manteniendo los enlaces de retorno que Clerk valide. Esto prevalece
sobre un fallback del ambiente que apuntaba a Superadmin, sin cambiar variables.

El frontend recuerda la última empresa y sede consultadas satisfactoriamente por
cada identidad Clerk. Al volver a `/dashboard`, consulta de nuevo las capacidades
vigentes en el backend. Propietario/administrador abren el directorio; anfitrión y
recepción abren las visitas de la sede. No se confía en un rol guardado ni en un
correo para autorizar. No se añaden permisos, endpoints, variables ni migraciones.

## Primer acceso y límites

La primera visita requiere el enlace de empresa/sede proporcionado por el
administrador. Sin ese contexto, el inicio ofrece «Acceso corporativo», donde se
puede indicar una empresa. No existe descubrimiento automático de membresías:
el API actual requiere seleccionar un tenant antes de consultar su directorio.
La preferencia es local a este navegador, está separada por identidad y contiene
solo identificadores; no persiste tokens, nombres, roles o visitas.

El almacenamiento es opcional. Si está bloqueado, los enlaces directos continúan
funcionando. Una preferencia manipulada nunca concede acceso: el backend vuelve
a comprobar membresía, empresa, sede y rol. Ante revocación o error no se redirige
a un portal residencial como alternativa. «Usar otro acceso» borra únicamente la
preferencia de la cuenta actual, sin modificar sus permisos.

## Validación

La regresión DOM sintética cubre propietario, administrador, anfitrión, recepción,
rol desconocido, rechazo, sesión ausente, contexto manipulado, cuentas distintas y
cambio de identidad mientras se comprueban capacidades. Usa fronteras de Clerk,
API y router simuladas. No equivale a dos sesiones Clerk reales en el sandbox.

Antes de aceptar la prueba independiente deben existir dos identidades Development
distintas, con membresías `reception` y `host` y asignación activa a una sola sede
de una empresa sintética. La cuenta propietaria y la autoridad GLOBAL se conservan.

1. Recepción crea un preregistro para el anfitrión de ensayo; no tiene controles de
   autorización/cancelación y el API rechaza esas transiciones.
2. El anfitrión consulta y autoriza su propia visita; no registra entrada/salida.
3. Recepción registra entrada y salida; bitácora vinculada al UUID y cuatro eventos.
4. Recargar conserva el cierre. Cada cuenta vuelve desde el inicio a su contexto.
5. Sede o empresa ajenas y membresía revocada son rechazadas. Las nuevas visitas
   terminan cerradas/canceladas y las credenciales permanecen fuera del repositorio.

La creación de cuentas que requiere contraseña corresponde al titular. No se
generan contraseñas, invitaciones ni identidades ficticias para simular una sesión
real. El resultado de sesiones reales debe registrarse por separado de CI.
