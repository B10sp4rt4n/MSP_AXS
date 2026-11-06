# AX-S — Plan de producto multi-MSP y preparación MVNO

**Estado:** propuesta de trabajo para revisión, sin cambios funcionales  
**Fecha:** 2026-09-29  
**Base revisada:** `main` en `997454ca65a7f5997240b0fe4b5c356d382fab87`  
**Objetivo comercial:** ofrecer AX-S a proveedores de seguridad que administran varios condominios.  
**Supuesto MVNO:** operador móvil virtual que suministra conectividad SIM/eSIM a interfonos, controladores y equipos de campo. Confirmar este alcance antes de diseñar la integración.

## 1. Contrato de producto

Jerarquía operativa:

```text
Operador AX-S
  └─ Proveedor de seguridad (MSP)
       └─ Condominio
            ├─ Unidades y residentes
            ├─ Guardias y administradores
            ├─ Casetas, puertas y dispositivos
            └─ Visitas, pases, aperturas y eventos
```

El operador AX-S gobierna la plataforma. El administrador de un MSP gestiona únicamente sus condominios. El administrador de un condominio gestiona solo ese condominio. Un guardia actúa únicamente en sus casetas asignadas. Un residente autoriza visitas de sus unidades. Una persona puede tener varias membresías explícitas, revocables y con vigencia. El rol global no concede acceso implícito a otro MSP.

### Flujos base acordados

| Flujo | Secuencia | Resultado auditable |
|---|---|---|
| Visita prevista | Residente autoriza visitante, puerta y ventana horaria; AX-S emite pase temporal QR o PIN; residente comparte por WhatsApp; visitante presenta pase en la entrada; AX-S valida y solicita apertura. | Pase autorizado/denegado, consumo, orden al controlador y confirmación física por separado. |
| Visita imprevista | Visitante llama desde interfón; residente identifica y autoriza esa solicitud y puerta; AX-S solicita apertura. | Llamada, decisión y confirmación del dispositivo. |
| Entrega | Residente emite PIN individual de un uso; repartidor lo ingresa en interfón; AX-S valida y solicita apertura. | Intentos, consumo único y confirmación del dispositivo. |
| Residente habitual | Residente presenta credencial configurada; AX-S verifica membresía, puerta, horario y política; solicita apertura. | Decisión y confirmación del dispositivo. |

El interfón no es paso obligatorio de la visita prevista. El QR de visita actual escaneado por guardia puede mantenerse durante la transición; el hardware automático se incorpora por adaptador.

**Plus:** solo para acciones o puertas privilegiadas de residentes. Exige una passkey con verificación local antes de la orden de apertura. No aplica a visitantes. La passkey prueba verificación local del dispositivo; no certifica reconocimiento facial específico.

### Invariantes del acceso

- Cada decisión tiene `msp_id`, `condominio_id`, `puerta_id`, actor, política, vigencia y resultado. No se infiere el alcance por rol, correo ni URL.
- `autorizado`, `orden_enviada`, `apertura_confirmada` y `fallo_de_dispositivo` son estados diferentes. Un HTTP 200 de la API no equivale a puerta abierta.
- Un pase de un uso se consume atómicamente. La revocación y expiración se comprueban al usarlo, no solo al generarlo. Reingreso exige política explícita.
- QR/PIN son credenciales opacas de alta entropía; se almacenan como huella cuando corresponda, no se registran en URL, logs ni eventos. PIN corto requiere límite de intentos por pase y dispositivo.
- Las acciones relevantes y las denegaciones dejan eventos con referencias, sin secretos ni datos personales innecesarios. Un fallo al registrar evidencia operacional debe quedar visible y recuperable.
- La caída de red o del controlador nunca se interpreta como confirmación de apertura. El procedimiento local de emergencia es responsabilidad operativa definida para cada instalación.

## 2. Estado comprobado en código

| Hallazgo | Evidencia | Implicación |
|---|---|---|
| Existen MSP, condominio, casa, caseta, visita y scope por tenant | `backend/db/core/models.py` | Base de dominio reutilizable. |
| `MSP_ADMIN` lista todos los MSP y condominios | `backend/routers/msp_router.py`, `backend/routers/condominios_router.py` | Falta frontera por proveedor. |
| Rutas de casas, preregistro, QR y evidencias aún autorizan por `usuario.rol` o `verificar_rol` | `backend/routers/` | El alcance no se aplica uniformemente. |
| `set_tenant_context` captura errores de `SET app.tenant_id` y continúa | `backend/core/tenant/context.py` | No se puede declarar aislamiento RLS efectivo sin prueba en PostgreSQL y rol de app. |
| Smoke de tenant usa SQLite y salta la comprobación de `current_setting` | `tests/smoke/test_tenant_isolation.py` | CI verde no prueba RLS productivo. |
| QR es `AXS|visita_id|token`, token truncado, vigencia en Visita | `backend/services/qr_service.py`, `backend/db/core/models.py` | Falta entidad de pase, puerta, revocación y consumo seguro. |
| `GET /qr/validar` registra entrada; el guardia escanea en web | `backend/routers/qr_router.py`, `frontend-next/src/app/dashboard/guardia/validar/ValidarQRClient.tsx` | Validar pase y abrir puerta requieren contrato nuevo con POST e idempotencia. |
| `reenviar_qr` genera imagen nueva aunque puede conservar token anterior | `backend/routers/preregistro_router.py` | Riesgo de mostrar QR que no corresponda al token persistido. |
| CORE, EVENT y GOV tienen sesiones separadas | `backend/db/core/`, `backend/db/event/`, `backend/db/gov/` | Diseñar reconciliación ante commit parcial y acciones físicas. |
| Conviven `frontend-next`, `frontend`, `backend/static` y SQL históricos | Árbol de `main` | Fijar implementación canónica y migraciones antes de extender. |
| El workflow de tests del commit base pasó | `.github/workflows/tests.yml` | Evidencia de CI, no de multi-MSP ni hardware extremo a extremo. |

