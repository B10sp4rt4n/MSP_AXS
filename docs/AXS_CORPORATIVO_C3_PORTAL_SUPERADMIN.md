# AXS Corporativo C3 — Consola privada de Superadmin

Fecha: 23 de octubre de 2026. **Estado: desarrollo aislado, sin despliegue ni activación productiva.**

Depende de [C0 #96](https://github.com/B10sp4rt4n/MSP_AXS/pull/96), [C1 #97](https://github.com/B10sp4rt4n/MSP_AXS/pull/97) y [C2 #98](https://github.com/B10sp4rt4n/MSP_AXS/pull/98), aún en borrador. El contrato funcional permanece en [#87](https://github.com/B10sp4rt4n/MSP_AXS/pull/87).

## Entregado en rama

- Pantalla separada `/dashboard/corporativo/plataforma`, sin cambiar los menús/roles residenciales.
- Layout validado en servidor mediante Clerk y `GET /plataforma/corporativo/estado`; **solo una autoridad GLOBAL vigente** obtiene el formulario. Una ruta directa, sin sesión, con error de backend o sin capacidad habilitada falla cerrada.
- En Dashboard MSP, un enlace a la consola se presenta únicamente después de confirmar permiso GLOBAL desde el backend. `MSP_ADMIN` por sí solo no concede acceso.
- Flujo guiado: empresa + proveedor existente + owner existente, contacto y aviso de privacidad; cuotas GOV de sedes/áreas; habilitación separada del directorio.
- Verificación previa del owner mediante consulta privada y confirmación explícita antes de cada operación.
- La interfaz conserva el mismo UUID de alta en reintentos, evita que un timeout genere otra solicitud; no guarda tokens, avisos ni contactos en almacenamiento local. Identificador corporativo visible para recuperar el proceso.
- Tras escribir cuotas GOV o habilitar el directorio, descarta el estado anterior y exige consulta posterior al backend. La aplicación no simula éxito de un proceso distribuido.
- Nuevos endpoints GET estrictamente privados: estado, vista limitada de usuario para elegir owner y consulta de una empresa por identificador conocido. No se agrega listado global entre tenants ni se elimina RLS.
- Tests de layout protegido, rutas backend y navegador simulado en 320/360/1280px con flujo de doble confirmación, cancelación sin mutación y reintento estable.

## Delimitación y seguridad

- **Nunca habilitar** `AXS_CORPORATE_API_ENABLED` ni `AXS_CORPORATE_PROVISIONING_ENABLED` en producción por este PR.
- No se ejecutan migraciones ni se configuran secretos. `DATABASE_CORPORATE_PROVISIONING_URL` solo corresponde al backend, bajo rol aislado; el frontend no recibe esa credencial.
- Los permisos se comprueban otra vez en cada endpoint, no por esconder controles o por el tipo de rol que devuelve `/auth/me`.
- No existe todavía directorio general de empresas para Superadmin: se retoma mediante el identificador. Un listado global requeriría control-plane explícito, no desactivar RLS.
- La habilitación es **solo del directorio**, no de visitas, QR, biometría, puertas, residencia compartida, correos, ni piloto real.
- ARCO sigue pendiente de prueba end-to-end para la empresa, retención/bloqueo/supresión/respaldos y avisos específicos. Registrar contacto de privacidad no acredita cumplimiento.
- El flujo C2 de escritura CORE+GOV no es una transacción distribuida; ante timeout se conserva UUID y se obliga a consultar antes de cambiar entradas. Queda pendiente la conciliación automatizada si el segundo commit falla.

## Verificación y aceptación pendiente

1. Pruebas de frontend y backend aprobadas en el SHA final; ejecución de PostgreSQL RLS con pruebas de C0–C2.
2. Ensayo de la navegación con cuenta Clerk GLOBAL y con un MSP_ADMIN sin GLOBAL, en entorno Development exclusivamente.
3. Ensayo de aprovisionamiento desde el portal usando la credencial segregada en una base desechable (no datos personales reales).
4. Revisión de exposición de logs y confirmación de no-regresión residencial, sobre todo Dashboard MSP.
5. Mantener PR en borrador hasta fusionar/validar dependencias y definir despliegue en orden.

## Próxima entrega

Mecanismo seguro de recuperación/conciliación de operaciones GOV+CORE y directorio por empresa; posteriormente el portal de owner, anfitriones, recepción y ciclo de visitas corporativas.
