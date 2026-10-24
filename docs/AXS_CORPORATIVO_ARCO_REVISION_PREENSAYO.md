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
| Panel privado corporativo | `ArcoClient.tsx` carga clientes desde `/condominios/` | Pendiente: ese listado excluye empresas; no afirmar recorrido UI corporativo completo |
| Identidad y representación | Referencias opacas y estado `verificada` | Verificación asistida fuera de AXS; no hay validación automática del titular |
| Responsable y custodia | `owner_id` y referencias del expediente | Son declaraciones del operador; falta acordar responsable, canal seguro y custodio del soporte |
| Plazos | Recepción y vencimientos con zona; historial y versiones | Captura manual; sin calendario legal ni recordatorios/constancias automáticos |
| Decisión y comunicación | Estados secuenciales, resultado y referencias obligatorias | Registro asistido; no demuestra entrega al titular ni ejecución por proveedores |
| Exportación y rectificación | No existe flujo corporativo integral para estas acciones | Pendiente definir categorías, terceros y medio seguro de entrega |
| Oposición, bloqueo y supresión | Casos asistidos; herramientas residenciales/ficticias de conservación separadas | No existe ejecución empresarial general demostrada; registrar cero pendientes no prueba borrado |
| Respaldos y restauración | Interlock general de recuperación y ensayos existentes | Falta acreditar reaplicación de decisiones ARCO por categoría/copia antes de reabrir servicio |
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

1. Incorporar selección corporativa al panel ARCO sin enumeración global ni
   exposición entre empresas; probar cambio de contexto y sesión real de prueba.
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