Los documentos `docs/ROADMAP_PRODUCTO.md` y `docs/FASE5_SECURITY_POSTURE.md` expresan objetivos y garantías históricas; sus afirmaciones deben cotejarse con esquema, rol de base, despliegue y pruebas actuales. No asumir que un SQL histórico representa la base en operación.

## 3. Arquitectura objetivo

**Identidad y alcance.** Membresías `UsuarioMSP`, `UsuarioCondominio` y asignación a unidad/caseta; una identidad puede operar varios ámbitos explícitos. Separar `AXS_PLATFORM_ADMIN` de `MSP_ADMIN`. Evaluar autorización por acción y recurso antes de consultar o modificar datos. RLS en PostgreSQL es segunda barrera, con contexto ligado a la transacción y rol sin bypass.

**Dominio de acceso.** `Visita` describe la visita; `PaseAcceso` describe la credencial emitida y sus usos; `Puerta` y `Dispositivo` describen el punto físico; `IntentoAcceso` registra decisión, orden y acuse. Las casetas agrupan puertas. Los adaptadores de hardware implementan un contrato común de orden, acuse, estado y reintento idempotente.

**Mensajería.** AX-S crea la invitación; un adaptador entrega enlace o código por el canal configurado. La entrega fallida no convierte el pase en usado. El envío manual por WhatsApp desde la pantalla actual puede sostener el primer piloto.

**Eventos y operación.** AUP_EVENT registra hitos verificables. Un identificador de correlación une invitación, pase, decisión, orden y acuse. Un outbox o mecanismo equivalente permite reintentar notificación/orden sin duplicar aperturas. Paneles muestran estados pendientes, dispositivos fuera de línea y conciliación.

**Conectividad MVNO.** Módulo separado `ConectividadDispositivo`: proveedor, identificadores de SIM/eSIM protegidos, plan, estado, consumo, última señal, costo y vínculo a dispositivo/condominio/MSP. Un adaptador lee o solicita cambios al proveedor de conectividad. Ethernet/Wi-Fi/celular pueden coexistir. La identidad del dispositivo y la autorización de puerta no dependen de poseer una SIM.

## 4. Fases y gates

| Fase | Entregable | Gate observable |
|---|---|---|
| **0 — Contrato y mapa** | Flujos, estados, esquema real, inventario de rutas y frontend canónico. | Matriz ruta → actor → MSP → condominio → recurso → evento; ninguna ambigüedad sobre apertura confirmada. |
| **1 — Aislamiento multi-MSP** | Membresías MSP, separación admin AX-S/MSP, autorización uniforme, migración y RLS transaccional. | Dos MSP × dos condominios: lecturas, escrituras, búsquedas, evidencias y eventos no cruzan fronteras; revocación inmediata; test con PostgreSQL y rol real. |
| **2 — Pases y operación atendida** | QR/PIN con ciclo de vida, revocación, usos, rate limit, POST de validación y pantalla de guardia. | Expiración, reenvío, puerta equivocada, revocación, replay y carreras concurrentes pasan pruebas; piloto atendido con entradas y salidas. |
| **3 — Interfón/controlador** | Registro de equipos, adaptador, llamada, orden, acuse, observabilidad y contingencia. | Una puerta real; fallo de red/controlador visible; orden idempotente; operación manual documentada. |
| **4 — Producto para proveedores** | Alta autoservicio asistida, personal, condominios, políticas, reportes, soporte, branding y medición de uso. | Un MSP incorpora y opera un condominio sin cambios de código; otro MSP no ve sus datos. |
| **5 — Preparación MVNO** | Inventario y adaptador de conectividad; piloto con un proveedor y un equipo celular. | Caída y recuperación visibles, costo/consumo por MSP/condominio; cambio de operador sin alterar permisos de acceso. |
| **6 — Plus** | Passkey para residentes y políticas de acceso privilegiado. | Autenticación reforzada solo donde la política lo exige; revocación y recuperación probadas. |

No fijar fechas ni porcentajes hasta verificar esquema desplegado, hardware disponible, proveedor de mensajería y alcance MVNO. La prioridad comercial es cerrar fases 0–3 en un piloto de un MSP y un condominio antes de replicar.

## 5. Primer paso para retomar

**Primer paso ejecutable: Fase 0 — contrato y mapa de aislamiento.** Abrir un PR separado, exclusivamente de diagnóstico y contrato, con:

1. Inventario de endpoints de `backend/routers`, método, actor, recurso, origen de `msp_id`/`condominio_id`, dependencia de scope y evento.
2. Inventario de tablas y migraciones realmente usadas en el ambiente de prueba. Comparar modelos CORE/EVENT/GOV con SQL histórico; no modificar producción.
3. Diagrama de flujo para los cuatro casos base con estados de decisión, orden y acuse.
4. Matriz de autorización para operador AX-S, administrador MSP, administrador condominio, guardia, residente, visitante y dispositivo.
5. Escenarios negativos y positivos con dos MSP y dos condominios, ejecutables luego en PostgreSQL bajo el rol de aplicación.

**Cierre de fase 0:** el PR identifica cada ruta que puede cruzar MSP o condominio, define la migración a efectuar en fase 1 y fija una prueba de aceptación reproducible. No habilitar control automático de puertas con las rutas de QR actuales.

**Siguiente PR, fase 1:** implementar la frontera MSP y el gate PostgreSQL/RLS a partir de ese inventario. Mantener las mutaciones de base productiva y la integración física fuera del PR documental.
