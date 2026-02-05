"""
═══════════════════════════════════════════════════════════════════════════════
SMOKE TEST CONCEPTUAL - PRE-PILOTO AUP
═══════════════════════════════════════════════════════════════════════════════

OBJETIVO:
  Validar que el sistema AUP está ontológicamente correcto y listo para piloto.

PREREQUISITOS:
  - Backend ejecutándose localmente o en producción
  - Variables de entorno configuradas (ver .env.example)
  - Usuario de prueba creado en sistema

═══════════════════════════════════════════════════════════════════════════════
TEST 1: AUP_SESSION (Identidad)
═══════════════════════════════════════════════════════════════════════════════

OBJETIVO: Validar que AUP_SESSION genera JWT válido y registra evento.

COMANDO:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@msp.com",
    "password": "your_password"
  }'
```

CRITERIOS DE ÉXITO:
  ✅ Retorna JWT válido (campo "access_token")
  ✅ Token decodificable con estructura correcta:
     - sub: usuario_id
     - exp: timestamp futuro
  ✅ Event registrado en aup_event:
     - entidad: "session"
     - accion: "login"
     - resultado: "exito"

VALIDACIÓN MANUAL (base de datos):
```sql
-- Consultar evento de login
SELECT * FROM events_aup 
WHERE entidad = 'session' 
  AND accion = 'login' 
  AND resultado = 'exito'
ORDER BY timestamp DESC LIMIT 1;
```

═══════════════════════════════════════════════════════════════════════════════
TEST 2: AUP_SCOPE (Alcance)
═══════════════════════════════════════════════════════════════════════════════

OBJETIVO: Validar que sistema rechaza operaciones sin scope válido.

COMANDO (debe FALLAR):
```bash
# Intenta listar visitas sin scope válido en ese tenant
curl -X GET http://localhost:8000/visitas?condominio_id=tenant-invalido \
  -H "Authorization: Bearer $TOKEN"
```

CRITERIOS DE ÉXITO:
  ✅ Retorna 403 Forbidden
  ✅ Mensaje: "Sin scope válido en tenant"
  ✅ Event registrado en aup_event:
     - resultado: "denegado"
     - motivo: contiene "scope"

COMANDO (debe FUNCIONAR):
```bash
# Listar visitas con scope válido
curl -X GET http://localhost:8000/visitas?condominio_id=tenant-valido \
  -H "Authorization: Bearer $TOKEN"
```

CRITERIOS DE ÉXITO:
  ✅ Retorna 200 OK con lista de visitas
  ✅ Sistema consultó user_tenant_scope en aup_gov

VALIDACIÓN MANUAL (base de datos):
```sql
-- Consultar scope del usuario
SELECT * FROM user_tenant_scope 
WHERE usuario_id = 'usuario-test' 
  AND tenant_id = 'tenant-valido'
  AND estado = 'activo';
```

═══════════════════════════════════════════════════════════════════════════════
TEST 3: AUP_EVENT (Registro de Verdad)
═══════════════════════════════════════════════════════════════════════════════

OBJETIVO: Validar que operaciones generan eventos inmutables.

COMANDO:
```bash
curl -X POST http://localhost:8000/visitas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "condominio_id": "tenant-valido",
    "nombre_visitante": "Juan Pérez",
    "casa_unidad": "101",
    "tipo_visita": "Paquetería",
    "vigencia": "2025-12-31T23:59:59"
  }'
```

CRITERIOS DE ÉXITO:
  ✅ Retorna 201 Created con visita_id
  ✅ Visita escrita en aup_event (tabla visitas)
  ✅ Event registrado en aup_event (tabla events_aup):
     - entidad: "visita"
     - accion: "crear"
     - resultado: "exito"
     - entidad_id: visita_id creado

VALIDACIÓN MANUAL (base de datos):
```sql
-- Consultar visita creada
SELECT * FROM visitas 
WHERE visita_id = 'visita-id-retornado';

-- Consultar evento de creación
SELECT * FROM events_aup 
WHERE entidad = 'visita' 
  AND accion = 'crear' 
  AND entidad_id = 'visita-id-retornado';
```

═══════════════════════════════════════════════════════════════════════════════
TEST 4: AUP_GOV (Denegación por Poder)
═══════════════════════════════════════════════════════════════════════════════

OBJETIVO: Validar que AUP_GOV deniega operaciones que violan políticas.

PRERREQUISITO:
  Crear policy que limite vigencia de QR a 7 días máximo.

COMANDO (debe FALLAR):
```bash
# Intenta generar QR con vigencia mayor a política
curl -X POST http://localhost:8000/qr/generar/visita-id \
  -H "Authorization: Bearer $TOKEN"
```

CRITERIOS DE ÉXITO:
  ✅ Sistema consulta Policy en aup_gov
  ✅ Si visita supera max_qr_vigencia_dias:
     - Retorna 403 Forbidden
     - Mensaje: "Gobierno denegó operación"
     - Event registrado:
       - entidad: "qr"
       - accion: "generar"
       - resultado: "denegado"
       - motivo: contiene "politica"

VALIDACIÓN MANUAL (base de datos):
```sql
-- Consultar policy activa
SELECT * FROM policies_gov 
WHERE accion_objetivo = 'generar_qr' 
  AND estado = 'activo';

-- Consultar evento de denegación
SELECT * FROM events_aup 
WHERE entidad = 'qr' 
  AND accion = 'generar' 
  AND resultado = 'denegado'
ORDER BY timestamp DESC LIMIT 1;
```

═══════════════════════════════════════════════════════════════════════════════
RESULTADO ESPERADO FINAL
═══════════════════════════════════════════════════════════════════════════════

✅ TEST 1: Login genera JWT y Event
✅ TEST 2: Request sin scope válido se rechaza
✅ TEST 3: Operación genera Event en aup_event
✅ TEST 4: Policy deniega operación correctamente

SI TODOS LOS TESTS PASAN:
  → Sistema está ontológicamente correcto
  → Memoria está bien declarada por dominio
  → Sistema listo para piloto

SI ALGÚN TEST FALLA:
  → Revisar configuración de variables de entorno
  → Verificar que migraciones se ejecutaron correctamente
  → Consultar logs del backend para detalles del error

═══════════════════════════════════════════════════════════════════════════════
NOTAS IMPORTANTES
═══════════════════════════════════════════════════════════════════════════════

1. DESARROLLO LOCAL:
   - Usa SQLite (3 archivos .db separados)
   - No requiere Neon

2. PRODUCCIÓN (NEON):
   - Requiere 3 bases PostgreSQL separadas
   - Ver DATABASE_URL_CORE/EVENT/GOV en .env.example

3. MIGRACIONES:
   - CORE: schema_axs.sql
   - EVENT: migration_03_events_aup.sql
   - GOV: migration_04_gov.sql

4. SCRIPTS DE BOOTSTRAP:
   - scripts/seed_gov_bootstrap.py (crear authority inicial)
   - scripts/seed_planes_comerciales.py (crear policies de planes)

═══════════════════════════════════════════════════════════════════════════════
"""
