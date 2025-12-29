"""
═══════════════════════════════════════════════════════════════════════════════
DECLARACIÓN AUP: AUP_GOV (Gobierno de Plataforma)
═══════════════════════════════════════════════════════════════════════════════

Entidad estructural que define y controla el PODER sistémico:
quién puede crear, delegar, limitar, suspender o auditar capacidades dentro
de la plataforma.

AUP_GOV NO ES:
  ❌ Un rol operativo (como ADMIN_CONDOMINIO)
  ❌ Permisos hardcodeados
  ❌ RBAC clásico mezclado con negocio

AUP_GOV ES:
  ✓ Plano superior de control (meta-poder)
  ✓ Gobierno explícito y auditable
  ✓ Separación entre poder y operación
  ✓ Base para escalado y monetización

═══════════════════════════════════════════════════════════════════════════════
SUB-ENTIDADES DE AUP_GOV
═══════════════════════════════════════════════════════════════════════════════

🧱 AUP_AUTHORITY (Autoridad de Gobierno)
───────────────────────────────────────────────────────────────────────────────

Actor con potestad declarada para gobernar.

Estructura:
  authority_id:   STRING          # Identificador único
  identity_id:    AUP_IDENTITY    # Quién tiene la autoridad
  tipo:           AUTHORITY_TYPE  # GLOBAL | FIRST_TIER
  estado:         STATUS          # ACTIVO | SUSPENDIDO | REVOCADO
  tenant_id:      AUP_TENANT?     # NULL si GLOBAL, tenant_id si FIRST_TIER
  metadata:       JSON            # Contexto adicional
  created_at:     DATETIME
  revoked_at:     DATETIME?

Tipos:
  - GLOBAL: Autoridad sobre toda la plataforma (ej: MSP_ADMIN global)
  - FIRST_TIER: Autoridad sobre un tenant específico (ej: Dueño de Condominio)

Axioma:
  Solo AUP_AUTHORITY puede crear o delegar poder.


🧱 AUP_POLICY (Política de Gobierno)
───────────────────────────────────────────────────────────────────────────────

Regla declarativa que gobierna límites y delegaciones.

Estructura:
  policy_id:        STRING          # Identificador único
  nombre:           STRING          # Nombre declarativo
  ámbito:           SCOPE_TYPE      # GLOBAL | TENANT | SCOPE
  target_tenant_id: AUP_TENANT?     # NULL si GLOBAL
  
  # QUÉ gobierna
  accion_objetivo:  STRING          # crear_tenant, asignar_scope, generar_qr
  
  # LÍMITES estructurales
  limites:          JSON            # {max_tenants: 10, max_qr_vigencia_dias: 7}
  
  # VIGENCIA
  valida_desde:     DATETIME
  valida_hasta:     DATETIME?
  
  estado:           STATUS          # ACTIVO | SUSPENDIDO | REVOCADO
  metadata:         JSON
  created_at:       DATETIME

Ámbitos:
  - GLOBAL: Aplica a toda la plataforma
  - TENANT: Aplica a un tenant específico
  - SCOPE: Aplica a scopes con cierto nivel

Ejemplos:
  1. GLOBAL: "max_tenants_per_first_tier = 5"
  2. TENANT: "max_usuarios_condominio_a = 100"
  3. GLOBAL: "max_qr_vigencia_dias = 7"

Axioma:
  La política precede a la operación (policy-first).


🧱 AUP_DELEGATION (Delegación de Poder)
───────────────────────────────────────────────────────────────────────────────

Relación que transfiere poder desde una autoridad a identidades o scopes.

Estructura:
  delegation_id:        STRING          # Identificador único
  authority_id:         AUP_AUTHORITY   # Quién delega
  
  # A QUIÉN se delega (mutuamente excluyente)
  target_identity_id:   AUP_IDENTITY?   # Usuario específico
  target_scope_id:      AUP_SCOPE?      # Scope específico
  
  # QUÉ se delega
  permisos_delegados:   JSON            # ["crear_tenant", "asignar_scope"]
  
  # VIGENCIA
  valida_desde:         DATETIME
  valida_hasta:         DATETIME?
  
  estado:               STATUS          # ACTIVO | SUSPENDIDO | REVOCADO
  metadata:             JSON
  created_at:           DATETIME
  revoked_at:           DATETIME?

Axiomas:
  1. Todo poder delegado es explícito
  2. Todo poder delegado es acotado (tiempo/alcance)
  3. Todo poder delegado es revocable

═══════════════════════════════════════════════════════════════════════════════
RELACIONES AUP
═══════════════════════════════════════════════════════════════════════════════

AUP_IDENTITY --tiene→ AUP_AUTHORITY
AUP_AUTHORITY --define→ AUP_POLICY
AUP_AUTHORITY --crea→ AUP_DELEGATION
AUP_DELEGATION --otorga_poder_a→ AUP_IDENTITY | AUP_SCOPE
AUP_POLICY --limita→ AUP_SCOPE | AUP_TENANT
AUP_GOV --genera→ AUP_EVENT (toda acción de gobierno)

═══════════════════════════════════════════════════════════════════════════════
AXIOMAS DE AUP_GOV (NO NEGOCIABLES)
═══════════════════════════════════════════════════════════════════════════════

1. PODER EXPLÍCITO
   Ninguna identidad puede crear o ampliar poder sin AUP_GOV.
   
2. DELEGACIÓN ACOTADA
   Todo poder delegado tiene límites (tiempo, alcance, acciones).
   
3. SEPARACIÓN DE PLANOS
   AUP_GOV no ejecuta operaciones; solo autoriza estructuras.
   
4. AUDITORÍA OBLIGATORIA
   Toda acción de gobierno genera AUP_EVENT.
   
5. POLICY-FIRST
   El gobierno precede a la operación.
   Se evalúan políticas ANTES de permitir acción.

6. REVOCABILIDAD
   Todo poder puede ser revocado instantáneamente.

═══════════════════════════════════════════════════════════════════════════════
TIPOS ESTRUCTURALES
═══════════════════════════════════════════════════════════════════════════════
"""

from enum import Enum

class AuthorityType(str, Enum):
    """Tipos de autoridad de gobierno"""
    GLOBAL = "global"           # Poder sobre toda la plataforma
    FIRST_TIER = "first_tier"   # Poder sobre tenant específico

class PolicyScope(str, Enum):
    """Ámbito de aplicación de política"""
    GLOBAL = "global"           # Aplica a toda la plataforma
    TENANT = "tenant"           # Aplica a tenant específico
    SCOPE = "scope"             # Aplica a scopes con nivel específico

class GovStatus(str, Enum):
    """Estado de entidades de gobierno"""
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    REVOCADO = "revocado"

class GovAction(str, Enum):
    """Acciones que AUP_GOV puede autorizar/denegar"""
    CREAR_TENANT = "crear_tenant"
    ASIGNAR_SCOPE = "asignar_scope"
    REVOCAR_SCOPE = "revocar_scope"
    GENERAR_QR = "generar_qr"
    CREAR_USUARIO = "crear_usuario"
    DELEGAR_PODER = "delegar_poder"
    MODIFICAR_POLITICA = "modificar_politica"

__all__ = [
    "AuthorityType",
    "PolicyScope",
    "GovStatus",
    "GovAction",
]
