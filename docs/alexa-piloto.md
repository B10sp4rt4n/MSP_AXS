# Alexa: aviso de entrada para una vivienda piloto

Estado: integración preparada, deshabilitada por defecto. No requiere migración.
La prueba manual de Amazon se validó con HTTP 202 y recepción en Alexa.
La integración automática requiere configuración, despliegue y prueba en sitio.

## Comportamiento

Tras confirmar una entrada en CORE y su auditoría EVENT pendiente, las rutas de
alta con entrada, entrada manual y validación QR programan un aviso en segundo
plano. Se compara condominio_id + casa_id del catálogo + destino_tipo=vivienda.
No se usa el número de casa como identidad. Las visitas previas sin destino_id
no notifican: deben usar un destino del catálogo.

El aviso usa AMAZON.MessageAlert.Activated, igual que la prueba manual:
«Tienes un mensaje de AXS Condominios». No anuncia nombre, placa, casa,
identificación ni motivo de la visita. No autoriza ni solicita autorización.
Un preregistro sin entrada, salida, cancelación o intento rechazado no notifica.

Se envía a una cuenta Alexa (Unicast), no a un Echo individual. Los dispositivos
compatibles de esa cuenta pueden recibir el aviso. El piloto se limita a la
cuenta de prueba; no asumir que seleccionar una casa garantiza la propiedad de
la cuenta: el operador debe comprobarla con el participante antes de habilitar.
La cuenta debe tener la skill de desarrollo habilitada y permiso de notificaciones.

## Configuración del backend

Mantener AXS_ALEXA_ENABLED=false hasta completar las otras variables:

| Variable | Valor |
| --- | --- |
| AXS_ALEXA_CLIENT_ID | Client ID que ya autenticó para esta skill |
| AXS_ALEXA_CLIENT_SECRET | Secreto correspondiente, sólo en variables privadas del backend |
| AXS_ALEXA_PILOT_CONDOMINIO_ID | ID exacto del condominio piloto |
| AXS_ALEXA_PILOT_CASA_ID | casa_id exacto de la vivienda participante |
| AXS_ALEXA_PILOT_USER_ID | userId amzn1.ask.account... que recibió la prueba manual |
| AXS_ALEXA_ENABLED | true al iniciar la prueba controlada |

El catálogo autorizado GET /condominios/{condominio_id}/casas devuelve casa_id.
No pegar secretos ni tokens en chat, frontend, capturas o commits. No se utiliza
el token temporal de PowerShell: el backend obtiene uno al enviar mediante
client_credentials y scope alexa::proactive_events. El endpoint permanece fijo
en stages/development durante este piloto.

## Prueba de aceptación

1. Configurar el vínculo con el participante y desplegar el backend.
2. Registrar una visita real de prueba al destino piloto, desde caseta.
3. Confirmar que AXS conserva la entrada y que Alexa recibe el aviso.
4. Repetir la solicitud de entrada: debe rechazarse sin otro aviso.
5. Registrar otra vivienda y un preregistro sin entrada: ninguno debe avisar.
6. Comprobar entrada por QR y por registro manual.
7. Desactivar AXS_ALEXA_ENABLED=false y verificar que AXS sigue registrando entradas.

Logs: «aviso de entrada aceptado por Amazon» significa HTTP 202, no entrega
confirmada al dispositivo. Confirmar la recepción preguntando a Alexa.

## Límites del piloto

Un solo intento en BackgroundTasks, sin cola durable ni reintento automático.
Un reinicio entre el commit y la ejecución puede perder el aviso. Los fallos de
Amazon se registran sin cuerpos, secretos ni userId y no deshacen el acceso.
El timeout HTTP es de 3 segundos por operación de red; el envío no espera en la
respuesta de acceso. Los reintentos de una entrada ya confirmada no programan
otro envío gracias a la transición atómica existente. referenceId estable por
visita y vivienda, no garantía de entrega exactamente una vez.

No es aún alta autoservicio, account linking ni despliegue comercial. Para
ampliar el piloto hacen falta vínculos verificables por residente, revocación,
cola durable y seguimiento de resultados separado de la auditoría de acceso.

## Consulta por voz: nombre y hora

