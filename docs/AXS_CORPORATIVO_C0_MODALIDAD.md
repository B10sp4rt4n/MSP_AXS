# AXS Corporativo — C0: modalidad por tenant y frontera de acceso

**Fecha:** 23 de octubre de 2026. **Estado:** cambios en rama / PR draft, sin migración aplicada en producción.

Contrato de producto: [PR #87](https://github.com/B10sp4rt4n/MSP_AXS/pull/87) (abierto). Auditoría previa: [PR #95](https://github.com/B10sp4rt4n/MSP_AXS/pull/95).

## Decisión de compatibilidad para C0

**Opción A provisional:** se conserva `condominios_exo` como raíz técnica para todas las claves foráneas AUP existentes, pero se añade `modalidad` (`residencial` por defecto / `corporativo`) y `corporativo_habilitado` (false por defecto). No implica que la empresa sea una vivienda: las entidades corporativas nuevas tendrán tablas y rutas propias en C1. El nombre físico legacy solo podrá generalizarse después de una migración probada de las FKs y RLS en todas las bases.

Alternativa B (tabla física universal `tenants`) sigue abierta para revisión si un ensayo PostgreSQL demuestra insuficiencia de A. **No crear un segundo repositorio ni duplicar el motor común.**

## Implementado en esta rama

- Modelos CORE con discriminador y controles de integridad sobre valores.
- Migración SQL aditiva e idempotente de columnas y constraints, preparada pero **no ejecutada**.
- `require_condominio` y `authorized_tenant_context`: exigen `residencial` por defecto, incluso ante un usuario GLOBAL/MSP; el modo `corporativo` requiere `corporativo_habilitado=true`.
- Directorio `GET /condominios/` restringido a modalidad residencial.
- `/arco/{condominio_id}`: usa `expected_mode=None` para no bloquear la obligación transversal de privacidad; conserva permisos AUP y designación propia; **no** habilita ARCO completo en empresa automáticamente.
- Pruebas sintéticas SQLite de denegación, inhabilitación, scope y listados. No demostrar RLS con SQLite.

## No implementado todavía / riesgo conocido

- Alta empresarial, sedes, áreas, anfitriones, su rol y sus autorizaciones.
- Habilitación comercial explícita desde superadmin.
- Rutas de visitas corporativas, QR por sede y su UI.
- **Barrera completa de modalidad en todos los caminos residenciales:** rutas que no pasan por `require_condominio` o por `authorized_tenant_context` aún requieren inventario, remediación y pruebas. No confiar en filtrar solo el portal.
- Pruebas de PostgreSQL desechable con RLS, concurrencia y migración reversibles.
- Validación de todos los usos legacy de `Condominio`, incluidos reportes, servicios y rutas de administración MSP.
- Flujo y ejecución de ARCO con retención/supresión para la nueva modalidad, y política por sede.
- No se añaden viviendas, residentes ni datos corporativos productivos; no hay activación del piloto.

## Orden seguro para validación futura

1. Ejecutar `migrations/20261023_tenant_modalidad_c0.sql` **solo en rama Neon aislada, mediante usuario propietario autorizado**; comprobar columnas, constraints, grants, RLS y que todos los tenants anteriores tengan `residencial,false`.
2. Ejecutar tests SQLite nuevos y el conjunto residencial; además pruebas negativas reales con `axs_core_app` bajo PostgreSQL RLS, incluidas dos empresas y un residencial sin correspondencia entre scopes.
3. Probar lectura y creación residencial con versión previa y versión nueva, validando que el rollback de aplicación no requiere borrar columnas.
4. No agregar clientes corporativos ni desplegar backend con nuevas columnas hasta completar la migración productiva en orden autorizado.
5. C1: endpoint superadmin de habilitación, empresas/sedes/anfitriones con permisos específicos; después ampliar la barrera a **todos** los servicios sin llamar a los métodos residenciales legacy.

## Criterios para terminar C0

- [ ] PostgreSQL desechable con migración y re-ejecución exitosas, datos previos intactos y RLS preservada.
- [ ] Verificados guards de **todos** los endpoints residenciales (HTTP), no solo del helper.
- [ ] Suite residencial completa y pruebas negativas cross-tenant.
- [ ] Identificación/seguimiento del tratamiento de datos y ARCO corporativo.
- [ ] Revisión de seguridad y aceptación explícita de puesta en producción.

No confundir el PR de preparación con una funcionalidad liberada.
