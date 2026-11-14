# AXS — paquete de liberación controlada, 14 de noviembre de 2026

**Estado: candidato consolidado, conexiones y gates CORE comprobados, snapshot
restaurado en aislamiento. La publicación sigue pendiente por los privilegios
EVENT/GOV y la configuración JWKS.** No se publicaron aplicaciones ni se
modificaron datos, permisos o configuración productivos. En Neon se crearon
el snapshot y una copia temporal de verificación. La integración Git de Vercel genera previews del PR;
GitHub reportó uno completado sobre `6adb936`, sin acreditar el alias productivo.
Después de autorizar el equipo de Vercel, se confirmó directamente el alias
productivo y el preview de la rama. La evidencia actual y el antecedente 403
se conservan en `evidencia-plataformas.json`.

La rama `release/axs-integrado-20261114` contiene el código y las pruebas de
`bc04dcc4934a76e62cdc355943d16674cd8ab3b7`, descendiente de los candidatos
#109, #110 y #111. Este paquete sólo añade documentación e inventario. La CI
citada corresponde al SHA de código; no se atribuye una nueva ejecución al
commit documental.

## 1. Qué se pretende liberar

| Componente | Referencia anterior | Candidato / efecto |
| --- | --- | --- |
| Backend Railway | `a68d1149242dd0b16cd0e363df3ccda917199423`, confirmado por el deployment y la configuración del servicio | `bc04dcc4934a76e62cdc355943d16674cd8ab3b7`: perfil aislado del ensayo y pruebas. En runtime productivo el provisioner conserva el rol original. |
| Frontend Vercel | `76bc9d619836f0872241741570fb7974e51d2bf6`, confirmado por alias y deployment Production READY | Mismo código candidato: incorpora directorio, consola GLOBAL, conciliación y ajuste de ARCO respecto a esa referencia. |
| Esquema | C0/C1/C2/C4 forman parte de la base del backend publicado | **Cero migraciones nuevas** entre el backend confirmado y el candidato. Verificar estado efectivo, sin repetir C4. |
| Activación corporativa | Valores actuales de flags no visibles por OAuth | La publicación propuesta mantiene API y aprovisionamiento desactivados. Habilitar un piloto es una fase posterior. |

El inventario con estados y hashes está en
[`inventario.json`](../releases/axs-integrado-20261114/inventario.json).
No tratar `main@76bc9d6` como si fuera el backend actualmente publicado.

## 2. Evidencia que ya existe

- [Suite del candidato](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43597122166):
  1,217 pruebas Python aprobadas, 73 omitidas, cobertura 82%; controles de roles,
  DOM y TypeScript aprobados; 13 scripts de navegador aprobados.
- [PostgreSQL 16/18](https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43597122129):
  123 pruebas de operación/RLS, 12 de actualización y 3 de catálogo/reversión
  aprobadas. Incluye el ensayo sintético de respaldo/restauración.
- [Regresión residencial simulada](../evidence/AXS_REGRESION_RESIDENCIAL_SIMULADA_20261114.md):
  preregistro, QR, identificación, entrada/salida, foto opcional, reintentos,
  cruce entre condominios y revocación con el mismo JWT.
