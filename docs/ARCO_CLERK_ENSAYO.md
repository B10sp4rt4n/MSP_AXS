# Ensayo ARCO con sesión Clerk real

Se completó el recorrido en AXS Development con una sesión Clerk autenticada manualmente por el titular de la cuenta. La designación temporal se limitó a `axs_demo_condo_a`; el cliente B mostró el rechazo por falta de designación y no expuso formulario ni expedientes.

Folio sintético: `618d485d-06a1-4d52-a278-b169afaf5102`, referencia `ARCO_SIM_003_CLERK`. Se registraron recepción, verificación declarada, resolución procedente simulada, ejecución declarada y cierre. Un intento de cierre con una acción pendiente fue rechazado, conservando el estado ejecutando. Tras declarar cero pendientes y una constancia simulada, el cierre quedó registrado. PostgreSQL confirmó estado cerrada, versión 5, cuatro transiciones y cero pendientes.

El backend probado fue el despliegue `c35e3280-fcef-4371-8c83-afbba1cbc8a9` (SUCCESS), commit `74d0762d3acb9937c25b1bad3973049cb47084e7`; la pantalla correspondió a `a421ef4640b9937c5e4eb22472c22a5778dfc716`. Los cambios entre ambos commits eran documentación y ejecutor del ensayo anterior.

La revisión visual detectó texto claro sobre el fondo blanco heredado. Se añadió un fondo oscuro explícito al contenedor ARCO para mantener contraste con sus textos y controles; esta corrección no cambia permisos ni el flujo probado.

Este ensayo valida sesión y seguimiento asistido con datos ficticios. No acredita verificación de identidad, eliminación de datos, comunicación efectiva al titular ni atención de una solicitud humana. No habilita el módulo en producción comercial. Evidencia estructurada: [resultado](evidence/arco-clerk-20261023.json).
