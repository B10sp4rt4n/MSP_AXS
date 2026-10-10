# Reportes de operación V1

Panel Admin → Reportes. Disponible para administradores y MSP con acceso vigente
al condominio seleccionado. La API vuelve a autorizar cada consulta y descarga.
No requiere migración ni modifica eventos o visitas.

## Contrato

`GET /reportes/{condominio_id}/operacion`

- `desde`, `hasta`: fechas inclusivas en America/Mexico_City; máximo 31 días.
- `estado`: estado capturado en el evento, no estado actual de la visita.
- `destino`: etiqueta histórica exacta `casa_unidad`.
- `actor_id`: identificador exacto de quien ejecutó la operación; puede ser un
  guardia, residente o administrador. No se infiere su rol histórico.
- `formato`: `json`, `xlsx` o `pdf` (carta).

Consulta sólo EVENT de visitas/QR del tenant autorizado y fecha de ocurrencia.
Límite explícito de 5,000 eventos; excederlo devuelve 422 y exige reducir periodo
o aplicar filtros. No hay truncamiento silencioso. La pantalla pagina de 25 en 25.
Las descargas repiten la consulta autorizada y registran su propia hora; no son
un snapshot congelado de la consulta previa.

## Definiciones

| Indicador | Evento requerido |
| --- | --- |
| Entrada | Éxito con estado `entrada_registrada`, acción visita crear/registrar o QR validar |
| Salida | Éxito, visita registrar con estado `salida_registrada` |
| Cancelación | Éxito, visita revocar |
| Operaciones rechazadas | Resultado denegado de visita/QR; incluye creación, autorización y acceso |
| Otros eventos | Todo lo restante, incluidos preregistros y generación de QR |

Cada evento pertenece a exactamente una categoría. Generar QR no equivale a
entrar. Una solicitud repetida rechazada sí es un intento distinto. La entrega
idempotente a EVENT no duplica un hecho. Estado, destino o propósito ausentes se
presentan sin dato; un filtro de estado/destino excluye eventos sin ese campo.

La alerta de entrega pendiente abarca todo el condominio, no exclusivamente el
periodo o filtros. Los totales son de hechos recibidos al consultar y pueden
cambiar cuando lleguen eventos atrasados. Cero eventos no demuestra cero actividad.
No se incluyen eventos globales de seguridad que puedan revelar otros tenants.

Los archivos usan una lista explícita de campos, sin tokens QR, hashes de sesión,
documentos de identidad ni cargas de evidencia. Excel almacena texto como texto,
incluido un valor que empiece por `=`, y fechas como celdas de fecha local.
PDF escapa el texto y lleva tipografía embebida y número de página.

## Verificación

`TESTING=1 python -m pytest tests/test_reportes_operacion.py tests/test_turno_bitacora.py -q --no-cov`

Prueba recorrido real con reloj simulado, bandeja pendiente, entrega idempotente,
límites diarios CDMX, filtros, denegación por tenant/rol en los tres formatos,
rangos inválidos, límite sin truncamiento, exportación vacía y texto no ejecutable.

Frontend: `npx next typegen && npx tsc --noEmit`, `npm run test:roles` y
`node tests/reportes-operacion.browser.cjs` con Playwright/Chromium. La prueba de
navegador usa el componente real con transporte sintético y red externa bloqueada;
cubre paginación, historial, descarga, filtros cambiados, error y cambio de tenant.
No equivale a aceptación de un despliegue real.

## Alcance posterior

Quedan para otros hitos: reporte propio del residente, consolidado multitenant
del MSP, permanencia sin salida registrada, agrupaciones por destino/personal y
envíos programados. V1 no infiere presencia física ni incorpora biometría.
