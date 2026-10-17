"""
AUP_CORE — Modelos de Identidad y Alcance

Responsabilidad: Declarar existencia de identidades y sus alcances operativos.

Contiene:
- Usuario (AUP_IDENTITY)
- MSP (proveedor de servicios)
- Condominio (AUP_TENANT)
- UserTenantScope (AUP_SCOPE)
- Caseta (infraestructura operativa)
- Visita (entidad de negocio)
- Evidencia (artefactos de operación)
"""

from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint, Index
from datetime import datetime
import enum

from .engine import Base_CORE


class AlexaAccount(Base_CORE):
    """Control-plane: signed Amazon account events can precede tenant linkage.

    No visitor data or OAuth tokens. Tenant/house bindings are snapshots,
    reauthorized against current Usuario and AUP_SCOPE on every use.
    """
    __tablename__ = "alexa_accounts"
    __table_args__ = (CheckConstraint(
        "(usuario_id IS NULL AND condominio_id IS NULL AND casa_id IS NULL AND linked_at IS NULL) OR "
        "(usuario_id IS NOT NULL AND condominio_id IS NOT NULL AND casa_id IS NOT NULL AND linked_at IS NOT NULL)",
        name="alexa_complete_binding"),)
    account_key = Column(String(64), primary_key=True)
    amazon_user_id = Column(String(1024), unique=True, nullable=False)
    usuario_id = Column(String, ForeignKey("usuarios.usuario_id"), index=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"), index=True)
    casa_id = Column(String, ForeignKey("casas.casa_id"))
    linked_at = Column(DateTime)
    disabled_at = Column(DateTime)
    permission_at = Column(DateTime)
    permission_granted = Column(Boolean, nullable=False, default=False)
    subscription_at = Column(DateTime)
    subscribed = Column(Boolean, nullable=False, default=False)


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS
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
    MSP_ADMIN = "msp_admin"
    ADMIN_CONDOMINIO = "admin_condominio"
    GUARDIA = "guardia"
    RESIDENTE = "residente"
    LECTURA = "lectura"


# ═══════════════════════════════════════════════════════════════════════════
# MSP (Proveedor de Servicios)
# ═══════════════════════════════════════════════════════════════════════════

class MSP(Base_CORE):
    """Proveedor de servicios de seguridad."""
    __tablename__ = "msps_exo"
    
    id = Column(Integer, primary_key=True, index=True)
    msp_id = Column(String, unique=True, index=True)
    nombre = Column(String)


# ═══════════════════════════════════════════════════════════════════════════
# CONDOMINIO (AUP_TENANT)
# ═══════════════════════════════════════════════════════════════════════════

class Condominio(Base_CORE):
    """
    AUP_TENANT: Contexto de aislamiento operativo.
    Cada condominio es un tenant independiente.
    """
    __tablename__ = "condominios_exo"
    
    id = Column(Integer, primary_key=True, index=True)
    condominio_id = Column(String, unique=True, index=True)
    msp_id = Column(String, ForeignKey("msps_exo.msp_id"))
    nombre = Column(String)
    reglas_acceso = Column(JSON, nullable=True)


class ProviderContract(Base_CORE):
    """Control-plane contract history; mutations serialize on the condominium."""
    __tablename__ = "provider_contracts"
    contract_id = Column(String, primary_key=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=False)
    msp_id = Column(String, ForeignKey("msps_exo.msp_id"), nullable=False)
    version = Column(Integer, nullable=False)
    evidence_ref = Column(String, nullable=False)
    opened_by = Column(String, nullable=False)
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime)
    open_event_uid = Column(String, nullable=False)
    close_event_uid = Column(String)
    close_receipt = Column(JSON)
    __table_args__ = (
        UniqueConstraint("condominio_id", "version", name="uq_provider_contract_version"),
        Index("uq_provider_contract_active", "condominio_id", unique=True,
              postgresql_where=closed_at.is_(None), sqlite_where=closed_at.is_(None)),
    )



# ═══════════════════════════════════════════════════════════════════════════
# CASA (Unidad dentro de un condominio)
# ═══════════════════════════════════════════════════════════════════════════

