# AXS Agents — línea paralela dentro de MSP_AXS

**No es otro proyecto, repositorio ni despliegue.** Este directorio es
parte del repositorio `B10sp4rt4n/MSP_AXS`; su arquitectura y fases se
definen en [ADR](../docs/ADR_AXS_AGENTS_001.md).

A0 implementa un contrato versionado y un observador determinista de
conciliación, totalmente offline. No importa motores SQLAlchemy de AXS,
no abre conexiones, no consume modelos de IA, no se registra automáticamente
en FastAPI y no puede modificar visitas ni conceder accesos.

Ejecutar sus tests sin conectarse a ningún sistema:

```bash
python -m pytest -q tests/test_axs_agents_contract.py
```

## Entrada

`VisitSnapshot(schema_version="1.0", snapshot_id=..., msp_id=...,
tenant_id=..., generated_at=..., records=[...])`: proyección mínima de
estados de visitas y marcas temporales, usando referencias opacas. Se excluyen
nombres, fotos, correos, documentos y tokens. No entregar snapshots a agentes
sin una puerta de autorización y entrega de servicio; A0 no contiene esa puerta.

## Salida

`observe_visit_snapshot(snapshot, as_of=...)` produce hallazgos
inmutables `AgentFinding` con `mode="observe"` y recomendación de revisar
el registro sin modificar el historial. La ausencia de salida no demuestra
que una persona siga físicamente adentro. Los hallazgos no se almacenan en
AXS hasta que AUP_GOV, scope y auditoría validen el canal A1.

## Evolución

A1: adaptador AXS con autenticación, permisos por tenant, eventos/snapshots
versionados, revocación y ARCO. A2: bandeja humana de propuestas. A3:
automatización de tareas indirectas autorizadas. El Core siempre conserva la
decisión final sobre acceso físico.

**Desarrollo:** PR y rama independientes en este mismo repositorio; integrar
solo después de pruebas y revisión. Sin añadir infraestructura de pago.
