# Aceptación residencial posterior al cambio de roles

Fuente: confirmaciones directas de Salvador en esta conversación, posteriores al despliegue cf190d6b-5162-4611-a786-b35f842568f6 del commit 02667290d6a9e762818372459c7184c915988e87. No son una consulta independiente de la base ni incluyen una captura o un folio de visita.

| Comprobación | Evidencia de usuario | Estado |
| --- | --- | --- |
| Inicio de sesión real | «Ya accedí» | Confirmado por el usuario |
| Residentes/visitas, bitácora y reporte | «Si, sin problemas», en respuesta a esos tres controles | Confirmado por el usuario |
| Entrada de la visita probada | «Funcionó, entró…», identificación omitida de esta evidencia pública | Confirmado por el usuario |
| Salida y ambos movimientos en bitácora | «Bitácora completa ciclo cerrado» | Confirmado por el usuario |

Se cierra la aceptación del recorrido residencial probado y del cambio de permisos en ese alcance. No se extiende a todos los condominios, todos los perfiles, captura de cámara, almacenamiento Blob, restauración de archivos o activación corporativa. Las evidencias técnicas independientes de permisos, conexiones, salud y Clerk están en AXS_PERMISOS_DEPLOY_VERIFICADO_20261114.md.

## Aviso de inicialización

La revisión de código identifica un create_all heredado en PostgreSQL que intenta crear identity_retention usando el rol CORE sin DDL. La tabla y su piloto no están habilitados en producción. Se prepara una corrección independiente que sólo permite bootstrap automático para SQLite; PostgreSQL conserva migraciones explícitas y los gates existentes. No se concede CREATE, no se crea la tabla y no se activa retención. Hasta desplegar esa corrección, el aviso puede repetirse al arrancar la versión actual.

## Próximo ensayo corporativo

Usar entorno de pruebas aislado y datos sintéticos. Las banderas productivas corporativas permanecen desactivadas. La siguiente secuencia es un plan, no una declaración de ejecución:

1. GLOBAL: comprobar autorización explícita y denegación para quien carece de ella.
2. Empresas A/B: crear empresa y sede con UUID estable; repetir solicitudes sin duplicados.
3. Destinos y membresías: asignar alcance por empresa/sede y comprobar denegación sin membresía.
4. Límites GOV: aceptar cuotas propias, bloquear exceso y modificación global o de otra empresa.
5. Acceso y auditoría: completar entrada/salida con eventos y bitácora coherentes.
6. Separación y privacidad: intentar cruces A/B, revocar membresía y comprobar acceso posterior y alcance ARCO.

Registrar resultados, identificadores sintéticos y errores por paso. No declarar piloto corporativo aceptado hasta ejecutar esa matriz. No reabrir una visita real cerrada para utilizarla como prueba.
