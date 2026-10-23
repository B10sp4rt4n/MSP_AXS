# AXS Corporativo — auditoría de base y primera separación técnica

Fecha: 23 de octubre de 2026  
Estado: **diagnóstico de código y plan técnico**, no implementación ni aprobación de un piloto.

Referencia de producto: [Contrato AXS Corporativo v1.1, PR #87](https://github.com/B10sp4rt4n/MSP_AXS/pull/87). La definición del producto permanece en ese PR abierto, no fusionado a `main`.

## Decisión de arquitectura

- Mantener inicialmente un único repositorio y servicios transversales compartidos: Clerk/identidad, AUP_SCOPE, AUP_GOV, auditoría/cola de eventos, QR, evidencias y ciclo entrada/salida.
- Separar **dominio, API, permisos y experiencia** de corporativo y residencial. No hacer que un anfitrión sea un `RESIDENTE` ni representar áreas empresariales con `Casa`.
- Mantener la modalidad corporativa **deshabilitada por defecto** y controlada en el servidor por tenant. Un rol owner no podrá habilitar modalidad o plan.
- No fusionar cambios corporativos de datos, interfaz o API ni desplegarlos a productivo hasta superar la batería de aislamiento y regresión descrita abajo.

## Hallazgos verificados del código actual

| Archivo | Hallazgo | Implicación |
| --- | --- | --- |
| `backend/db/core/models.py` | `Condominio` corresponde a `condominios_exo` y `UserTenantScope.tenant_id` tiene FK a `condominios_exo.condominio_id`. `Visita`, `Casa`, `Caseta` e `IdentityRetention` referencian al condominio. | La palabra `tenant` aún está modelada sobre una entidad residencial. Crear una empresa independiente sin plan de migración rompería FKs o RLS. |
| `backend/db/core/models.py` | `AccessLevel` enumera `MSP_ADMIN`, `ADMIN_CONDOMINIO`, `GUARDIA`, `RESIDENTE`, `LECTURA`; `Usuario.rol` es global y `Usuario.casa_id` vincula viviendas. | Roles corporativos deben evaluarse por membresía empresarial + sede, no reinterpretar niveles globales sin revisión. |
| `backend/core/scope/msp_boundary.py` | `require_condominio` autoriza por GLOBAL, membresía MSP o scope activo con validación de origen; `require_visita(own_unit=True)` usa vivienda. | Conservar el principio de autorización server-side, pero separar verificadores de modalidad corporativa y de sede. |
| `backend/routers/condominios_router.py` | `POST /condominios/` crea destinos residenciales predefinidos en `casas`. | No reutilizar este endpoint para dar de alta empresas: generaría destinos residenciales ajenos al nuevo dominio. |
| `backend/routers/visitas_router.py` y `backend/services/visita_service.py` | El alta, la búsqueda del destino y el preregistro resuelven `casa_unidad` o `Casa`; las transiciones de entrada y salida son compare-and-set. | Extraer/reutilizar semántica de transiciones, no copiar flujo de vivienda al corporativo. |
| `backend/routers/solicitudes_acceso_router.py` | La autorización remota filtra por `usuario.casa_id` y exige rol `RESIDENTE` al responder. | Crear autorización de anfitrión corporativo específica; no abrir esta ruta a roles nuevos. |
| `backend/routers/qr_router.py` | QR opera sobre `Visita`, `condominio_id`, estado y ventana, y verifica scope antes de consultar el registro. | Reusar mecanismos, pero incluir y revalidar empresa, sede y destino en el contrato corporativo. |
| `frontend-next/src/app/dashboard/DashboardClient.tsx` | Muestra accesos Guardia/Residente/Admin/MSP por `rol` global. | Necesita un acceso corporativo independiente determinado por membresía y modalidad activa, no solo por un rol textual. |
| PR #90 / PR #91 | Expediente ARCO asistido liberado y comprobado exclusivamente para el operador/tenant designados en San Luis. | No equivale a cobertura ARCO operativa de una futura empresa ni a eliminación automática o cumplimiento integral. |

## Ruta de construcción incremental propuesta

### C0 — Frontera de modalidad y tenant (primera entrega técnica)

1. Definir la representación persistente de `tenant_id` común con `tipo = residencial | corporativo`, sin renombrar o migrar en bloque `condominios_exo` en producción. Evaluar dos opciones mediante prueba de migración: (A) extender el registro tenant físico legado con discriminador y perfil empresarial separado, o (B) introducir una tabla base `tenants` y referencias compatibles. No escoger por conveniencia de UI: comprobar FKs, RLS, restauración y reversibilidad.
2. Añadir un guard de modalidad en servidor antes de servir endpoints corporativos o residenciales; corporate off por defecto. Evitar que `/condominios`, `/solicitudes-acceso` residencial, alta Excel y portales residenciales operen sobre una empresa.
3. Pruebas negativas de acceso cruzado entre tenant residencial y corporativo, incluido operador MSP y una identidad vinculada a dos organizaciones. Usar PostgreSQL desechable con RLS: SQLite no es evidencia de aislamiento productivo.
4. Evaluar migraciones **solo en rama aislada de Neon**; no tocar CORE, EVENT ni GOV productivos.

**Criterio de salida:** esquema evolutivo verificable, opción de modelo decidida y documentada, cero nuevos tenants corporativos visibles u operables en producción.

### C1 — Entidades corporativas sin viviendas ficticias

- Empresa (tenant), sede (zona horaria y política de acceso), destino/área, anfitrión, recepción y sus asignaciones explícitas por sede.
- Owner/admin maneja sedes y miembros dentro de capacidades habilitadas por superadmin.
- Endpoint propio de alta empresarial, sin insertar registros en `Casa`.
- Pruebas de denegación entre sedes y por cambio/revocación de membresía; RLS para nuevas tablas y FK compuestas cuando se relacionen tenant/sede/destino.

### C2 — Recorrido de visitas corporativas

- Preregistro de anfitrión, QR vinculado a empresa + sede + destino + ventana.
- Recepción de visitante inesperado y autorización explícita por anfitrión o delegado.
- Entrada y salida confirmadas, reintentos sin duplicados, tablero de estancias abiertas; nunca salida por caducidad del QR.
- Políticas configurables de fotografías de identificación y evidencia opcional de salida, mínimo necesario y conservación definida.

### C3 — Privacidad, aceptación y piloto sintético

- Vincular avisos, responsable del tratamiento, contacto y proceso ARCO a la empresa.
- Ensayar acceso, rectificación, cancelación y oposición; bloqueo, localización de datos, supresión y restauración de respaldos son requisitos por verificar, **no funciones terminadas**.
- Tests completos corporativos y de regresión residencial; piloto inicial sintético de **una empresa y una sede**, con dos tenants para probar el aislamiento.
- No habilitar piloto con datos personales reales hasta comprobar identidad, facultades, retención, ARCO, avisos y protección de evidencias.

## Exclusiones expresas de V1

Asistencia/nómina, biometría, control de torniquetes, apertura remota, proveedores recurrentes, recepción común multicliente, pagos automáticos y mensajería nueva. No desplazar hacia corporativo obligaciones residenciales del piloto de San Luis.

## Decisiones y riesgos para el primer PR de código

1. **Riesgo alto — FK de `tenant_id` dependiente de `condominios_exo`.** Probar una migración aditiva reversible sobre copia; no cambiar el significado de una FK silenciosamente.
2. **Riesgo alto — roles globales/jerarquía.** Reglas corporativas como autorizaciones explícitas tenant+sede+acción; no agregar `ANFITRION` a una jerarquía residencial para heredar privilegios accidentalmente.
3. **Riesgo alto — rutas residenciales legadas.** Controles de modalidad backend en rutas de alta, listados, QR, salida, evidencias y exportaciones; la ocultación del menú no es seguridad.
4. **Riesgo alto — privacidad.** Mantener ARCO atendible durante suspensión/baja y evitar fotos/PII en ledger inmutable.
5. **Riesgo medio — interfaz.** Menús separados; no renombrar `Casa` a `Área` solamente en frontend.
6. **Riesgo medio — solapamiento PR #87.** Este documento audita el código de `main`; no sustituye el contrato ni hace suposiciones de fusión.

## Verificaciones efectivamente realizadas en esta preparación

- Lectura remota de archivos y contrato mediante GitHub.
- Consulta del estado de PR #87 (abierto) y PR #88, #90, #91, #92 y #93 (fusionados).
- **No se ejecutaron** pruebas unitarias, CI, migraciones, despliegues, altas de tenants, envío de correos ni operaciones sobre datos reales.

Siguiente trabajo ejecutable: seleccionar y ensayar el modelo de tenant en PostgreSQL aislado, añadir bloqueo por modalidad y pruebas de rechazo entre tenants, manteniendo la rama en borrador hasta validación.
