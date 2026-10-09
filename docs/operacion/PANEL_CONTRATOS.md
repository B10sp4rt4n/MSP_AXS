# Panel de contratos — candidato previo a producción

Ruta `/dashboard/proveedores`, enlazada desde Dashboard MSP. Requiere sesión;
la lectura y cada mutación siguen exigiendo Authority GLOBAL activa en backend.
No concede autoridad por rol ni convierte a un MSP_ADMIN en operador GLOBAL.
Sin una consulta autorizada no muestra controles de mutación.

Flujo: consultar ID de condominio → revisar proveedor/contrato vigente y permisos
→ registrar procedencia desconocida con evidencia → revisar y confirmar baja →
abrir UUID nuevo para el mismo u otro MSP existente → otorgar permiso nuevo a
personal existente → consultar historial y referencias de auditoría.

Los reintentos de apertura conservan UUID y datos. Después de una respuesta
exitosa, una apertura posterior usa otro UUID, incluso con la misma referencia.
No reabre contratos cerrados ni reactiva scopes. La baja incluye el contrato
vigente; mantiene compatibilidad con una relación legacy sin contrato. Un cierre
con procedencia sin resolver queda bloqueado. Todas las mutaciones tienen un
paso de revisión explícita y exclusión de doble envío. Un fallo de actualización
posterior a una mutación exitosa conserva el comprobante y oculta controles
obsoletos. Los errores estructurados muestran IDs de permisos pendientes.

## Pruebas reproducibles

Desde `frontend-next`, después de `npm ci`:

```bash
npm run test:roles
npx next typegen
npx tsc --noEmit
npx eslint src/components/ProviderConsole.tsx src/app/dashboard/proveedores/page.tsx src/lib/provider-contracts.ts
npm install --no-save --package-lock=false playwright@1.58.2
npx playwright install --with-deps chromium
node tests/provider-console.browser.cjs
```

El ensayo de navegador monta el componente React con Clerk y transporte
sintéticos; bloquea cualquier solicitud externa. Comprueba denegación de acceso,
dos ciclos, UUID estable después de fallo de red posterior al commit, cierre por
contrato y controles ocultos tras fallo de actualización. No es una prueba de
Clerk/Next/backend integrados ni sustituye revisión visual humana. Está incluido
en un job dedicado de CI sin secretos ni acceso a producción.

Validación local inicial: 21 pruebas frontend aprobadas, TypeScript y ESLint
aprobados; backend contratos/baja: 7 aprobadas, 4 omitidas por PostgreSQL.
Chromium no estaba instalado; descarga local bloqueada/fallida. Consultar CI del
PR para el resultado real del ensayo de navegador; no asumir aprobación local.

Pendiente antes de producción: revisión visual con operador de desarrollo,
prueba integrada con Clerk y backend de desarrollo actualizado, y decisión de
publicación. Configurar NEXT_PUBLIC_API_URL hacia desarrollo antes de arrancar
una interfaz conectada: el cliente existente usa producción como fallback.
No arrancar esta consola conectada usando ese fallback para ensayos.
No se modificaron Railway, relaciones reales ni main. La fusión continúa
retenida porque main dispara despliegue automático.
