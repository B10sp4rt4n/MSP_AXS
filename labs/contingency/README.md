# AXS · Laboratorio de contingencia O0

Primera implementación aislada de [la propuesta](../../docs/ADR_AXS_CONTINGENCIA_001.md).
HTML servido localmente + SQLite persistente + un segundo SQLite que simula el receptor.
Es parte del mismo repositorio, sin importar ni modificar el backend o frontend de AXS.

**Solo datos ficticios. No es caseta productiva, no abre puertas, no valida QR actuales,
no envía notificaciones ni sincroniza con la nube.** Selector A/B = escenarios de
prueba, no autenticación/aislamiento productivo. No introducir datos personales reales.

## Ejecutar

Requisito: Python 3.10 o superior con `sqlite3` y un navegador moderno.
Sin instalar dependencias Python, servicios, API keys ni herramientas IA.
Desde la raíz del repositorio, en Windows/macOS/Linux:

```sh
python -m labs.contingency.server --data-dir tmp/axs-contingency-lab
```

Abrir **http://127.0.0.1:8766** en el mismo equipo. El servicio solo escucha en loopback.
No requiere internet externo; la carga de la página y las peticiones API usan localhost.
Un archivo HTML abierto por sí solo no sustituye este servicio de persistencia.

Los archivos `local.synthetic.sqlite` y `receiver.synthetic.sqlite` quedan en la carpeta
indicada. Reiniciar con esa MISMA carpeta conserva movimientos, acuses y vigencia original.
La copia ficticia vence una hora después de crear el escenario; reiniciar no la renueva.
Para un escenario nuevo usar otra carpeta, preservando la anterior para revisión.
No borrar bases con pendientes para «restablecer» la pantalla.

## Recorrido de prueba

1. Seleccionar A. Revisar última copia, vencimiento, destino y pase ficticio.
2. Registrar entrada. Cerrar/reabrir la página: el evento sigue pendiente.
3. Opcionalmente detener el proceso con Ctrl+C y reiniciar con la misma carpeta.
4. Registrar salida. Pulsar «Simular confirmación perdida»: el receptor guarda el
   primer evento, pero el nodo no recibe su acuse.
5. Pulsar «Sincronizar con simulador». Hay dos hechos, ambos recibidos una sola vez.
   Repetir sincronización no aumenta el total.
6. Seleccionar B: el diario de A no aparece. Antes de la entrada local, cancelar
   la visita SOLO en el receptor. Registrar entrada/salida y sincronizar.
7. Ambos hechos de B quedan «En revisión»; el receptor conserva la cancelación.

La salida es una observación y no habilita un mecanismo físico de egreso. El
laboratorio la conserva después de vencer la copia, siempre que exista entrada local.
Las excepciones humanas y visitas desconocidas no están implementadas.

## Verificación automatizada

```sh
python -m unittest discover -s labs/contingency -p 'test_*.py' -v
```

Usa bases temporales y HTTP loopback, sin importar la configuración AXS ni leer `.env`.
18 casos: persistencia/reapertura, respuesta perdida, reintento alterado, consumo único,
alcance MSP/tenant/guardia/nodo/caseta, vencimiento, retroceso respecto al último tiempo
conservado, salida, cancelación remota, secuencias, dos carreras con SQLite real,
rollback de diario/proyección ante fallo inyectado, restricciones de diario y frontera HTTP.
La falla de almacenamiento se inyecta con un trigger; no es una prueba física de disco lleno.

Navegador, contra una carpeta de datos NUEVA y puerto 8766:

```sh
node labs/contingency/test_browser.cjs
```

Esta prueba requiere Playwright y Chromium instalados en el entorno de pruebas.
No son dependencias de la aplicación. Comprueba UI → API → SQLite, pérdida de respuesta
de operación, recuperación con mismo UID tras recargar, acuse perdido, conciliación,
selector A/B, ancho móvil y ausencia de solicitudes externas. No utilizarla contra
una carpeta de ensayo manual que se desee conservar sin movimientos adicionales.

El workflow preparado ejecutará la suite SQLite en Ubuntu y Windows y la prueba de
navegador en Ubuntu cuando se autorice su publicación. La suite general AXS permanece
independiente. Ver el resultado del SHA antes de declarar CI aprobada.

## Límites explícitos

- Fixtures e identidad sintética fijados en código; token HTTP local evita llamadas
  casuales desde otros orígenes, pero no sustituye autenticación de dispositivos/guardias.
- Archivos sin cifrar y sin respaldo automático: nunca usar datos personales.
- Detección parcial de retroceso de reloj, no reloj seguro ni protección contra restaurar
  una base antigua. Firmas, epoch/antirrollback y permisos temporales pendientes de O1.
- Diario append-only por triggers, no custodia forense; un administrador del equipo puede
  modificar archivos. El checksum detecta cambios accidentales, no falsificación de autor.
- Un nodo por escenario; no coordinación de casetas aisladas, PWA ni pruebas en iPad.
- El receptor aplica solo dos transiciones sintéticas; no replica las reglas completas
  de AXS ni acredita seguridad, escala o compatibilidad productiva.
- No hay carga de fotos, validación de documentos ni lector QR/cámara en O0.
- No hay modo nube real ni detección de red. No se observan bases ni servicios AXS.

Siguiente gate: contrato verificable y habilitación de nodo/guardia por inmueble (O1),
antes de desarrollar el receptor productivo o pedir activación de un piloto.
