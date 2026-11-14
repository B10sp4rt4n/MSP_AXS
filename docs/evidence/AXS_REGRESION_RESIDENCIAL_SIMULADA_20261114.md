# AXS: regresión residencial simulada del candidato integrado

Fecha: 2026-11-14. Base de código: `a2b88a34f2141b36dcde8d8d5630d5ae2c254c18`.

## Recorrido reproducible

`tests/test_residential_simulated_journey.py` ejecuta solicitudes HTTP contra
las rutas de la aplicación, con SQLite temporal, JWT de prueba y fotografías
de colores generadas en memoria. El almacenamiento privado es un adaptador en
memoria. No utiliza cuentas Clerk, fotografías personales ni servicios vivos.

Las tres variantes recorren el mismo preregistro autorizado por el residente,
destino de vivienda, rechazo de QR incorrecto y de entrada manual que eluda el
QR, entrada con QR válido, rechazo de reutilización, identificación de ambos
lados y salida. Comprueban que los reintentos conservan los movimientos y sus
horas, sin duplicar la visita ni las evidencias.

| Variante | Comprobación adicional |
| --- | --- |
| Sin foto de salida | La salida queda registrada sin exigir fotografía. |
| Con foto de salida | Captura y reintento con el mismo identificador producen una evidencia. |
| Fallo de almacenamiento y reintento | El fallo de la fotografía conserva la salida y permite reintentar sólo la carga. |

Cada variante verifica aislamiento en ambos sentidos entre dos condominios,
lectura privada de fotografías, bloqueo del residente a la evidencia de
identificación y revocación del guardia. Después de revocar se reutiliza el
mismo JWT: detalle, fotografía y QR deben devolver 403.

El recorrido corporativo ya existente, `tests/test_corporate_simulated_journey.py`,
cubre empresas A/B, cuotas, aislamiento en ambos sentidos y revocación de
membresía con el token ya emitido. Se ejecuta junto con la regresión residencial.

## Ejecución

```bash
python -m pytest -q --no-cov tests/test_residential_simulated_journey.py tests/test_corporate_simulated_journey.py tests/test_destinos_visitas.py tests/test_guardia_recuperacion.py tests/test_reglas_acceso.py tests/test_identificaciones.py tests/test_evidencias_salida.py tests/test_tenant_modalidad_http.py tests/test_tenant_modalidad_privacy_alexa.py
cd frontend-next
npm run test:roles
```

Los workflows existentes ejecutan automáticamente la suite Python completa,
roles e interfaz en navegador, y los gates PostgreSQL 16/18 para esta rama.
El resultado y los enlaces a cada ejecución se registran en el PR, asociados
al commit exacto. Las pruebas concurrentes requieren el job PostgreSQL.

## Alcance de la evidencia

Esto acredita comportamiento reproducible de las rutas y reglas del código.
No acredita entrega de correo, autenticación Clerk real, persistencia en Blob
real, cámara física, funcionamiento sin internet, ni una prueba de operación
con usuarios reales. Las pruebas de navegador usan respuestas HTTP sintéticas;
los gates PostgreSQL son independientes del recorrido SQLite.

Esta rama añade pruebas y documentación. No modifica comportamiento del
producto, configuración, datos remotos ni despliegues. El sandbox continúa
apuntando al candidato base; no se fusiona ni se activa producción.