class Casa(Base_CORE):
    """Unidad habitacional dentro de un condominio (casa, depto, local)."""
    __tablename__ = "casas"

    id = Column(Integer, primary_key=True, index=True)
    casa_id = Column(String, unique=True, index=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=False)
    numero = Column(String, nullable=False)          # "A-12", "101", "Local 3"
    tipo = Column(String, default="casa")            # casa / depto / local
    descripcion = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# USUARIO (AUP_IDENTITY)
# ═══════════════════════════════════════════════════════════════════════════

class Usuario(Base_CORE):
    """
    AUP_IDENTITY: Entidad que puede autenticarse y operar en el sistema.
    Requiere AUP_SCOPE válido para actuar en un tenant.
    """
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(String, unique=True, index=True)
    clerk_id = Column(String, unique=True, index=True, nullable=True)  # Clerk user_id
    msp_id = Column(String)
    condominio_id = Column(String)  # Tenant principal (legacy, usar scope)
    casa_id = Column(String, ForeignKey("casas.casa_id"), nullable=True)
    casa_unidad = Column(String)    # Denormalizado de casa.numero (compat legado)
    nombre = Column(String)
    email = Column(String, unique=True, index=True)
    rol = Column(String)  # MSP_ADMIN, ADMIN_CONDOMINIO, GUARDIA, RESIDENTE
    password_hash = Column(Text, nullable=True)  # Nullable para usuarios Clerk
    creado = Column(DateTime, default=datetime.utcnow)


class MSPMembership(Base_CORE):
    """Membresía explícita del administrador en un proveedor de seguridad."""
    __tablename__ = "msp_memberships"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(String, ForeignKey("usuarios.usuario_id"), nullable=False, index=True)
    msp_id = Column(String, ForeignKey("msps_exo.msp_id"), nullable=False, index=True)
    estado = Column(String, nullable=False, default="activo")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("usuario_id", "msp_id", name="uq_msp_membership"),)


# ═══════════════════════════════════════════════════════════════════════════
# USER_TENANT_SCOPE (AUP_SCOPE)
# ═══════════════════════════════════════════════════════════════════════════

