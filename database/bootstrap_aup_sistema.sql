-- ═══════════════════════════════════════════════════════════════════════════
-- BOOTSTRAP INICIAL - SISTEMA MSP_AXS (AUP)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Propósito: Inicializar sistema desde CERO ABSOLUTO
--
-- Principios:
--   - Sistema nace CERRADO (sin políticas → denegado)
--   - Todo poder es explícito (vía authorities_gov)
--   - Sin scope → sin operación
--   - UUIDs hardcodeados (reproducibilidad)
--   - Evento de génesis con hash SHA-256
--
-- Orden de ejecución:
--   1. MSP raíz (no comercial)
--   2. Tenant demo/sandbox
--   3. Usuario root (super admin)
--   4. Scope explícito root → demo
--   5. Autoridad global root
--   6. Políticas mínimas (crear_tenant, qr_vigencia)
--   7. Evento de génesis
--
-- Compatible con: PostgreSQL 14+, Neon
-- ═══════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────
-- 1. MSP RAÍZ DE PLATAFORMA
-- ───────────────────────────────────────────────────────────────────────────
INSERT INTO msps_exo (msp_id, nombre) VALUES
('msp_root_00000000000000000001', 'MSP_ROOT_PLATFORM');

-- ───────────────────────────────────────────────────────────────────────────
-- 2. TENANT DEMO/SANDBOX
-- ───────────────────────────────────────────────────────────────────────────
INSERT INTO condominios_exo (condominio_id, msp_id, nombre) VALUES
('tenant_demo_0000000000000001', 'msp_root_00000000000000000001', 'Demo Sandbox');

-- ───────────────────────────────────────────────────────────────────────────
-- 3. USUARIO ROOT (SUPER ADMIN DE PLATAFORMA)
-- ───────────────────────────────────────────────────────────────────────────
-- Password: "root123" (bcrypt hash)
-- Generado con: bcrypt.hashpw(b"root123", bcrypt.gensalt()).decode('utf-8')
INSERT INTO usuarios (usuario_id, msp_id, condominio_id, nombre, email, rol, password_hash, creado) VALUES
(
  'user_root_000000000000000001',
  'msp_root_00000000000000000001',
  'tenant_demo_0000000000000001',
  'Root Administrator',
  'root@mspaxs.platform',
  'MSP_ADMIN',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYXxKzqXbOK',
  now()
);

-- ───────────────────────────────────────────────────────────────────────────
-- 4. SCOPE EXPLÍCITO: ROOT → TENANT DEMO
-- ───────────────────────────────────────────────────────────────────────────
-- Sin este scope, root NO puede operar en el tenant demo
INSERT INTO user_tenant_scope (usuario_id, tenant_id, access_level, estado, created_at) VALUES
(
  'user_root_000000000000000001',
  'tenant_demo_0000000000000001',
  'msp_admin',
  'activo',
  now()
);

-- ───────────────────────────────────────────────────────────────────────────
-- 5. AUTORIDAD GLOBAL (ROOT PUEDE GOBERNAR TODA LA PLATAFORMA)
-- ───────────────────────────────────────────────────────────────────────────
INSERT INTO authorities_gov (authority_id, identity_id, tipo, tenant_id, estado, created_at, metadata) VALUES
(
  'auth_global_root_0000000001',
  'user_root_000000000000000001',
  'global',
  NULL,  -- NULL = autoridad sobre TODA la plataforma
  'activo',
  now(),
  '{"description": "Autoridad suprema de plataforma", "genesis": true}'::jsonb
);

-- ───────────────────────────────────────────────────────────────────────────
-- 6. POLÍTICAS MÍNIMAS
-- ───────────────────────────────────────────────────────────────────────────

-- 6.1 Política global: Crear tenants (solo autoridades globales)
INSERT INTO policies_gov (policy_id, nombre, ambito, target_tenant_id, accion_objetivo, limites, valida_desde, valida_hasta, estado, created_at, metadata) VALUES
(
  'policy_global_crear_tenant',
  'Política Global: Crear Tenants',
  'global',
  NULL,
  'crear_tenant',
  '{"max_tenants_per_msp": 1000, "require_authority_global": true}'::jsonb,
  now(),
  NULL,  -- Sin fecha de expiración
  'activo',
  now(),
  '{"description": "Solo autoridades globales pueden crear tenants", "genesis": true}'::jsonb
);

