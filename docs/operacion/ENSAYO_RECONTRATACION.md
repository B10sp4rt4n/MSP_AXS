# Ensayo sintético: dos ciclos del mismo proveedor

Revisado y ejecutado el 9 de octubre de 2026. Base actual:
`bc35bfd` (PR #38); base histórica: `60dd0a5` (PR #37).

La corrección mínima ya fue integrada en #38: UUID inmutable por contrato,
versión por condominio, procedencia de cada permiso ligada al UUID, cierre
idempotente por contrato y comprobantes persistentes independientes del outbox.
No se duplica esa implementación. Este cambio refuerza su regresión funcional.

## Resultado ejecutado

- En #37, baja legacy → revinculación sintética directa al mismo MSP → segunda
  baja produce 409 `Relación reutilizada`. Sólo existe un evento de baja y los
  permisos revocados siguen revocados. La revinculación directa únicamente
  reproduce el defecto en la base temporal; no es un procedimiento operativo.
- En #38, tras cerrar la relación legacy de preparación, se abren y cierran dos
  contratos versionados consecutivos del mismo MSP. Tienen UUID y scopes
  distintos. La misma sesión JWT recibe 403 antes de cada permiso nuevo, 200
  después de otorgarlo y 403 después de cada cierre.
- Reactivar artificialmente el scope del contrato 1 durante el contrato 2 no
  autoriza al guardia. Reintentar el cierre 1 después de otorgar el permiso 2
  conserva el acceso del contrato 2. Repetir el cierre 2 conserva su comprobante.
- Ambos scopes conservan contrato, revocación y fecha; cada cierre tiene un
  evento único y un comprobante propio. Se conservan visita, evidencia, permisos
  de residente/administrador local y acceso del guardia al otro condominio.

## Reproducción local

Con las dependencias de `requirements.txt` instaladas, desde la raíz:

```bash
env -u AXS_TEST_POSTGRES_URL TESTING=1 \
  DATABASE_CORE_URL=sqlite:// DATABASE_EVENT_URL=sqlite:// DATABASE_GOV_URL=sqlite:// \
  python -m pytest --no-cov -q tests/test_provider_legacy_rehire.py \
    tests/test_provider_contracts.py tests/test_provider_offboarding.py
```

Resultado local: **8 aprobadas, 4 omitidas** (bloqueos/concurrencia PostgreSQL).
Las fixtures sustituyen CORE, GOV y EVENT por bases efímeras. No se usan Clerk,
Railway, proveedores reales ni conexiones productivas.

Para reproducir el comportamiento histórico, crear un worktree separado en
`60dd0a520d2cb03201253068c0893d0668e1a67b`, copiar únicamente
`tests/test_provider_legacy_rehire.py` desde esta rama a ese worktree y ejecutar
el mismo comando con sólo ese archivo. Resultado ejecutado: **1 aprobada**.

El workflow PostgreSQL existente ya ejecuta `test_provider_contracts.py`,
incluyendo la regresión ampliada. Los resultados locales anteriores no acreditan
concurrencia PostgreSQL, migración SQL ni despliegue. No se aplicaron migraciones,
no se alteraron relaciones reales y no se desplegó producción en este ensayo.