class UserTenantScope(Base_CORE):
    """
    AUP_SCOPE: Materialización explícita del alcance de una identidad sobre un tenant.
    
    Axiomas:
      1. Una identidad sin scope válido no existe operativamente en el tenant
      2. El scope NO se serializa en JWT (es dinámico)
      3. El sistema NO infiere alcance, lo VALIDA
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
    
    # Nivel de acceso (DÓNDE puede actuar)
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
    
    # Metadatos adicionales
    metadata_json = Column(JSON, nullable=True)


# ═══════════════════════════════════════════════════════════════════════════
# CASETA (Infraestructura)
# ═══════════════════════════════════════════════════════════════════════════

class Caseta(Base_CORE):
    """Punto de control de acceso físico en un condominio."""
    __tablename__ = "casetas"
    
    id = Column(Integer, primary_key=True, index=True)
    caseta_id = Column(String, unique=True, index=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"))
    nombre = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# VISITA (Entidad de Negocio)
# ═══════════════════════════════════════════════════════════════════════════

class Visita(Base_CORE):
    """Registro de visita autorizada a un condominio."""
    __tablename__ = "visitas"
    
    id = Column(Integer, primary_key=True, index=True)
    visita_id = Column(String, unique=True, index=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"))
    nombre_visitante = Column(String)
    proposito = Column(Text, nullable=True)
    autorizada_por = Column(String, ForeignKey("usuarios.usuario_id"), nullable=True)
    autorizada_en = Column(DateTime, nullable=True)
    destino_id = Column(String, ForeignKey("casas.casa_id"), nullable=True)
    destino_tipo = Column(String, nullable=True)
    destino_motivo = Column(Text, nullable=True)
    casa_unidad = Column(String)
    tipo_visita = Column(String)  # frecuente, eventual, proveedor
    vigencia = Column(DateTime)
    solicitud_remota_id = Column(String, nullable=True)
    autorizacion_remota_hasta = Column(DateTime, nullable=True)
    qr_token = Column(String, unique=True, nullable=True)
    qr_vigencia = Column(DateTime, nullable=True)
    estado = Column(String, default="pendiente")  # pendiente, activa, completada, cancelada
    entrada_registrada_en = Column(DateTime, nullable=True)
    salida_registrada_en = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# EVIDENCIA (Artefactos)
# ═══════════════════════════════════════════════════════════════════════════

class Evidencia(Base_CORE):
    """Evidencia fotográfica de entrada/salida de visitas."""
    __tablename__ = "evidencias"
    
    id = Column(Integer, primary_key=True, index=True)
    evidencia_id = Column(String, unique=True, index=True)
    visita_id = Column(String, ForeignKey("visitas.visita_id"), index=True)
    categoria = Column(String)  # entrada / salida
    sub_tipo = Column(String)   # visitante, ine_frente, ine_reverso, placas, vehiculo, documento
    archivo_url = Column(Text)
    hash_sha256 = Column(Text)
    guardia_id = Column(String, ForeignKey("usuarios.usuario_id"))
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EventOutbox(Base_CORE):
    """Evento capturado en la transacción CORE; el envío a EVENT es reintentable."""
    __tablename__ = "event_outbox"
    event_uid = Column(String, primary_key=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_error = Column(String, nullable=True)
    __table_args__ = (Index("ix_event_outbox_pending", "condominio_id", "delivered_at", "next_attempt_at"),)


class SecurityOutbox(Base_CORE):
    """Auditoría global de sesión/alcance: deliberadamente sin FK de condominio."""
    __tablename__ = "security_outbox"
    event_uid = Column(String, primary_key=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_error = Column(String, nullable=True)
    __table_args__ = (Index("ix_security_outbox_pending", "delivered_at", "next_attempt_at"),)


class IdentityRetention(Base_CORE):
    """One durable lifecycle per immutable ID pair; private references stay server-side."""
    __tablename__ = "identity_retention"
    visita_id = Column(String, ForeignKey("visitas.visita_id"), primary_key=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=False)
    captura_id = Column(String, nullable=False)
    policy_version = Column(String, nullable=False)
    captured_at = Column(DateTime, nullable=False)
    base_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    state = Column(String, nullable=False, default="active")
    hold_until = Column(DateTime)
    hold_owner = Column(String)
    hold_incident = Column(String)
    hold_reason = Column(String)
    snapshots = Column(JSON, nullable=False)
    audit_context = Column(JSON, nullable=False)
    operation_id = Column(String)
    claim_token = Column(String)
    claim_until = Column(DateTime)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False)
    last_error = Column(String)
    purged_at = Column(DateTime)
    event_uid = Column(String)
    __table_args__ = (Index("ix_identity_retention_due", "condominio_id", "state", "next_attempt_at"),)


class RecoveryCheckpoint(Base_CORE):
    """Recovery audit/checkpoint; incident identifier comes from deployment config."""
    __tablename__ = 'recovery_checkpoints'
    incident_id = Column(String, primary_key=True)
    phase = Column(String, nullable=False, default='locked')
    release_nonce = Column(String, nullable=True)
    report = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SolicitudAcceso(Base_CORE):
    """Durable resident inbox; authorization never represents physical entry."""
    __tablename__ = "solicitudes_acceso"
    solicitud_id = Column(String, primary_key=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"), nullable=False, index=True)
    visita_id = Column(String, ForeignKey("visitas.visita_id"), nullable=False, index=True)
    destino_id = Column(String, ForeignKey("casas.casa_id"), nullable=False)
    solicitada_por = Column(String, ForeignKey("usuarios.usuario_id"), nullable=False)
    destinatarios = Column(JSON, nullable=False)
    fingerprint = Column(String, nullable=False)
    estado = Column(String, nullable=False, default="pendiente")
    creada_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    expira_en = Column(DateTime, nullable=False)
    respondida_por = Column(String, ForeignKey("usuarios.usuario_id"), nullable=True)
    respondida_en = Column(DateTime, nullable=True)
    consentimiento_en = Column(DateTime, nullable=True)