-- 6.2 Política por tenant: Vigencia máxima de QR (7 días en demo)
INSERT INTO policies_gov (policy_id, nombre, ambito, target_tenant_id, accion_objetivo, limites, valida_desde, valida_hasta, estado, created_at, metadata) VALUES
(
  'policy_tenant_demo_qr_vigencia',
  'Política Demo: Vigencia QR',
  'tenant',
  'tenant_demo_0000000000000001',
  'generar_qr',
  '{"max_dias_vigencia": 7, "max_qr_por_residente_mes": 50}'::jsonb,
  now(),
  NULL,  -- Sin fecha de expiración
  'activo',
  now(),
  '{"description": "Límites de QR para tenant demo", "genesis": true}'::jsonb
);

-- ───────────────────────────────────────────────────────────────────────────
-- 7. EVENTO DE GÉNESIS
-- ───────────────────────────────────────────────────────────────────────────
-- Declara que el sistema nació en este momento preciso
-- hash_evento: SHA-256 de campos críticos concatenados

-- Cálculo manual de hash (en producción usar función PostgreSQL o app):
-- echo -n "evt_genesis_system_000001user_root_000000000000000001genesis_hashtenant_demo_0000000000000001sistemasistema_id_0bootstrap_sistemapermitidoSistema MSP_AXS inicializado desde bootstrap" | sha256sum
-- Resultado: 8a3f9c1b2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a (ejemplo)

INSERT INTO events_aup (
  event_id,
  identity_id,
  session_hash,
  scope_id,
  tenant_id,
  entidad,
  entidad_id,
  accion,
  resultado,
  motivo,
  timestamp,
  hash_evento,
  metadata
) VALUES (
  'evt_genesis_system_000001',
  'user_root_000000000000000001',
  'genesis_hash',  -- Hash especial para evento de génesis (no es sesión JWT)
  NULL,  -- Evento de sistema, no atado a scope específico
  'tenant_demo_0000000000000001',
  'sistema',
  'sistema_id_0',
  'bootstrap_sistema',
  'permitido',
  'Sistema MSP_AXS inicializado desde bootstrap',
  now(),
  '8a3f9c1b2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a',  -- Hash de inmutabilidad
  '{
    "genesis": true,
    "version": "1.0.0-aup",
    "bootstrap_date": "2026-01-01",
    "components_initialized": [
      "msp_root",
      "tenant_demo",
      "user_root",
      "scope_root_demo",
      "authority_global_root",
      "policy_global_crear_tenant",
      "policy_tenant_demo_qr_vigencia"
    ]
  }'::jsonb
);

-- ═══════════════════════════════════════════════════════════════════════════
-- FIN DE BOOTSTRAP
-- ═══════════════════════════════════════════════════════════════════════════
--
-- VERIFICACIÓN POST-BOOTSTRAP (ejecutar manualmente):
--
-- SELECT 'MSP' as entidad, count(*) as total FROM msps_exo
-- UNION ALL
-- SELECT 'Tenants', count(*) FROM condominios_exo
-- UNION ALL
-- SELECT 'Usuarios', count(*) FROM usuarios
-- UNION ALL
-- SELECT 'Scopes', count(*) FROM user_tenant_scope
-- UNION ALL
-- SELECT 'Autoridades', count(*) FROM authorities_gov
-- UNION ALL
-- SELECT 'Políticas', count(*) FROM policies_gov
-- UNION ALL
-- SELECT 'Eventos', count(*) FROM events_aup;
--
-- Resultado esperado:
--   MSP:         1
--   Tenants:     1
--   Usuarios:    1
--   Scopes:      1
--   Autoridades: 1
--   Políticas:   2
--   Eventos:     1
--
-- ═══════════════════════════════════════════════════════════════════════════
