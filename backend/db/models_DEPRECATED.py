from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from datetime import datetime
from .connection import Base
import enum


# ═══════════════════════════════════════════════════════════════════════════
# AUP_SCOPE - Enums de Estado
# ═══════════════════════════════════════════════════════════════════════════

class ScopeStatus(str, enum.Enum):
    """Estados posibles de AUP_SCOPE"""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    REVOCADO = "revocado"


class AccessLevel(str, enum.Enum):
    """
    Niveles de acceso en AUP_SCOPE.
    Define DÓNDE una identidad puede actuar, no QUÉ puede hacer.
    """
    MSP_ADMIN = "msp_admin"              # Acceso a nivel MSP
    ADMIN_CONDOMINIO = "admin_condominio"  # Administrador del tenant
    GUARDIA = "guardia"                   # Personal de seguridad del tenant
    RESIDENTE = "residente"               # Residente del tenant
    LECTURA = "lectura"                   # Solo lectura (auditoría, reportes)


# ═══════════════════════════════════════════════════════════════════════════
# Modelos Existentes
# ═══════════════════════════════════════════════════════════════════════════


class MSP(Base):
    __tablename__ = "msps_exo"
    id = Column(Integer, primary_key=True, index=True)
    msp_id = Column(String, unique=True, index=True)
    nombre = Column(String)


class Condominio(Base):
    __tablename__ = "condominios_exo"
    id = Column(Integer, primary_key=True, index=True)
    condominio_id = Column(String, unique=True, index=True)
    msp_id = Column(String, ForeignKey("msps_exo.msp_id"))
    nombre = Column(String)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(String, unique=True, index=True)
    msp_id = Column(String)
    condominio_id = Column(String)
    casa_unidad = Column(String)
    nombre = Column(String)
    email = Column(String)
    rol = Column(String)  # MSP_ADMIN, ADMIN_CONDOMINIO, GUARDIA, RESIDENTE
    password_hash = Column(Text)
    creado = Column(DateTime, default=datetime.utcnow)


