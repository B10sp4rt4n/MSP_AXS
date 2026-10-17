# Beta Alexa: alta de residentes con Clerk

Estado: código preparado, desactivado por defecto. Requiere configurar el cliente
OAuth en Clerk y Account Linking/eventos en Amazon, aplicar la migración y
realizar una prueba física antes de invitar vecinos. El piloto existente sigue
funcionando con `AXS_ALEXA_LINKING_ENABLED=false`.

## Experiencia del vecino

1. Acepta la invitación a la beta de AXS Condominios y activa la skill.
2. Vincula su cuenta usando el inicio de sesión de AXS (Clerk).
3. Autoriza notificaciones en la aplicación Alexa.
4. Las entradas y salidas confirmadas en su vivienda generan el aviso «Tienes un mensaje
   de AXS Condominios». Con «Alexa, abre accesos condominio» escucha nombre y
   hora del último movimiento (entrada o salida) de su vivienda en las últimas 24 horas.

Activar la beta no concede por sí solo el permiso de notificaciones. No se
copian IDs ni tokens por vecino. El usuario debe existir en AXS con clerk_id,
rol RESIDENTE, casa_id del catálogo y AUP_SCOPE vigente. Debe haber entrado a
AXS previamente para que su identidad Clerk esté vinculada a su registro.
Un vecino no escoge ni envía el ID de otra vivienda para vincularla.

## Configuración única en Clerk

En la instancia **de producción de AXS**, abrir **OAuth applications** y crear
una aplicación confidencial llamada `AXS Alexa beta`:

- Authorization Code y refresh tokens; habilitar PKCE S256 y consentimiento.
- Scopes `openid offline_access`. No necesita email ni metadatos privados.
- Registrar las **Alexa Redirect URLs** que muestra **Build → Account Linking**
  en la skill existente; copiar las URLs completas de esa consola, sin inventar
  vendorId ni sustituirlas por la URL del backend. Incluir las regiones usadas.
- Conservar Client ID y Client Secret. Es un cliente Clerk nuevo, diferente
  de las credenciales de Alexa Skill Messaging usadas para enviar avisos.

Los metadatos públicos de la instancia fueron comprobados el 2026-10-15 en
`https://clerk.auth.axs-mx.com/.well-known/openid-configuration`: soporta
`authorization_code`, `refresh_token`, `client_secret_basic`, `client_secret_post`,
S256 y los scopes anteriores. No se crea otro proveedor de autenticación.

## Configuración única en Alexa

Usar la skill existente; conservar la invocación **accesos condominio**.
En **Build → Account Linking**:

| Campo | Valor |
| --- | --- |
| Account Linking | Habilitado |
| Permitir activar sin vincular cuenta | Desactivado para este flujo |
| Grant | Auth Code Grant |
| PKCE | Habilitado, S256 |
| Web Authorization URI | `https://clerk.auth.axs-mx.com/oauth/authorize` |
| Access Token URI | `https://clerk.auth.axs-mx.com/oauth/token` |
| Client ID / Secret | Los de la aplicación OAuth de Clerk |
| Client authentication scheme | HTTP Basic |
| Scope | `openid` y `offline_access` |

En permisos mantener `alexa::devices:all:notifications:write`.
Actualizar el manifiesto existente con estas suscripciones, conservando
publicaciones/otros campos existentes (fragmento, no reemplazo del manifiesto):

```json
{
  "events": {
    "endpoint": {
      "uri": "https://web-production-ed4f3.up.railway.app/webhooks/alexa",
      "sslCertificateType": "Wildcard"
    },
    "publications": [{"eventName": "AMAZON.MessageAlert.Activated"}],
    "subscriptions": [
      {"eventName": "SKILL_ACCOUNT_LINKED"},
      {"eventName": "SKILL_DISABLED"},
      {"eventName": "SKILL_PERMISSION_ACCEPTED"},
      {"eventName": "SKILL_PERMISSION_CHANGED"},
      {"eventName": "SKILL_PROACTIVE_SUBSCRIPTION_CHANGED"}
    ]
  }
}
```

Las regiones que ya tengan endpoint explícito deben apuntar al mismo webhook
y usar `sslCertificateType: Wildcard`, como el endpoint de voz ya validado.
El backend también acepta `SkillAccountUnlinked` si Amazon lo envía; Amazon
sólo ofrece ese evento con personalización. No habilitar personalización sólo
para conseguir ese evento. La desactivación, la revocación de permisos y la
baja local funcionan sin él.

## Backend y migración

1. Aplicar `migrations/20261015_alexa_accounts.sql` con el propietario de CORE,
   base `neondb`. Es aditiva; probar primero en una rama de producción.
2. Configurar variables privadas en Railway:

