"""
AUP_GOV — Modelos de Poder Explícito

Responsabilidad: Declarar quién tiene poder, sobre qué, bajo qué límites.

Axiomas:
1. Gobierno precede a operación
2. Sin política asignada → denegado (default deny)
3. Si AUP_GOV falla → operación denegada
4. Revocación es inmediata (sin cache)

Contiene:
- Authority (AUP_AUTHORITY)
- Policy (AUP_POLICY)
- Delegation (AUP_DELEGATION)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum, Index
from datetime import datetime
import enum

from .engine import Base_GOV


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════

class AuthorityType(str, enum.Enum):
    """Tipos de autoridad de gobierno"""
    GLOBAL = "global"           # Poder sobre toda la plataforma
    FIRST_TIER = "first_tier"   # Poder sobre tenant específico


class PolicyScope(str, enum.Enum):
    """Ámbito de aplicación de política"""
    GLOBAL = "global"           # Aplica a toda la plataforma
    TENANT = "tenant"           # Aplica a tenant específico


class GovStatus(str, enum.Enum):
    """Estados de entidades de gobierno"""
    ACTIVO = "activo"
    REVOCADO = "revocado"
    SUSPENDIDO = "suspendido"


# ═══════════════════════════════════════════════════════════════════════════
# AUTHORITY (AUP_AUTHORITY)
# ═══════════════════════════════════════════════════════════════════════════

class Authority(Base_GOV):
    """
    AUP_AUTHORITY: Actor con potestad declarada para gobernar.
    
    Axiomas:
      - Todo poder es explícito (no heredado)
      - Todo poder tiene alcance declarado (GLOBAL o FIRST_TIER)
      - Todo poder es revocable
    
    Ejemplos:
      - GLOBAL: MSP_ADMIN puede crear tenants
      - FIRST_TIER: Dueño de Condominio A gobierna solo Condominio A
    """
    __tablename__ = "authorities_gov"
    
    # Identificador único
    authority_id = Column(String, primary_key=True, index=True)
    
    # AUP_IDENTITY que tiene la autoridad (referencia a aup_core.usuarios)
    identity_id = Column(String, nullable=False, index=True)
    
    # Tipo de autoridad
    tipo = Column(SQLEnum(AuthorityType), nullable=False, index=True)
    
    # Tenant sobre el que tiene autoridad (NULL si GLOBAL)
    tenant_id = Column(String, nullable=True, index=True)
    
    # Estado
    estado = Column(SQLEnum(GovStatus), nullable=False, default=GovStatus.ACTIVO)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Metadata adicional (contexto de autoridad)
    metadata_json = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_authority_identity', 'identity_id', 'estado'),
        Index('idx_authority_tenant', 'tenant_id', 'estado'),
    )


# ═══════════════════════════════════════════════════════════════════════════
# POLICY (AUP_POLICY)
# ═══════════════════════════════════════════════════════════════════════════

class Policy(Base_GOV):
    """
    AUP_POLICY: Regla declarativa que gobierna límites y delegaciones.
    
    Axioma: La política precede a la operación (policy-first).
    
    Ejemplos:
      - "max_tenants_per_first_tier = 5"
      - "qr_vigencia_dias = 7"
      - "max_usuarios_por_tenant = 100"
    
    Pregunta que responde: "¿Bajo qué límites puedo actuar?"
    """
    __tablename__ = "policies_gov"
    
    # Identificador único
    policy_id = Column(String, primary_key=True, index=True)
    
    # Nombre de la política (qr_vigencia_dias, max_tenants, max_usuarios)
    nombre = Column(String, nullable=False, index=True)
    
    # Descripción legible
    descripcion = Column(Text, nullable=True)
    
    # Ámbito de aplicación (GLOBAL o TENANT)
    ambito = Column(SQLEnum(PolicyScope), nullable=False, index=True)
    
    # Tenant al que aplica (NULL si GLOBAL)
    target_tenant_id = Column(String, nullable=True, index=True)
    
    # Acción objetivo (generar_qr, crear_tenant, asignar_scope)
    accion_objetivo = Column(String, nullable=False, index=True)
    
    # Límites estructurales (JSON)
    # Ejemplos: {"max_count": 10}, {"max_dias_vigencia": 7}, {"max_usuarios": 100}
    limites = Column(JSON, nullable=False)
    
    # Vigencia
    valida_desde = Column(DateTime, default=datetime.utcnow, nullable=False)
    valida_hasta = Column(DateTime, nullable=True)
    
    # Estado
    estado = Column(SQLEnum(GovStatus), nullable=False, default=GovStatus.ACTIVO)
    
    # Metadata adicional
    metadata_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_policy_ambito', 'ambito', 'accion_objetivo', 'estado'),
        Index('idx_policy_tenant', 'target_tenant_id', 'estado'),
    )


# ═══════════════════════════════════════════════════════════════════════════
# DELEGATION (AUP_DELEGATION)
# ═══════════════════════════════════════════════════════════════════════════

class Delegation(Base_GOV):
    """
    AUP_DELEGATION: Transferencia explícita de poder desde autoridad a identidades/scopes.
    
    Axiomas:
      1. Todo poder delegado es explícito
      2. Todo poder delegado es acotado (tiempo/alcance)
      3. Todo poder delegado es revocable
    
    Ejemplo:
      - Authority GLOBAL delega "crear_tenant" a usuario X hasta fecha Y
    """
    __tablename__ = "delegations_gov"
    
    # Identificador único
    delegation_id = Column(String, primary_key=True, index=True)
    
    # AUP_AUTHORITY que delega
    authority_id = Column(String, ForeignKey("authorities_gov.authority_id"), nullable=False, index=True)
    
    # A QUIÉN se delega (mutuamente excluyente)
    # Puede ser a una identidad directa (referencia a aup_core.usuarios)
    target_identity_id = Column(String, nullable=True, index=True)
    # O a un scope (referencia a aup_core.user_tenant_scope)
    target_scope_id = Column(String, nullable=True, index=True)
    
    # QUÉ se delega (array de acciones: ["crear_tenant", "asignar_scope"])
    permisos_delegados = Column(JSON, nullable=False)
    
    # Vigencia
    valida_desde = Column(DateTime, default=datetime.utcnow, nullable=False)
    valida_hasta = Column(DateTime, nullable=True)
    
    # Estado
    estado = Column(SQLEnum(GovStatus), nullable=False, default=GovStatus.ACTIVO)
    
    # Metadata adicional
    metadata_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_delegation_authority', 'authority_id', 'estado'),
        Index('idx_delegation_target_identity', 'target_identity_id', 'estado'),
        Index('idx_delegation_target_scope', 'target_scope_id', 'estado'),
    )
