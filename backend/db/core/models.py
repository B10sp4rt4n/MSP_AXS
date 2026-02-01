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

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum, Index
from datetime import datetime
import enum

from .engine import Base_CORE


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
    msp_id = Column(String)
    condominio_id = Column(String)  # Tenant principal (legacy, usar scope)
    casa_unidad = Column(String)
    nombre = Column(String)
    email = Column(String, unique=True, index=True)
    rol = Column(String)  # MSP_ADMIN, ADMIN_CONDOMINIO, GUARDIA, RESIDENTE
    password_hash = Column(Text)
    creado = Column(DateTime, default=datetime.utcnow)


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
    telefono = Column(String, nullable=True)  # Nuevo: teléfono visitante
    casa_unidad = Column(String)
    residente_anfitrion = Column(String, nullable=True)  # Nuevo: residente anfitrión
    tipo_visitante = Column(String)  # frecuente, eventual, proveedor, cliente, entrega, consulta, familia
    motivo = Column(String, nullable=True)  # Nuevo: motivo de visita
    placa_vehiculo = Column(String, nullable=True)  # Nuevo: placa vehículo
    vigencia = Column(DateTime, nullable=True)  # Permitir NULL
    qr_token = Column(String, unique=True, nullable=True)
    qr_vigencia = Column(DateTime, nullable=True)
    estado = Column(String, default="creada_sin_qr")  # creada_sin_qr, entrada_registrada, salida_registrada
    hora_entrada = Column(DateTime, nullable=True)  # Nuevo: hora de entrada registrada
    hora_salida = Column(DateTime, nullable=True)  # Nuevo: hora de salida registrada
    entrada_registrada_en = Column(DateTime, nullable=True)
    salida_registrada_en = Column(DateTime, nullable=True)
    creada_por = Column(String, ForeignKey("usuarios.usuario_id"), nullable=True)  # Nuevo: guardia que creó
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_visita_estado", "estado"),
        Index("idx_visita_condominio_fecha", "condominio_id", "created_at"),
    )


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


# ═══════════════════════════════════════════════════════════════════════════
# QR_CODE (Códigos alfanuméricos)
# ═══════════════════════════════════════════════════════════════════════════

class QRCode(Base_CORE):
    """
    Códigos QR alfanuméricos para compartir acceso
    Permite validar acceso por código sin escanear QR
    """
    __tablename__ = "qr_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)  # V-260201-123
    visita_id = Column(String, ForeignKey("visitas.visita_id"), index=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"))
    
    # Vigencia
    vigencia_desde = Column(DateTime, default=datetime.utcnow)
    vigencia_hasta = Column(DateTime)
    
    # Estado
    usado = Column(Integer, default=0)  # 0=no usado, 1=usado
    usado_en = Column(DateTime, nullable=True)
    
    # Auditoría de compartición
    compartido_via = Column(String, nullable=True)  # whatsapp, sms, email, pantalla
    compartido_a = Column(String, nullable=True)   # teléfono/email destinatario
    compartido_por = Column(String, ForeignKey("usuarios.usuario_id"), nullable=True)
    compartido_en = Column(DateTime, nullable=True)
    
    # Metadata
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_qrcode_vigencia", "vigencia_hasta"),
        Index("idx_qrcode_visita", "visita_id"),
        Index("idx_qrcode_usado", "usado"),
    )
