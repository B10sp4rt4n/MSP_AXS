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