- [Recorrido remoto GLOBAL y propietario A](https://github.com/B10sp4rt4n/MSP_AXS/blob/aa04b169ab9e454e0aa6fbec9e36dd2080c4eeb0/docs/evidence/AXS_CORPORATIVO_CIERRE_OWNER_INTEGRADO_20261114.md):
  autenticación real, dos empresas, cuotas, sedes/destinos y denegación A→B sobre
  el código `a2b88a3`. El cambio posterior `bc04dcc` sólo añade pruebas/documento.

La simulación no acredita cámara, Blob o sesión Clerk reales del piloto.
El ensayo de restauración CI no es un respaldo productivo.
El [acta de backend y restauración real](../evidence/AXS_BACKEND_Y_RESTAURACION_REAL_20261114.md)
registra la comprobación posterior con conexiones efectivas, snapshot,
restauración, integridad delimitada de eventos y hallazgos de permisos/Clerk.

## 3. Destinos y configuración a comprobar antes del cambio

| Elemento | Destino / valor requerido | Situación de esta preparación |
| --- | --- | --- |
| Railway proyecto | `532a32f5-6313-4ee3-98de-cfcfc225dbb7` | Confirmado por consulta. |
| Entorno / servicio | `72f597ee-89d2-4dd4-9295-6618d3694d22` / `55c12ef5-ba69-449c-ad84-b77ee280eb5b` (`web`) | Servicio live, sin cambios staged al consultar. |
| API pública | `https://web-production-ed4f3.up.railway.app` | Dominio confirmado por Railway. |
| Frontend | `https://app.axs-mx.com`, proyecto `frontend-next` (`prj_m4X1hxQCfaYOFWzN50Uu1z6NrE3S`), equipo `salvador-ruiz-esparzas-projects` | Confirmado: alias apunta a `dpl_Dcd9Rw6L9FWn1PQBXRhjS9L2q17t`, Production READY, SHA `76bc9d6`. |
| Fuente nueva | SHA exacto del candidato / commit documental revisado, nunca HEAD móvil | Fijar en la operación autorizada; conservar identificadores de build y deployment. |
| `AXS_CORPORATE_API_ENABLED` | `false` en publicación de código | `false`, confirmado dentro del contenedor productivo. |
| `AXS_CORPORATE_PROVISIONING_ENABLED` | `false` en publicación de código | `false`, confirmado dentro del contenedor productivo. |
| `AXS_CORPORATE_SANDBOX_ONLY` | `false` en producción | `false`, confirmado dentro del contenedor productivo. |
| Perfil y constancia de sandbox | No copiar `integrated-20261114`, run ID, issuer Development ni conexiones `*_sbx_*` a producción | Exclusivos del ensayo. |
| CORE / EVENT / GOV | Host `ep-rough-voice-b5vx4odv-pooler.c-7.us-east-2.aws.neon.tech`; bases `neondb` / `aup_event` / `aup_gov` | Confirmados desde Railway y mapeados a `br-empty-firefly-b5ob1gsg`. CORE usa `axs_core_app`; EVENT/GOV usan `neondb_owner`, con privilegios excesivos por corregir. |
| Clerk | Instancia Production, issuer/JWKS coherentes y misma instancia en web/API | Issuer y dominio del backend Production confirmados; clave pública fijada presente. JWKS todavía apunta a Development: corrección pendiente, sin cambiar la clave fijada. Detalle en el acta. |
| API del frontend | `NEXT_PUBLIC_API_URL` hacia la API productiva, compilada con configuración Production | Variable Production verificada: `https://web-production-ed4f3.up.railway.app`. Falta comprobar el build que se liberará. |
| CORS y registro | `ALLOWED_ORIGINS` incluye el frontend elegido; callback/redirect Clerk coinciden | CORS confirmado: incluye `https://app.axs-mx.com`. Callbacks y sesión real de aceptación pendientes. |
| Fotografías | Conservar configuración vigente de captura/almacenamiento privado y su retención | Nombres de variables presentes; probar carga/lectura autorizadas antes del piloto. |
| Build y arranque API | RAILPACK; `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`; salud `/health` | Configuración remota confirmada. No cambiar builder por el NIXPACKS del archivo histórico `railway.json`. |
| Predeploy API | `python scripts/check_core_rls.py && python -m scripts.check_corporate_schema` | Confirmado en el servicio; ambos deben terminar con código 0. |

Registrar los valores no secretos en un acta de la ventana. No solicitar ni
publicar cadenas de conexión completas, tokens, fotografías o llaves.

El preview `dpl_H6Kagg9e13JJLrfTAUDjMucUSfiT`, SHA `f4b8272` de la rama de
liberación, figura READY con target no productivo. El inventario de Vercel
sitúa las variables de Clerk/API listadas en Production, no en Preview;
un build READY de preview no acredita autenticación funcional ni su promoción
con configuración productiva. No se cambiaron variables ni aliases.

## 4. Esquema y migraciones

El diff contra `a68d114` no modifica `migrations/` ni los modelos de base.
La acción prevista es **verificar**, no volver a aplicar C0→C1→C2→C4.
Ejecutar bajo el runtime CORE efectivo, en un contexto autorizado que ya tenga
las variables del servicio, sin importar `backend.main` para inspeccionar:

```bash
python scripts/check_core_rls.py
python -m scripts.check_corporate_schema
```

El segundo comando debe devolver
`{"gate": "PASS", "schema": "public", "corporate_tables": 6}`.
Si falla alguno, detener la publicación e inspeccionar destino y catálogo.
Una discrepancia no autoriza a ejecutar SQL ni a reparar con `create_all`.

C4 no es repetible: no borrar journal, tabla o índices para volver a correrlo.
No usar bootstrap, certificados o grants de sandbox en producción. Si el
catálogo real exigiera una modificación, preparar otro cambio revisable con
su alcance y respaldo; no incluirlo implícitamente en esta liberación.

## 5. Respaldo y recuperación de datos

**Estado: snapshot PostgreSQL creado y restauración aislada verificada.**
`snap-orange-hill-b5sz65pw` cubre las tres bases y vence el 21 de noviembre a
las 07:40:13 CDMX. La copia `br-fancy-firefly-b5ov421w` aprobó gates CORE,
comparación del catálogo/ACL público y 35 FKs sin huérfanos. De 267 eventos,
202 tienen hash correcto, 65 son históricos no verificables y ninguno de los
verificables presenta discrepancia. Su endpoint de lectura quedó deshabilitado
e idle; la copia vence el 15 de noviembre a las 07:46:24 CDMX.

No incluye binarios Blob ni un dump externo. El punto de datos declarado por
Neon es 14 de noviembre, 07:39:39 CDMX; se debe refrescar antes de una futura
ventana y conciliar escrituras/revocaciones posteriores si se usara la copia.
El siguiente procedimiento conserva las condiciones para esa ventana.
Antes de modificar el servicio:

1. Identificar las conexiones efectivas CORE/EVENT/GOV y el destino privado de
   fotografías. Confirmar el punto de recuperación disponible del proveedor y
   su retención; no asumir que una política histórica sigue vigente.
2. Registrar por base proyecto/rama/base, hora UTC, punto de recuperación o
   identificador de respaldo, responsable y ventana cubierta. Si se usa dump
   lógico, guardar cifrado en destino privado y anotar SHA-256; no adjuntarlo
   al repo ni al PR. El respaldo debe incluir esquema/datos y un registro
   separado de roles, grants, RLS y configuración necesaria para recuperar.
3. Coordinar una ventana consistente para las tres bases: suspender escrituras
   y despachador de outbox sólo dentro de una operación expresamente acordada,
   o utilizar una estrategia de recuperación consistente acreditada. Registrar
   pendientes/ACK y el orden temporal; tres copias tomadas en momentos distintos
   no equivalen por sí solas a una instantánea común.
4. Restaurar una copia en un destino aislado, sin workers, notificaciones ni
   integraciones activas. Verificar integridad de eventos, relaciones, conteos,
   permisos/RLS y revocaciones. Mantener las autorizaciones restauradas en
   cuarentena hasta conciliar cambios posteriores al punto de recuperación.
5. Verificar por separado referencias y disponibilidad de objetos privados:
   un respaldo PostgreSQL no incluye los binarios de Blob. No ampliar retención
   de identificaciones ni recuperar fotos ya eliminadas por política.
6. Registrar resultado, tiempos reales y ubicación privada del acta. RPO/RTO
   productivos quedan por medir; el resultado de CI no los establece.

Para este cambio de aplicación se conserva el esquema y las escrituras. Una
restauración global de datos queda fuera de la reversión ordinaria y necesita
evaluar pérdida de movimientos, evidencias y revocaciones posteriores.

## 6. Secuencia de liberación propuesta

1. **Cerrar preparación:** resolver los privilegios EVENT/GOV y alinear JWKS
   mediante un cambio separado y ensayado; refrescar conexiones, flags y
   respaldo para la ventana; fijar baseline web/API y candidato. Comprobar
   de nuevo que no hay cambios staged ni otra operación en curso. Revisar
   disparadores automáticos de ambas plataformas antes de modificar una rama.
2. **Revisar el cambio concreto:** SHA, servicio/proyecto, configuración,
   ventana y reversión. La aprobación de este paquete de preparación no es
   una aprobación de publicar ni de activar empresas.
3. **Comprobar esquema y permisos:** ejecutar ambos gates bajo el runtime. No
   aplicar migraciones dentro del deploy de esta propuesta.
4. **Backend primero:** publicar el SHA fijado en el servicio existente,
   conservando conexiones, predeploy, builder y flags corporativos desactivados.
   Esperar `SUCCESS`, gates aprobados y `/health` 200. Si falla, detener avance.
5. **Regresión residencial de aceptación:** cuenta autorizada y visitante de
   prueba identificable; verificar vivienda propia, preregistro/QR, entrada,
   salida y evidencia opcional. Corroborar que permisos ajenos se rechazan y
   que no aparecen movimientos duplicados. Registrar y retirar los datos de
   prueba según la política aplicable, conservando la auditoría.
6. **Frontend después:** construir el mismo candidato para Production sin
   mover inicialmente el alias; comprobar Clerk/API/CORS en el build preparado.
   Un preview de sandbox no acredita las variables del build productivo.
   Tras aceptación, promover ese build y confirmar alias y estado `READY`.
7. **Observación:** comprobar errores de autenticación/HTTP, outbox y fotografía
   privada durante la ventana acordada. Registrar horas UTC, SHAs, deployments,
   checks y decisión de mantener o revertir. No inventar un periodo cumplido.

### Apertura posterior del piloto corporativo

Requiere aceptación real de Clerk, cámara y Blob y definir empresa/propietario
piloto, responsable y aviso de privacidad. El provisioner exige una credencial
segregada backend-only (`DATABASE_CORPORATE_PROVISIONING_URL`), rol de mínimos
privilegios, autoridad GLOBAL y límites confirmados. Esa variable no apareció
en el inventario actual del servicio: no asumir aprovisionamiento listo.

La activación debe ser específica: API/provisión, alta por GLOBAL, cuota
confirmada CORE/GOV, membresía del owner y habilitación del directorio de esa
empresa. No convertir ni habilitar todos los condominios residenciales.
El alcance corporativo de este candidato es alta, cuotas, directorio y permisos;
las rutas residenciales de visitas permanecen bloqueadas para tenants
corporativos. Este paquete no acredita operación de visitas corporativas.
Probar propietario B→A y revocación con sesión real antes de cerrar aceptación;
los resultados sintéticos de esos casos quedan claramente separados.

## 7. Reversión de aplicación

| Componente | Objetivo anterior | Condición |
| --- | --- | --- |
| Frontend | Deployment `dpl_Dcd9Rw6L9FWn1PQBXRhjS9L2q17t`, SHA `76bc9d6` | Confirmado Production READY y asociado a `app.axs-mx.com`; objetivo anterior de reversión fijado. Refrescar disponibilidad antes del cambio; no se ejecutó ni ensayó una reversión remota. |
| Backend | Deployment `be9b87a6-8a58-4341-a181-b4fc70ebd808`, SHA `a68d1149242dd0b16cd0e363df3ccda917199423` | Railway lo reportó SUCCESS, redeploy/rollback disponibles al preparar. Reconfirmar disponibilidad en la ventana. |
| Datos y esquema | Conservar tablas, columnas, journal, evidencias y escrituras | Sin DROP, downgrade SQL ni restauración global automática. |

Revertir si los gates fallan, el backend no alcanza SUCCESS/salud, la
autenticación o el recorrido residencial fallan, se observa acceso cruzado o
se pierde integridad de movimientos/evidencias. Ante una incidencia, impedir
la apertura de nuevas operaciones corporativas mediante los controles
revisados, preservar evidencia y decidir según el componente afectado.

Si ambos componentes cambiaron: volver primero al frontend previo y luego al
backend `a68d114`, conservando la configuración productiva capturada. Confirmar
`READY`/`SUCCESS`, alias, salud y recorrido residencial después de revertir.
No usar como rollback productivo los deployments o certificados del sandbox.
Si una reversión Vercel desactiva asignaciones automáticas, dejar registrado
ese estado y revisar explícitamente la siguiente promoción.

## 8. Condiciones aún pendientes

| Condición | Estado |
| --- | --- |
| Código consolidado, CI y diferencias inventariadas | Completado en esta preparación. |
| Baseline, fuente y predeploy API | Confirmados por Railway; refrescar al ejecutar. |
| Baseline y objetivo de reversión de frontend | Confirmados por Vercel tras autorización del equipo; sin mover el alias. |
| API y Clerk públicos de frontend | Confirmados en variables Production; build de liberación y autenticación real pendientes. |
| Conexiones, flags, issuer y CORS del backend | Confirmados dentro del contenedor; EVENT/GOV usan el propietario y JWKS apunta a Development. |
| Gates sobre CORE efectivo y copia restaurada | RLS y esquema PASS en ambos; refrescar al ejecutar la ventana. |
| Respaldo PostgreSQL y restauración aislada | Snapshot real creado y verificado; vencimientos y límites en el acta. |
| Privilegios EVENT/GOV y JWKS | Corrección pendiente antes de publicar; sin cambios remotos aplicados. |
| Recuperación de objetos privados / copia externa | Pendiente; snapshot PostgreSQL no respalda los binarios Blob. |
| Aceptación real de Clerk/cámara/Blob y cruces/revocación de sesión | Pendiente antes de abrir el piloto. |
| Publicación y activación | No ejecutadas; requieren revisar el cambio concreto anterior. |
