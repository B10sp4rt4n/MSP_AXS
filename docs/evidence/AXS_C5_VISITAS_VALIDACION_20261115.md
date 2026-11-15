# AXS C5 — evidencia de validación, 15 de noviembre de 2026

## Identidad y resultado

Repositorio: B10sp4rt4n/MSP_AXS.
PR candidato: https://github.com/B10sp4rt4n/MSP_AXS/pull/115
Código validado: 042eeb09d1390ba225915b71982bb48d1c44d371.
Base: 7ccef8e897d98555c0540aa8b03e0340102bf163 (PR #114).

Los cuatro runs (push y pull_request, Tests y PostgreSQL RLS gate) terminaron con todos sus jobs en success. La validación corresponde al SHA indicado, no constituye aceptación de producción.

## Evidencia CI

| Ejecución | Resultado |
| --- | --- |
| https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43675567715 | Python: 1243 aprobadas, 107 omitidas; cobertura 82%. Frontend roles y navegador aprobados. |
| https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43675567700 | PostgreSQL 16: 157 aprobadas y 12 de migraciones. PostgreSQL 18: 3 catálogo y 11 C5 aprobadas. |
| https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43675572932 | Tests del PR: todos los jobs aprobados. |
| https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43675572936 | Gate PostgreSQL del PR: todos los jobs aprobados. |

El job Python calculó cobertura localmente; la carga opcional a Codecov rechazó la publicación por falta de token. El job y el umbral local terminaron en success. No se presenta esa carga como evidencia publicada.

## Qué se ejecutó

- API: preregistro, autorización, entrada, salida, cancelación previa y bitácora; roles, empresa/sede, revocación, conflictos de UUID y rollback de auditoría.
- Navegador Chromium con transporte e identidad sintéticos: ciclo completo, revisión y confirmación, respuesta perdida con UUID estable, doble envío, permisos de anfitrión, denegación, cambio de empresa, token pendiente al desmontar contexto y sesión cerrada. Incluye validez nativa del folio: rechaza espacios y acepta guion.
- PostgreSQL 16/18 reales y desechables: SQL de migración, login runtime separado sin bypass de RLS, gate de esquema, ciclo HTTP y outbox. Identidad HTTP sintética; no se usó un inicio de sesión real de Clerk.
- Denegaciones SQL: mezcla de empresas, destino/anfitrión ajenos, DELETE/TRUNCATE, edición de referencia, tiempos inválidos, desactivar RLS y escalar a postgres.
- Local: 43 aprobadas, 11 PostgreSQL omitidas por falta de servidor local; generación de tipos Next y TypeScript aprobados. La evidencia de navegador proviene de CI, no de Chromium local.

## Estado de entrega y límites

Implementación candidata en PR #115, sin merge. No se aplicó migración remota, no se desplegó ni se activó C5 en producción. AXS_CORPORATE_VISITS_ENABLED queda desactivada por defecto.

La versión registra una referencia opaca que puede ser dato personal por vinculación. No incorpora nombre/documento del visitante, fotos, QR, biometría, apertura física, vencimiento automático ni aforo. La bitácora consultada es operativa CORE/outbox, no una demostración de custodia inmutable EVENT.

La consulta ARCO exige designación y referencia exacta. Retención, rectificación/eliminación, vigencia e identificación/evidencia deben acordarse antes de un piloto con datos personales reales. Pendiente: ensayo backend/frontend coordinado, migración aislada y autenticación Clerk real, con aceptación de operadores.

Contrato: docs/operacion/AXS_VISITA_CORPORATIVA_C5.md.
