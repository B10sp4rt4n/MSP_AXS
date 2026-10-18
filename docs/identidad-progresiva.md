# Identidad progresiva de AXS

## Decisiones y alcance

`usuarios.usuario_id` sigue siendo la identidad interna estable. Clerk sigue siendo el mecanismo de autenticación existente. El alta, invitaciones, requisitos de acceso y `/auth/me` conservan sus contratos.

| Dato | Propietario | Uso |
|---|---|---|
| Celular E.164, fecha de consentimiento y verificación | Usuario | Contacto privado opcional; no credencial |
| WhatsApp (número E.164), Facebook e Instagram (URL de perfil) | Identidad externa asociada por usuario/proveedor | Referencias declaradas, no acreditación de propiedad |
| Pertenencia y nivel de acceso por condominio | `UserTenantScope` existente | Autorización independiente, validada en cada operación |
| Vivienda y condominio principales | Campos legacy existentes | Compatibilidad; no se multiplican usuarios para añadir scopes |

Una persona puede tener scopes en varios condominios. Este PR no introduce comunidades sociales, invitaciones automáticas ni asignación residencial a varias viviendas: los flujos que dependen de la vivienda principal mantienen ese alcance. La conectividad MVNO/eSIM no interviene en pertenencia ni autenticación.

## API privada

- `GET /auth/me/identity`: datos opcionales del usuario autenticado.
- `PATCH /auth/me/identity`: `{celular: "+525512345678", consent: true}`; `{celular: null}` retira el dato y su consentimiento/verificación.
- `PUT /auth/me/identity/external/{whatsapp|facebook|instagram}`: `{reference: "…", consent: true}`.
- `DELETE /auth/me/identity/external/{provider}`: revoca y borra la referencia; conserva fecha de revocación y consentimiento previo.

Todas las respuestas usan `Cache-Control: no-store`. No se acepta un usuario objetivo ni campos de rol, scope o verificación. El perfil es privado; no se añade a directorios de residentes ni exportaciones. Las escrituras serializan en la fila de usuario, y la restricción usuario/proveedor impide referencias duplicadas por proveedor. PUT y DELETE repetidos mantienen sus fechas si no cambia el estado.

El consentimiento `profile-reference-v1` autoriza exclusivamente guardar el dato en el perfil privado. No autoriza mensajes, campañas, compartirlo con la comunidad ni OAuth. Celular y WhatsApp son independientes, incluso si tienen el mismo número. Cambiar una referencia invalida su verificación; revocarla elimina la referencia. Volver a guardarla exige consentimiento nuevo. No se guardan tokens.

Las referencias declaradas no son únicas entre usuarios: sin prueba de propiedad, una declaración no debe permitir reservar o secuestrar la cuenta de alguien más. No se usan para login, deduplicación, recuperación o concesión de permisos. Los IDs Meta ligados a aplicaciones no se inventan a partir de URLs.

## Verificación y futuras integraciones

Se reservan campos independientes de verificación, pero este PR no contiene un endpoint que la conceda. Todos los nuevos datos quedan sin verificar. Una integración futura necesita revisar documentación y autorizaciones vigentes de cada proveedor, prueba de propiedad, identificadores y ámbito de aplicación, consentimiento por finalidad, revocación y borrado, manejo seguro de secretos y una política de unicidad para identidades verificadas. Esta revisión queda como requisito previo, no como trabajo realizado.

## Migración y reversión

Aplicar `migrations/20261018_progressive_identity.sql` en CORE **antes** de desplegar el backend. Es aditiva, transaccional y repetible: tres columnas opcionales y una tabla nueva. No cambia registros, scopes, roles ni relaciones existentes. Como `usuarios` y `alexa_accounts`, es un modelo de identidad global de control, no una tabla propiedad de un tenant. La API limita acceso al propietario autenticado. El rol `axs_core_app` recibe SELECT/INSERT/UPDATE en la tabla; no DELETE. Las credenciales de base de datos siguen siendo exclusivas del servidor.

Reversión: volver a la versión previa del código y conservar las columnas/tabla; la versión previa las ignora. No ejecutar DROP durante una reversión operativa. No se ha aplicado esta migración a producción.

## Validación

`tests/test_progressive_identity.py` recorre la API con SQLite sintético y el validador real de scopes: alta previa sin datos, aislamiento entre personas, dos comunidades con la misma identidad, rechazo de una tercera y de elevación administrativa, revocación de scope, cambio de cuenta, independencia de verificaciones, consentimiento, revocación, reintentos y rechazo de inyección/URLs inválidas.

Las pruebas sintéticas no acreditan integración real con Meta/WhatsApp ni operación residencial multivivienda. La migración PostgreSQL debe probarse en un entorno aislado antes de producción.
