# AXS C5 — nuevo ensayo preparado, 15 de noviembre de 2026

## Resultado y estado
PR #117: https://github.com/B10sp4rt4n/MSP_AXS/pull/117
Código: 52a03c633b829057792a6726fa7a4b110539f6f9.
Perfil fijo: visits-20261115. Run: 8d21baad-bc93-4898-8056-99cedd5a40f6.
Se crearon tres bases vacías y cuatro roles independientes en la rama de ensayo Neon br-soft-leaf-b59xcclw, proyecto patient-tree-68362559. No se modificaron el ensayo previo ni producción.
Cada base se certificó vacía después del esquema/ACL/C5 y antes de cualquier semilla. La nueva vigencia comienza el 15 de noviembre a las 07:19 CDMX y vence el 16 de noviembre a las 07:19 CDMX; no renueva la constancia anterior.

## Validación
- Local: 52 pruebas focalizadas aprobadas.
- https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43717968641 — todos los jobs aprobados: Python 1249 aprobadas, 109 omitidas, cobertura 82%; frontend y navegador aprobados.
- https://github.com/B10sp4rt4n/MSP_AXS/actions/runs/43717968640 — todos los jobs aprobados: PostgreSQL 16, 159 aprobadas y 12 de migraciones; PostgreSQL 18, catálogo y C5 aprobados.
- Prueba nueva: perfil fijo, rechazo de conexiones anteriores, roles sin privilegios elevados, certificación inicial C5, esquema, RLS y rechazo por vencimiento.
- ACL remota: CORE 182 comprobaciones de tabla/980 de columna; GOV 35/168; EVENT 14/88; provisioner 182/980. Sin propiedad, membresías, DDL, TEMP, bypass o delegación de privilegios.
- Hash de catálogo SQL cotejado con serialización Python exacta en las tres bases.
- Acceso real por cada rol runtime y lectura de su nueva constancia vigente. Contraseñas independientes verificadas y preparadas en variables privadas del despliegue; ningún secreto en esta evidencia.
- RLS real CORE, tenant A: una membresía y un destino propios; cero membresías/destinos de B. C5 con FORCE RLS; DELETE/TRUNCATE denegados.
- RLS real GOV, tenant A: dos cuotas propias y cero de B.

## Semilla y alcance
Tres sujetos sintéticos ya inscritos en la misma instancia Clerk de prueba; se conservaron sus Clerk subjects y alcances de empresa previamente autorizados. No se copiaron contraseñas de usuario, teléfonos, evidencia, visitas, expedientes ARCO o eventos anteriores. Correos de aplicación sintéticos example.invalid.
Dos empresas sintéticas, dos owners, tres sedes, dos destinos y cuatro cuotas de directorio. Un actor GLOBAL sintético conserva su función de plataforma; GLOBAL no sustituye membresía operativa de visitas.
CORE empieza con cero visitas; EVENT sin eventos de negocio anteriores. La semilla inicial se ejecutó por propietario fuera del backend después de certificar el vacío, sin ampliar los permisos runtime.

## Railway preparado, sin desplegar
Proyecto AXS Corporativo Sandbox, entorno sandbox.
Patch 45565227-ab2b-4f73-b50c-b8272cea53bb: 16 cambios pendientes.
Backend y frontend fijados al SHA validado; backend con nuevo perfil, run_id y URLs de las bases nuevas, usando sólo los roles mínimos. Se mantienen Clerk de prueba y la separación del entorno residencial.
No se llamó accept-deploy: el paso de esta entrega es dejar listo el botón Deploy para el usuario. No se afirma aceptación con Clerk real hasta comprobar el despliegue y el ciclo en pantalla.

## Preservación y pendiente
El ensayo previo conserva run 1917d6a4-bd60-499f-b719-1ddc30ea725f y vencimiento original 15 de noviembre 06:06 CDMX, con sus dos membresías y dos sedes.
Producción conserva deployment 93d1ad63-7259-40bf-beeb-f9250cd11ff9 y SHA 7ccef8e897d98555c0540aa8b03e0340102bf163.
Pendiente: usuario aplica Deploy en sandbox; revisar predeploy/salud y luego autenticación Clerk real, preregistro con folio sintético, autorización, entrada, salida y bitácora. No se incorporan fotos, QR o apertura física.