La segunda fase agrega `POST /webhooks/alexa`. La consulta permanece apagada
hasta configurar `AXS_ALEXA_VOICE_ENABLED=true`, `AXS_ALEXA_SKILL_ID` y
`AXS_ALEXA_PILOT_RESIDENTE_ID`. Reutiliza los IDs de cuenta Alexa, condominio y
casa del piloto de notificaciones. Son controles independientes: apagar la voz
no apaga los avisos, y apagar los avisos no apaga la voz.

El vínculo se configura manualmente sólo para este piloto; no es account
linking autoservicio. Para Pensamientos 36, el operador verifica la identidad
del participante antes de asociar su usuario RESIDENTE en AXS. Se revalida en
cada consulta que pertenezca a esa casa y condominio y conserve scope activo
con contrato vigente. No hay acceso administrativo a otras viviendas por voz.

### Autenticación y límites

Es una sesión externa firmada por Alexa, no una ruta anónima de lectura. El
webhook sustituye el JWT de navegador por verificación de la cadena X.509
contra raíces CA confiables, SAN `echo-api.amazon.com`, firma RSA SHA-256 del
cuerpo original (`Signature-256`), timestamp de máximo 150 segundos y skill ID
esperado. Sólo se descargan certificados de HTTPS s3.amazonaws.com/echo.api/,
sin redirects y con tamaño/timeout acotados. No se acepta un userId sin firma.
Un guardado de auditoría fallido impide entregar el nombre. El bloqueo de
recuperación también cubre el webhook. No se guardan nombres ni userIds de
Amazon en EVENT ni se registran cuerpos de solicitudes.

La lectura informa la última entrada confirmada de las últimas 24 horas,
excluye preregistros y otras viviendas y dice si ya se registró salida. La hora
se expresa en America/Mexico_City. No equivale a detectar presencia física.
El nombre se devuelve como PlainText; no se interpreta como SSML. No incluye
placas ni identificaciones. Cualquiera con acceso al Echo de esa cuenta podría
escuchar la respuesta al abrir la skill: no autentica a la persona que habla.

### Conectar la skill en desarrollo

Después de desplegar y comprobar el endpoint:

1. En Alexa Developer Console abrir AXS Condominios, Build → Endpoint.
2. Elegir HTTPS y usar
   `https://web-production-ed4f3.up.railway.app/webhooks/alexa`.
3. Sustituir también los endpoints regionales que estén configurados (NA es el
   usado por es-MX), o retirarlos para heredar Default. No dejar el antiguo
   Lambda en una región que sobrescriba Default.
4. Seleccionar la opción de certificado emitido por una autoridad confiable
   cuyo dominio coincide con el endpoint. Guardar.
5. Decir «Alexa, abre accesos condominio», el nombre de invocación usado en
   el piloto. LaunchRequest ya consulta; no requiere intents nuevos.
6. Para frases adicionales, crear ConsultarVisitaIntent con ejemplos como
   «quién llegó», «mi última visita» y «quién entró», y construir el modelo.

Cambiar el endpoint implica que el editor Alexa-hosted deja de atender esas
peticiones; el código de consulta se mantiene ahora en el backend AXS. No
reemplazar todo el manifiesto con el ZIP antiguo: conservar permisos y eventos
de notificación ya configurados. Los eventos asíncronos de la skill no están
habilitados para gestión de vínculos en esta fase.

### Aceptación y reversión

Probar desde un Echo real: nombre correcto, hora local y última visita de la
vivienda. Probar también sin entradas recientes, visita ya salida, cuenta sin
vínculo y scope revocado. `AMAZON.HelpIntent`, Stop y Cancel no leen datos.
La autenticación se probó con una CA y firmas reales sintéticas; la recepción
de una solicitud firmada real de Amazon requiere la prueba tras conectar el
endpoint. No afirmar funcionamiento de voz en producción antes de esa prueba.

Para detener lectura: `AXS_ALEXA_VOICE_ENABLED=false` y desplegar. Para volver a
la atención anterior, restaurar el endpoint Alexa-hosted en la consola. Los
avisos de entrada usan su propia bandera `AXS_ALEXA_ENABLED`.