| Variable | Valor |
| --- | --- |
| `CLERK_JWT_ISSUER` | `https://clerk.auth.axs-mx.com` |
| `AXS_ALEXA_CLERK_CLIENT_ID` | Client ID de la aplicación Clerk |
| `AXS_ALEXA_CLERK_CLIENT_SECRET` | Secreto de la aplicación Clerk |
| `AXS_ALEXA_BETA_CONDOMINIOS` | `condo_b6b00ba13ba5` inicialmente (San Luis); lista de IDs separados por coma |
| `AXS_ALEXA_LINKING_ENABLED` | `true` después de completar Clerk y Amazon |
| `AXS_ALEXA_ENABLED` | `true` para avisos de entradas y salidas |
| `AXS_ALEXA_VOICE_ENABLED` | `true` para consulta por voz |

Conservar `AXS_ALEXA_SKILL_ID` y las credenciales existentes
`AXS_ALEXA_CLIENT_ID/SECRET` de envío Amazon. Los secretos de Clerk van en
Railway y en Account Linking, nunca en chat, capturas, frontend o git.
El predeploy comprueba configuración y permisos de la tabla cuando se habilita
la vinculación. Con el flag activado, el vínculo piloto manual deja de usarse:
Salvador también debe vincular su cuenta una vez.

## Seguridad y límites

El webhook verifica firma SHA-256, CA/SAN, skill y tiempo antes de procesar
cualquier evento. Sigue la tolerancia de ASK: voz 150 segundos; sólo los eventos
conocidos, una hora. Se guardan relojes separados de vínculo, baja, permiso y
suscripción; los eventos antiguos y duplicados no revierten una baja posterior.
Una reactivación exige vínculo y consentimientos posteriores a la baja.

`alexa_accounts` es un mapa de identidad del plano de control, deliberadamente
sin RLS porque el consentimiento puede llegar antes de conocer el condominio.
No contiene visitantes ni tokens OAuth. El rol operativo tiene SELECT/INSERT/
UPDATE, sin DELETE/TRUNCATE. Antes de consultar visitas o enviar avisos se
revalida rol, vivienda, lista beta, AUP_SCOPE y contrato de proveedor, y se
establece el tenant para RLS. Las consultas siguen limitadas por vivienda.
La voz verifica el token directamente en la introspección de Clerk, incluyendo
cliente OAuth y scope. No admite email como prueba de identidad.

`GET /alexa/vinculacion` muestra el estado propio sin IDs Amazon.
`DELETE /alexa/vinculacion` da de baja los vínculos del usuario autenticado,
incluso si perdió su scope. Son endpoints AXS protegidos por la sesión normal;
no son rutas públicas. Los cambios de cuentas ya vinculadas se auditan sin
nombres de visitantes ni tokens. Antes del vínculo sólo se conserva el estado
de consentimiento firmado, sin atribuirle un tenant ficticio.

Los avisos mantienen el envío best effort del piloto: un intento en
BackgroundTasks después del commit, sin cola durable ni garantía de entrega.
HTTP 202 significa aceptación de Amazon. Un reinicio puede perder un aviso;
Amazon también puede rechazarlo o limitarlo. No reemplaza el registro en AXS.
No abre el portón ni autoriza visitas. Un envío ya en curso podría terminar
cuando llega una revocación; las siguientes ejecuciones leen el estado nuevo.

El destino Amazon se mantiene en `stages/development` para las pruebas. La
recepción de un vecino debe comprobarse en la beta real antes de ampliar las
invitaciones; no asumir que HTTP 202 certifica entrega. El lanzamiento público
requiere certificación y configurar el endpoint live en un cambio separado.

## Aceptación antes de invitar vecinos

- Aplicar/repetir migración en rama aislada y verificar permisos del rol app.
- Con el flag beta aún apagado, comprobar que sigue funcionando el piloto.
- Habilitar beta y vincular a Salvador desde Alexa sin invocar la skill.
- Conceder notificaciones; comprobar estado propio vinculado/notificaciones.
- Registrar entrada de prueba a Pensamientos 36: comprobar aviso en Echo y
  nombre/hora al abrir mis visitas. Probar manual, QR y alta con entrada.
- Registrar otra casa y un preregistro sin entrada: no debe recibir avisos.
- Probar otro residente con otra casa: cada cuenta recibe sólo su vivienda.
- Revocar notificaciones/desactivar skill/baja local: no enviar nuevos avisos.
- Cambiar la vivienda o revocar scope en AXS: impedir aviso y lectura anterior.
- Mantener lista beta acotada hasta terminar estas pruebas físicas.

Fuentes oficiales:
- https://clerk.com/docs/guides/configure/auth-strategies/oauth/single-sign-on
- https://developer.amazon.com/en-US/docs/alexa/smapi/add-events-to-your-skill-with-smapi.html
- https://developer.amazon.com/en-US/docs/alexa/smapi/proactive-events-api.html
- https://developer.amazon.com/docs/alexaplus/account-linking/configure-authorization-code-grant.html

La ventana de 24 horas usa la hora del movimiento: una salida reciente se incluye aunque la entrada ocurrió días antes. La referencia proactiva distingue entrada y salida; se vuelve a validar la residencia, el scope, el contrato y el consentimiento al enviar. Consultar `docs/alexa-integracion-63-64.md` antes de ampliar la beta.
