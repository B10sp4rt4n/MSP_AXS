# Preparación de activación ARCO en producción
Estado: preparada, pendiente de cierre de CI y acceso administrativo al frontend. No equivale a activación.

## Validación completada
- Suite backend local: 565 aprobadas, 26 omitidas por requerir PostgreSQL desechable; cobertura 80 %. Ejecutada con los cambios de aplicación del PR #90, sin acceder a bases externas.
- CI del commit 0d2d6605e39fdd69a1f46b91b11ea87b0a09ff8b: PostgreSQL RLS SUCCESS (39901812343), roles y navegador SUCCESS (39901812405). Job general backend todavía in_progress en la última consulta; no se declara aprobado.
- Migración aditiva ensayada sobre copia actual de producción: Neon patient-tree-68362559, rama br-summer-queen-b536tft0, padre br-empty-firefly-b5ob1gsg, LSN 0/4664650.
- Tabla nueva arco_cases con RLS habilitado y forzado. Rol axs_core_app sin bypass, SELECT/INSERT/UPDATE concedidos, DELETE no concedido. Consulta con credencial del rol y contexto del condominio aprobada; cero expedientes. No se copiaron expedientes sintéticos de Development a producción.
- Se omitió DROP POLICY del archivo original porque la tabla no existía. SQL de primera aplicación aditiva: migrations/20261023_arco_cases_first_apply.sql. La migración repetible original sigue disponible para ensayos.

## Alcance inicial preparado
Primer condominio propuesto según el piloto existente: Residencial San Luis, condo_b6b00ba13ba5. Operador inicial preparado: Salvador, usr_b8f20a70e2bb4b4e (MSP_ADMIN). Ambos identificadores se verificaron en la rama de producción en modo lectura. Esta propuesta no modifica el rol base ni incorpora otros operadores.

Backend Railway: proyecto 532a32f5-6313-4ee3-98de-cfcfc225dbb7, entorno 72f597ee-89d2-4dd4-9295-6618d3694d22, servicio 55c12ef5-ba69-449c-ad84-b77ee280eb5b. Fuente main, healthcheck /health y predeploy check_core_rls.py conservados. El conector devuelve valores de variables redactados: falta confirmar que DATABASE_CORE_URL apunta a la rama productiva identificada antes de aplicar la migración allí.

Frontend localizado mediante listado Vercel: proyecto prj_m4X1hxQCfaYOFWzN50Uu1z6NrE3S, frontend-next, equipo team_wCPRqvRGXWpRT4eUvfAz38jF. Consultar su configuración devuelve 403 por falta de autorización al equipo salvador-ruiz-esparzas-projects. Se necesita acceso a ese equipo en la conexión Vercel, no cambios a los permisos de usuarios AXS. El conector recomienda authorize_team_access, pero esa operación no está expuesta en las herramientas de esta sesión.

## Secuencia de liberación pendiente
1. Cerrar el job backend CI y confirmar el SHA exacto a fusionar.
2. Recuperar autorización al equipo Vercel y confirmar repositorio, dominio, rama y configuración del frontend.
3. Confirmar el endpoint CORE de Railway. Aplicar la migración ensayada en la base correcta, con ARCO deshabilitado, y verificar RLS/permisos.
4. Fusionar el PR #90 y esperar backend y frontend con estado final exitoso. Verificar /health y portal público.
5. Configurar backend AXS_ARCO_CASES_ENABLED=true y AXS_ARCO_OPERATORS=usr_b8f20a70e2bb4b4e:condo_b6b00ba13ba5. Mostrar entrada del frontend con NEXT_PUBLIC_ARCO_CASES_UI_ENABLED=true y redesplegar.
6. Con sesión productiva del operador, verificar listado autorizado de San Luis y denegación de otro cliente sin introducir solicitudes ficticias en producción.
7. Registrar los despliegues y evidencia final. La prueba Clerk previa de Development no sustituye esta verificación productiva.

## Reversión operativa
Deshabilitar AXS_ARCO_CASES_ENABLED y vaciar AXS_ARCO_OPERATORS; ocultar la entrada del frontend y esperar despliegues exitosos. Conservar la tabla y sus expedientes/auditoría; no borrar datos ni revertir esquema como parte de esta reversión.

## Operación
El registro solo conserva seguimiento asistido. La revisión de identidad, los plazos/calendario, la evidencia privada, la respuesta al titular y la ejecución real de acciones corresponden al responsable. No envía correos ni ejecuta eliminación de datos. Los plazos propuestos de PR #89 no se adoptan por esta liberación.

## Actualización posterior de verificación

El acceso Vercel quedó confirmado al consultar directamente el proyecto autorizado sin teamId: devolvió su identidad y app.axs-mx.com. El 403 con teamId no se resolvió ampliando permisos y la conexión no fue desconectada. Por tanto, la observación inicial de bloqueo Vercel anterior ya no es un pendiente.

La consola web Railway mostró un aviso de incidencia de plataforma y no abrió la configuración de este servicio (pantalla 404 sin sesión). Esto no prueba una caída del backend; el conector había reportado el servicio con estado SUCCESS. La conexión CORE sigue sin verificarse. La revisión automática rechazó crear una función auxiliar productiva para leer metadatos de conexión; no se creó ni se intentó ejecutar por otra vía. Se acudió a la alternativa de lectura de consola.

Se detectó un identificador pytest de más de 8 MB generado a partir del caso de archivo demasiado grande de test_evidencias_salida.py. Se sustituyeron los identificadores automáticos por nombres cortos sin cambiar datos ni aserciones. Sus nueve pruebas pasaron localmente. Es una corrección de diagnóstico de logs; no se afirma que explique por sí sola el job CI todavía pendiente.

La activación, la migración productiva y la fusión permanecen pendientes. No se ejecutó ninguna de esas tres acciones durante esta verificación.
