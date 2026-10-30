# AXS Corporativo: revisión técnica ARCO antes del ensayo integral

Fecha de revisión: 23 de octubre de 2026. Alcance: código de C1–C3 y pruebas
sintéticas. No es dictamen legal ni declaración de cumplimiento integral.
No autoriza datos personales reales, migraciones, grants o despliegues.

## Resultado de la revisión

La base C0 validada (`2267ee1268ae96dd301e1e5379e94407bc216d80`) se integra
en orden C1 → C2 → C3. Incluye 424 rechazos HTTP residenciales y su réplica en
PostgreSQL, protección de avisos Alexa en cola y excepción de privacidad.
Los resultados de cada rama actualizada deben verificarse sobre su propio SHA.

Se identificó una incompatibilidad real entre el expediente ARCO legado y el
modelo empresarial: el owner corporativo designado necesitaba un scope
residencial para entrar; a su vez, un scope residencial sobre una empresa podía
ser aceptado sin membresía corporativa. Tres pruebas de owner/admin fallaron
antes de corregirlo. No se otorgaron scopes residenciales como solución.

`backend/core/scope/arco_boundary.py` separa ahora las dos modalidades:

- Residencial conserva nivel administrativo efectivo, procedencia del grant,
  rol administrativo y designación expresa.
- Empresa exige membresía corporativa activa owner/admin y designación
  `usuario_id:tenant_id`, sin heredar permisos de `Usuario.rol` ni de un scope
  residencial. Host/recepción y administrador MSP sin GLOBAL son rechazados.
- GLOBAL conserva acceso transversal únicamente con rol administrativo y
  designación expresa; GLOBAL por sí solo no abre expedientes.
- La disponibilidad ARCO es independiente de `corporativo_habilitado` y del
  flag comercial del directorio. El flag ARCO propio sigue requerido.
- Revocar la membresía o la designación bloquea la siguiente petición,
  incluso con el mismo JWT. La consulta bajo RLS no sustituye autorización.

No se introducen nuevas migraciones ni permisos de base. El runtime que llegue
a operar ARCO necesitará los permisos ya definidos y revisados para sus tablas;
el sandbox real permanece cerrado hasta una autorización específica.

## Matriz de preparación observada

| Capacidad | Evidencia en código | Estado para el ensayo |
| --- | --- | --- |
| Canal público | `/privacidad/arco`, enlaces públicos y contacto asistido | Existe guía general; no es recepción automática ni aviso empresarial específico |
| Aviso por empresa | C2 exige contacto, URL HTTPS y versión; C3 los captura | Metadatos mínimos; no verifica contenido, responsable ni correspondencia por tratamiento/sede |
| Acceso al expediente | Guard ARCO por modalidad, designación y membresía vigente | Corrección preparada en rama, con pruebas HTTP y gate PostgreSQL |
| Empresa deshabilitada | Expediente independiente de habilitación comercial | Alta, consulta y avance probados sintéticamente; revocación de facultades sigue aplicando |
| Panel privado corporativo | `ArcoClient.tsx` consulta `GET /arco-clientes` | Selección por designación y facultades ARCO vigentes, residencial/empresa; pruebas de cambio de cliente/sesión y revocación |
| Identidad y representación | Referencias opacas y estado `verificada` | Verificación asistida fuera de AXS; no hay validación automática del titular |
| Responsable y custodia | `owner_id` y referencias del expediente | Son declaraciones del operador; falta acordar responsable, canal seguro y custodio del soporte |
| Plazos | Recepción y vencimientos con zona; historial y versiones | Captura manual; sin calendario legal ni recordatorios/constancias automáticos |
| Decisión y comunicación | Estados secuenciales, resultado y referencias obligatorias | Registro asistido; no demuestra entrega al titular ni ejecución por proveedores |
| Exportación y rectificación | No existe flujo corporativo integral para estas acciones | Pendiente definir categorías, terceros y medio seguro de entrega |
| Oposición, bloqueo y supresión | Casos asistidos; herramientas residenciales/ficticias de conservación separadas | No existe ejecución empresarial general demostrada; registrar cero pendientes no prueba borrado |
| Respaldos y restauración | Cuarentena ampliada a membresías corporativas/asignaciones; liberación residencial exige constancia de revisión de privacidad | Reaplicación de decisiones por categoría/copia sigue asistida; la constancia no demuestra por sí sola supresión ni reconstruye decisiones perdidas |
| Datos de visitantes corporativos | Rutas residenciales denegadas y directorio separado | Fuera de alcance; QR, evidencias, voz y accesos físicos no se habilitan por el directorio |
| Conciliación CORE/GOV | C3 ya contiene journal/protocolo C4 en su head de partida `2b397b4` | Código versionado; SQL/permisos no aplicados al sandbox; no equivale a operación real |

La información general de la guía no reemplaza la revisión jurídica y operativa
del responsable. Este documento no actualiza ni interpreta plazos legales.

