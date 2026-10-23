# ADR-AXS-AGENTS-001 — Desarrollo paralelo dentro de AXS

Estado: **aprobado como dirección arquitectónica; implementación A0 experimental**.
Fecha: 2026-10-23.

## Decisión

AXS Agents **pertenece al mismo proyecto AXS y al mismo repositorio**
`B10sp4rt4n/MSP_AXS`. No se crea otro repositorio, otro producto ni
otro proyecto Railway/Neon. Es una **línea de desarrollo paralela** a AXS
Residencial y AXS Corporativo, inicialmente en
`feat/axs-agents-a0-parallel-20261023`, basada en `main`.

El directorio `agents/` tiene código aislado, contrato propio, pruebas y
versiones de snapshots. Podrá empaquetarse o ejecutarse como proceso separado
cuando lo requiera su carga; compartir repositorio **no implica compartir**
proceso, credenciales, base de datos o autoridad. Un servicio adicional dentro
del mismo proyecto de infraestructura requiere evaluación de costos y decisión
posterior. A0 no despliega servicios.

## Componentes y límites

```text
                 REPOSITORIO MSP_AXS
  +--------------------------------------------+
  | AXS Core / AUP_SESSION + AUP_GOV + EVENT    |
  |              autoridad exclusiva           |
  +-----------------------+--------------------+
                          |
            snapshot/evento versionado
            firmado o autenticado en gateway
                          v
  +--------------------------------------------+
  | agents/                                    |
  |  contrato -> observador -> hallazgo         |
  |           -> propuesta de acción           |
  | sin acceso directo a BD ni decisión física |
  +-----------------------+--------------------+
                          |
             propuesta, nunca escritura
                          v
  AXS API de gobierno y operaciones (futura)
          revalida tenant, rol, límites, ARCO,
          evidencia, auditoría e idempotencia.
```

1. **Primero observa** eventos/snapshots versionados y mínimos. Después
   interpreta, correlaciona y recomienda. Solo en otra etapa actuará con
   políticas de AUP_GOV y aprobación según criticidad.
2. **No autoridad implícita.** Un agente NO puede aprobar accesos, registrar
   entradas/salidas, generar QR, cambiar reglas, inventar hechos, crear roles
   ni ampliar su propio alcance. Tampoco puede invocar tablas directamente.
3. **Multi-MSP y multitenant.** `msp_id` y `tenant_id` son parte del
   contexto de cada mensaje. El receptor AXS, no el agente, valida pertenencia
   y permisos actuales; nunca se confía exclusivamente en campos enviados.
   Cada instancia de trabajo tiene un único tenant.
4. **Datos mínimos y ARCO.** Snapshots con referencias opacas en lugar de
   nombres, fotos, documentos, placas, emails o tokens. Retención corta,
   propósito explícito y controles ARCO requeridos antes de admitir PII.
   Ninguna réplica general de las BD CORE/GOV/EVENT.
5. **Conectores reemplazables.** Un adaptador por fuente externa (por ejemplo,
   órdenes de mantenimiento) convierte datos a un contrato versionado; fallas
   externas no detienen AXS Core. No acoplar cada integración a endpoints
   residenciales ni al catálogo corporativo.
6. **Integridad temporal.** El agente conserva `snapshot_id`,
   `schema_version`, timestamp de origen y referencia. Una anomalía se
   describe como observación, nunca como prueba concluyente de que una visita
   ocurrió, terminó o sigue físicamente en sitio.
7. **Idempotencia y auditoría.** Los hallazgos tienen claves deterministas;
   nuevas acciones requerirán `request_id` y recibos en AXS. Duplicados
   de snapshots no deben multiplicar tareas.
8. **Sin consumo nuevo de IA en A0.** Las reglas de observación iniciales
   son deterministas y probables localmente; LLMs, MCP o A2A son opciones
   futuras sujetas a contratos, autorización y presupuesto.

## Estructura propuesta

```text
MSP_AXS/
  backend/                      # operativa AXS vigente, sin cambios por A0
  frontend-next/                # interfaces AXS; sin menú Agents todavía
  agents/
    __init__.py
    contracts.py                # snapshots, hallazgos y contratos
    observers/
      __init__.py
      reconciliation.py         # primer observador puro
  tests/
    test_axs_agents_contract.py # sintéticos, no DB ni servicios externos
  docs/
    ADR_AXS_AGENTS_001.md
```

## Integración progresiva

- **A0 — contratos + observador fuera de línea.** Validar aislamiento, datos
  mínimos, ausencia de escrituras, consistencia de deduplicación. PR draft
  separado, paralelo a #96/#97/#98/#100.
- **A1 — entrega de snapshots por API interna** autenticada con identidad de
  servicio, autorización en AUP_GOV, permiso explícito por tenant y registro
  de consumo. No se habilita automáticamente por instalar código.
- **A2 — propuesta y revisión humana.** Bandeja de hallazgos en el panel AXS;
  escalamiento, plazo y responsable, sin mutar hechos.
- **A3 — resolución acotada.** Sólo tareas indirectas clasificadas de bajo
  riesgo, con recibos de auditoría, evaluación de políticas en el momento de
  actuar, límites y revocación. Acceso físico siempre a cargo de AXS.

## Independencia de las ramas

Agents se implementa sobre `main`, sin añadir commits a los PR corporativos
en borrador ni alterar sus migraciones. La integración con Corporativo llegará
por contrato/eventos cuando sus capacidades estén aprobadas. La integración
con Residencial usa la misma puerta controlada de eventos, sin saltarse
`AUP_SCOPE`. No fusionar ni desplegar A0 automáticamente.