class Caseta(Base):
    __tablename__ = "casetas"
    id = Column(Integer, primary_key=True, index=True)
    caseta_id = Column(String, unique=True, index=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"))
    nombre = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Visita(Base):
    __tablename__ = "visitas"
    id = Column(Integer, primary_key=True, index=True)
    visita_id = Column(String, unique=True, index=True)
    condominio_id = Column(String)
    nombre_visitante = Column(String)
    casa_unidad = Column(String)
    tipo_visita = Column(String)
    vigencia = Column(DateTime)
    qr_token = Column(String)
    qr_vigencia = Column(DateTime)
    estado = Column(String, default="pendiente")
    entrada_registrada_en = Column(DateTime)
    salida_registrada_en = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Evidencia(Base):
    __tablename__ = "evidencias"
    id = Column(Integer, primary_key=True, index=True)
    evidencia_id = Column(String, unique=True, index=True)
    visita_id = Column(String, index=True)
    categoria = Column(String)          # entrada / salida
    sub_tipo = Column(String)           # visitante, ine_frente, ine_reverso, placas, vehiculo, documento, foto_salida
    archivo_url = Column(Text)
    hash_sha256 = Column(Text)
    guardia_id = Column(String)
    # Use SQLAlchemy JSON type (works with Postgres JSON/JSONB and falls back on Text for SQLite)
    # JSONB (postgres-only) removed to keep local compatibility with SQLite.
    # If production requires JSONB-specific features, ensure migrations use that type.
    metadata_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# AUP_SCOPE - Modelo Relacional de Alcance
# ═══════════════════════════════════════════════════════════════════════════

class UserTenantScope(Base):
    """
    Materialización de AUP_SCOPE.
    
    DECLARACIÓN AUP:
      Entidad relacional viva que declara explícitamente el alcance
      permitido de una AUP_IDENTITY sobre un AUP_TENANT.
    
    AXIOMAS APLICADOS:
      1. Una AUP_IDENTITY sin scope válido no existe operativamente en el tenant
      2. El scope NO se serializa en JWT (es dinámico)
      3. El sistema NO infiere alcance, lo VALIDA
    
    RELACIÓN:
      AUP_IDENTITY -tiene→ AUP_SCOPE -sobre→ AUP_TENANT
    
    CASOS DE USO:
      - First Tier: Una identidad puede tener múltiples scopes (múltiples tenants)
      - Revocación: Invalidar acceso a un tenant sin afectar otros
      - Auditoría: Histórico de quién tuvo acceso a qué tenant
    """
    __tablename__ = "user_tenant_scope"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # AUP_IDENTITY que posee este scope
    usuario_id = Column(
        String,
        ForeignKey("usuarios.usuario_id"),
        nullable=False,
        index=True
    )
    
    # AUP_TENANT sobre el que aplica este scope
    tenant_id = Column(
        String,
        ForeignKey("condominios_exo.condominio_id"),
        nullable=False,
        index=True
    )
    
    # Nivel de acceso (DÓNDE puede actuar, no QUÉ puede hacer)
    access_level = Column(
        SQLEnum(AccessLevel),
        nullable=False
    )
    
    # Estado del scope
    estado = Column(
        SQLEnum(ScopeStatus),
        nullable=False,
        default=ScopeStatus.ACTIVO
    )
    
    # Timestamps de auditoría
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    
    # Metadatos adicionales (futuro: vigencia temporal, delegación, etc.)
    metadata_json = Column(JSON, nullable=True)
    
    # Índice compuesto para búsquedas eficientes
    # (usuario_id, tenant_id) debe ser único por combinación activa
    __table_args__ = (
        # Index para búsqueda rápida: ¿tiene scope este usuario en este tenant?
        # Index('idx_user_tenant', 'usuario_id', 'tenant_id'),
    )


# ═══════════════════════════════════════════════════════════════════════════
# AUP_EVENT - Declaración de Hechos Estructurales
# ═══════════════════════════════════════════════════════════════════════════

class Event(Base):
    """
    Entidad estructural universal que declara que un HECHO ocurrió dentro del
    sistema, con identidad, contexto, alcance y resultado verificables.
    
    AUP_EVENT NO ES logging técnico. ES una entidad de dominio inmutable que
    declara existencia en el tiempo.
    
    Axiomas:
    1. Toda acción relevante genera al menos un AUP_EVENT
    2. AUP_EVENT sin identidad/tenant es estructuralmente inválido
    3. AUP_EVENT es inmutable (no se edita, solo se agrega)
    4. Estado del sistema se puede reconstruir desde eventos
    5. Si no hay evento, no ocurrió para el sistema
    """
    __tablename__ = "events_aup"
    
    # Identificador único del evento
    event_id = Column(String, primary_key=True, index=True)
    
    # -------------------------------------------------------------------------
    # Contexto AUP (QUIÉN, DÓNDE, CÓMO)
    # -------------------------------------------------------------------------
    
    # AUP_IDENTITY: Quién actúa
    identity_id = Column(String, ForeignKey("usuarios_exo.usuario_id"), nullable=False, index=True)
    
    # AUP_SESSION: Contexto temporal (hash del JWT)
    session_hash = Column(String, nullable=False, index=True)
    
    # AUP_SCOPE: Alcance sobre tenant (puede ser NULL en login)
    scope_id = Column(String, ForeignKey("user_tenant_scope.id"), nullable=True, index=True)
    
    # AUP_TENANT: Dónde ocurre
    tenant_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=False, index=True)
    
    # -------------------------------------------------------------------------
    # Declaración del Hecho (QUÉ, RESULTADO)
    # -------------------------------------------------------------------------
    
    # Entidad afectada (visita, qr, evidencia, usuario, condominio, scope)
    entidad = Column(String, nullable=False, index=True)
    
    # ID específico de la entidad
    entidad_id = Column(String, nullable=False, index=True)
    
    # Acción ejecutada (crear, validar, registrar, revocar, denegar)
    accion = Column(String, nullable=False, index=True)
    
    # Resultado de la acción (permitido, denegado, error, exito, fallo)
    resultado = Column(String, nullable=False, index=True)
    
    # Motivo estructural (por qué ocurrió o falló)
    motivo = Column(Text, nullable=True)
    
    # -------------------------------------------------------------------------
    # Metadatos y Trazabilidad
    # -------------------------------------------------------------------------
    
    # Timestamp inmutable
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Hash de inmutabilidad (calculado desde campos críticos)
    hash_evento = Column(String, nullable=False, unique=True)
    
    # Metadata adicional estructurada
    metadata_json = Column(JSON, nullable=True)
    
    # Índices compuestos para queries comunes
    __table_args__ = (
        # Query: "¿Qué hizo este usuario en este tenant?"
        # Index('idx_identity_tenant', 'identity_id', 'tenant_id', 'timestamp'),
        
        # Query: "¿Qué eventos afectaron esta entidad?"
        # Index('idx_entidad', 'entidad', 'entidad_id', 'timestamp'),
        
        # Query: "¿Qué eventos fallaron/fueron denegados?"
        # Index('idx_resultado', 'resultado', 'timestamp'),
    )