## Ensayo permitido y salida pendiente

Con CI aprobada se puede preparar un recorrido con identidades y empresa
totalmente sintéticas: alta empresarial, owner, cuotas, directorio y expediente
ARCO por API. Su ejecución en infraestructura externa depende además de
credenciales mínimas, políticas/grants revisados y configuración aislada.
Este cambio no configura ni despliega esa infraestructura.

Antes de declarar un piloto con personas reales listo se requiere:

1. Completar el ensayo del selector privado ya preparado con una sesión real de
   prueba en el entorno autorizado. React/Chromium y API/PostgreSQL usan identidad
   y transportes sintéticos; no acreditan por sí solos Clerk real.
2. Acordar responsable, aviso por tratamiento, custodio y canales de recepción,
   verificación, entrega y constancia, independientes de suspensión comercial.
3. Verificar cada acción ARCO sobre categorías y proveedores, conservación,
   objetos/copias/exportaciones y restauración. Documentar lo asistido y lo
   automático sin atribuir al registro de estados una ejecución que no realiza.
4. Validar CI por SHA, permisos mínimos efectivos y recuperación CORE/GOV en
   entorno autorizado; aprobar aparte cualquier SQL, credencial o despliegue.

## Pruebas reproducibles

- `tests/test_corporate_arco.py`: owner/admin sin scope residencial, designación,
  membresía revocada, host/recepción, MSP, GLOBAL y empresa deshabilitada.
- `tests/test_arco_cases.py`: ciclo asistido, idempotencia, versiones, fechas,
  alcance residencial y reversión ante falla de auditoría.
- `tests/test_tenant_modalidad_privacy_alexa.py`: separación de operaciones
  residenciales, voz/vinculación y disponibilidad ARCO con membresía explícita.
- `tests/smoke/test_corporate_arco_postgres.py`: HTTP con sesiones nuevas,
  tablas forzadas a RLS, rol sin bypass, falta de contexto, cruce y revocación.
- Matriz C0 y suites de directorio/aprovisionamiento/conciliación se conservan.

Los resultados anteriores de C0 no certifican por sí solos los cambios nuevos.
Mantener PR #97, #98 y #100 en borrador y la secuencia de dependencias.

## Panel y validación de datos/proveedores/respaldos

`GET /arco-clientes` solo considera las designaciones del usuario autenticado y
revalida las facultades de cada cliente antes de devolver ID, nombre y modalidad.
No utiliza listados globales de empresas ni devuelve contactos, membresías o
expedientes. GLOBAL tampoco ve clientes sin designación. ARCO deshabilitado
devuelve 404. La lista sigue disponible para una empresa deshabilitada cuando
el operador conserva su membresía y designación.

El panel distingue Empresa/Condominio. Cambiar cliente, actualizar la lista o
cambiar usuario/sesión retira formularios y expedientes anteriores; las respuestas
tardías no rellenan otro contexto. Se conserva el UUID por intención de recepción.

La revisión de restauración reprodujo tres defectos: permisos corporativos que
seguían activos después de cuarentena, reactivación de membresía no detectada y
liberación residencial capaz de emitir un scope para una empresa. Se corrigieron.
El ensayo de `pg_dump`/`pg_restore` se amplía con membresía/asignación corporativas
para demostrar la resurrección del grant antiguo y su denegación en cuarentena.

| Acción evaluada | Prueba y resultado esperado | Límite vigente |
| --- | --- | --- |
| Registro, consulta y rectificación de estados ARCO | Versiones, alcance, designación y eventos mínimos en `test_arco_cases.py` y `test_corporate_arco.py` | Cambiar un estado no rectifica automáticamente los datos del titular |
| Conservar/bloquear fotos vencidas | `test_identificacion_conservacion.py`: lectura denegada aunque se detenga el worker; excepción finita y reintentos | Piloto de pares ficticios residenciales; no es conservación empresarial general |
| Borrado en proveedor | Pares ficticios: fallo parcial queda pendiente, conserva intención y reintenta; 304/429/5xx no prueban ausencia | Proveedor simulado/SDK bajo mock; no hay borrado real empresarial ni garantía sobre copias ajenas |
| Respaldo y permisos antiguos | `test_restore_drill_postgres.py` y `test_recovery_mode.py`: cuarentena, revocación corporativa, reautorización residencial acotada | No reconstruye resoluciones ARCO ausentes ni borra automáticamente objetos restaurados |
| Apertura posterior a restauración | Sin confirmación/ref. de revisión de privacidad, `release` deniega; se comprueban huella y cuarentena | Confirmación asistida del operador; debe respaldarse con revisión de categorías/proveedores/copias |

No se añadieron rutas empresariales de exportación masiva, rectificación de datos
del titular ni supresión general porque todavía falta especificar categorías y
custodia. No se ejecutaron acciones sobre almacenamiento, datos, permisos o
respaldos productivos. No declarar el piloto con personas reales listo por estas
pruebas sintéticas.
