# Simulación corporativa posterior al despliegue

Código ejecutado: 7ccef8e897d98555c0540aa8b03e0340102bf163 (PR #114). Ejecución local de tests HTTP con SQLite descartable, JWT sintéticos y adaptadores de transporte. Los resultados detallados y huellas de los XML JUnit se guardan en el JSON adjunto. La fecha del nombre identifica la ejecución UTC; corresponde a la sesión del 14/11/2026 en CDMX.

## Resultado por capacidad

| Capacidad | Resultado comprobado |
| --- | --- |
| GLOBAL y alta de empresas A/B | Altas sintéticas; rechazo de usuarios sin facultad; reintento del mismo comando sin duplicar empresa |
| Habilitación del directorio | Antes de habilitar, consulta denegada; habilitación explícita y cuotas configuradas por GLOBAL |
| Sedes y destinos | Dos sedes permitidas y tercera rechazada; un destino por sede configurado y excedente rechazado |
| Separación A/B | Consulta y escritura cruzadas rechazadas en ambos sentidos; GLOBAL no sustituye una membresía de directorio |
| Membresías y sedes | Host limitado a sede asignada; no puede crear destinos; revocación bloquea las solicitudes siguientes con el mismo JWT |
| Conciliación y privacidad | Suites de revisión/reintentos y ARCO corporativo aprobadas en simulación; no se infiere ejecución real de ARCO |
| Auditoría corporativa | El recorrido integrado comprueba eventos encolados en outbox; no equivale a bitácora corporativa de entrada/salida |
| Entrada/salida corporativa | **No disponible en el alcance actual.** Las rutas residenciales devuelven 403 para tenants corporativos, incluso con directorio habilitado |
| Ciclo residencial | Tres variantes sintéticas de prerregistro/entrada/salida/evidencias y revocación aprobadas; son una regresión residencial separada |

## Hallazgo que cambia el siguiente paso

La propuesta conversacional anterior incluía completar entrada/salida corporativa. La inspección de backend/routers/corporativo_router.py y la matriz HTTP muestran que el módulo actual es directorio de sedes/destinos, sin visitas ni hardware. No fue correcto presentarlo como un recorrido corporativo ya ejecutable. La simulación acredita la base de gobierno/directorio y sus límites, pero **no cierra un piloto corporativo de control de accesos**.

La matriz de modalidad prueba 53 combinaciones de método/ruta con cuatro actores y dos estados de habilitación, más una comprobación de cobertura: las operaciones residenciales se rechazan para el tenant corporativo sin cambiar sus datos operativos y con auditoría de denegación sanitizada.

## Límites de la evidencia

No se utilizaron usuarios reales, Clerk, cámaras ni almacenamiento Blob real. Las conexiones del ensayo son SQLite, por lo que no prueban RLS PostgreSQL en esta ejecución. Las memberships y asignaciones de host del recorrido integrado se siembran como fixtures; no se acredita un flujo UI/API de administración de membresías. Las pruebas residenciales de bitácora y evidencia no se atribuyen a empresas corporativas.

No se modificaron producción, variables, roles o bases remotas ni se activaron banderas corporativas. No se reutilizó el sandbox remoto vencido. No se simularon respuestas como si fueran observaciones de producción.

## Siguiente desarrollo concreto

Definir e implementar el contrato de visita corporativa: empresa, sede, destino y anfitrión/membresía; roles operativos de recepción/seguridad; autorización, entrada, salida, evidencia opcional y eventos/bitácora. Mantener el rechazo de rutas residenciales. Después ejecutar el ciclo corporativo nuevo y las pruebas de cuotas, revocación y separación A/B, y repetir el ensayo con PostgreSQL aislado antes de habilitar un piloto productivo.