# ═══════════════════════════════════════════════════════════════════════════
# AUP_GOV - Gobierno de Plataforma
# ═══════════════════════════════════════════════════════════════════════════

class AuthorityType(str, enum.Enum):
    """Tipos de autoridad de gobierno"""
    GLOBAL = "global"           # Poder sobre toda la plataforma
    FIRST_TIER = "first_tier"   # Poder sobre tenant específico


class PolicyScope(str, enum.Enum):
    """Ámbito de aplicación de política"""
    GLOBAL = "global"           # Aplica a toda la plataforma
    TENANT = "tenant"           # Aplica a tenant específico
    SCOPE = "scope"             # Aplica a scopes con nivel específico


class GovStatus(str, enum.Enum):
    """Estado de entidades de gobierno"""
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    REVOCADO = "revocado"


class Authority(Base):
    """
    AUP_AUTHORITY: Actor con potestad declarada para gobernar.
    
    Axioma: Solo AUP_AUTHORITY puede crear o delegar poder.
    
    Tipos:
      - GLOBAL: Autoridad sobre toda la plataforma
      - FIRST_TIER: Autoridad sobre un tenant específico (dueño)
    """
    __tablename__ = "authorities_gov"
    
    # Identificador único
    authority_id = Column(String, primary_key=True, index=True)
    
    # AUP_IDENTITY que tiene la autoridad
    identity_id = Column(String, ForeignKey("usuarios_exo.usuario_id"), nullable=False, index=True)
    
    # Tipo de autoridad
    tipo = Column(SQLEnum(AuthorityType), nullable=False, index=True)
    
    # Tenant sobre el que tiene autoridad (NULL si GLOBAL)
    tenant_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=True, index=True)
    
    # Estado
    estado = Column(SQLEnum(GovStatus), nullable=False, default=GovStatus.ACTIVO)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Metadata adicional
    metadata_json = Column(JSON, nullable=True)
    
    # Índices
    __table_args__ = (
        # Index('idx_authority_identity', 'identity_id', 'estado'),
        # Index('idx_authority_tenant', 'tenant_id', 'estado'),
    )


class Policy(Base):
    """
    AUP_POLICY: Regla declarativa que gobierna límites y delegaciones.
    
    Axioma: La política precede a la operación (policy-first).
    
    Ejemplos:
      - "max_tenants_per_first_tier = 5"
      - "max_qr_vigencia_dias = 7"
      - "max_usuarios_por_tenant = 100"
    """
    __tablename__ = "policies_gov"
    
    # Identificador único
    policy_id = Column(String, primary_key=True, index=True)
    
    # Nombre declarativo
    nombre = Column(String, nullable=False)
    
    # Ámbito de aplicación
    ambito = Column(SQLEnum(PolicyScope), nullable=False, index=True)
    
    # Tenant objetivo (NULL si GLOBAL)
    target_tenant_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=True, index=True)
    
    # Acción que gobierna (crear_tenant, asignar_scope, generar_qr, etc.)
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
    
    # Índices
    __table_args__ = (
        # Index('idx_policy_ambito', 'ambito', 'accion_objetivo', 'estado'),
        # Index('idx_policy_tenant', 'target_tenant_id', 'estado'),
    )


class Delegation(Base):
    """
    AUP_DELEGATION: Relación que transfiere poder desde autoridad a identidades/scopes.
    
    Axiomas:
      1. Todo poder delegado es explícito
      2. Todo poder delegado es acotado (tiempo/alcance)
      3. Todo poder delegado es revocable
    """
    __tablename__ = "delegations_gov"
    
    # Identificador único
    delegation_id = Column(String, primary_key=True, index=True)
    
    # AUP_AUTHORITY que delega
    authority_id = Column(String, ForeignKey("authorities_gov.authority_id"), nullable=False, index=True)
    
    # A QUIÉN se delega (mutuamente excluyente)
    target_identity_id = Column(String, ForeignKey("usuarios_exo.usuario_id"), nullable=True, index=True)
    target_scope_id = Column(String, ForeignKey("user_tenant_scope.id"), nullable=True, index=True)
    
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
    
    # Índices
    __table_args__ = (
        # Index('idx_delegation_authority', 'authority_id', 'estado'),
        # Index('idx_delegation_target_identity', 'target_identity_id', 'estado'),
        # Index('idx_delegation_target_scope', 'target_scope_id', 'estado'),
    )

