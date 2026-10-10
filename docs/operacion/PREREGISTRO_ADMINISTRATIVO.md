# Preregistro administrativo sin vivienda propia

El administrador no necesita tener una casa asignada. Para generar un QR debe seleccionar explícitamente un condominio autorizado y un destino de su catálogo. El rol descriptivo no sustituye la comprobación de acceso ADMIN_CONDOMINIO ni la política GOV generar_qr.

La pantalla existente `/dashboard/residente/nueva` adapta el formulario según `/auth/me`. MSP_ADMIN y ADMIN_CONDOMINIO eligen condominio y destino; RESIDENTE conserva su vivienda asignada. No se cambia el perfil del operador ni se asigna una casa ficticia.

## Contrato API

`POST /preregistro/crear`, autenticado:

```json
{
  "nombre_visitante": "Visitante sintético",
  "tipo_visita": "visita_personal",
  "condominio_id": "condominio-autorizado",
  "destino_id": "destino-del-catalogo"
}
```

Para administración ambos identificadores son obligatorios. Se rechazan destinos ajenos, inexistentes y OTRO. Se admiten viviendas y destinos comunes catalogados. El residente puede omitir ambos campos; si los envía, deben coincidir con su condominio y vivienda. La autorización queda a nombre del operador. Visita, QR y eventos conservan la transacción existente.

## Validación sintética

- `python -m pytest tests/test_destinos_visitas.py tests/test_event_outbox.py tests/test_reglas_acceso.py -q --no-cov`: 36 aprobadas, 3 omitidas por requerir PostgreSQL en la ejecución local.
- `cd frontend-next && npx tsc --noEmit`: aprobado.
- `npm run test:roles`: 21 aprobadas.
- `node tests/preregistro-admin.browser.cjs`: incluido en CI. No ejecutado localmente: Chromium no disponible y descarga fallida. Comprueba ambos administradores, payload del residente, respuesta tardía de catálogo y errores de perfil/reglas/rol con transporte sintético.

Las pruebas backend cubren administradores sin vivienda, aislamiento entre condominios, ausencia de scope, denegación GOV, destino del residente, atribución de auditoría y rollback ante fallo al generar QR. Las pruebas locales usan SQLite aislado; no certifican RLS PostgreSQL ni un despliegue real.

## Alcance de entrega

PR separado desde main 5f198eab305976c86e672a4b6166bce7e18cf33e. Sin migraciones, cambios de perfiles, visitas reales ni despliegue. Antes de fusionar: revisar CI y comprobar el formulario con cuenta y destinos exclusivamente sintéticos en un entorno de pruebas. La fusión y publicación quedan fuera de esta preparación.
