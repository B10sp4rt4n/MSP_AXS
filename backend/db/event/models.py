"""
AUP_EVENT — Modelo de Verdad Histórica

Responsabilidad: Registrar hechos inmutables con identidad, alcance y resultado.

Axiomas:
1. Append-only (solo INSERT, nunca UPDATE/DELETE)
2. Si no hay evento, no ocurrió para el sistema
3. Si hash cambia, hay manipulación detectable
4. Estado del sistema se puede reconstruir desde eventos

Contiene:
- Event (única tabla, todos los eventos del sistema)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index
from datetime import datetime

from .engine import Base_EVENT


# ═══════════════════════════════════════════════════════════════════════════
# EVENT (AUP_EVENT)
# ═══════════════════════════════════════════════════════════════════════════

class Event(Base_EVENT):
    """
    AUP_EVENT: Declaración inmutable de que un hecho ocurrió.
    
    NO ES logging técnico. ES una entidad de dominio que declara existencia en el tiempo.
    
    Axiomas aplicados:
    1. Toda acción relevante genera al menos un AUP_EVENT
    2. AUP_EVENT sin identidad/tenant es estructuralmente inválido
    3. AUP_EVENT es inmutable (no se edita, solo se agrega)
    4. Estado del sistema se puede reconstruir desde eventos
    5. Si no hay evento, no ocurrió para el sistema
    
    Pregunta que responde: "¿Qué ocurrió realmente?"
    """
    __tablename__ = "events_aup"
    
    # -------------------------------------------------------------------------
    # Identificación
    # -------------------------------------------------------------------------
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Tipo de evento (sesion_iniciada, qr_generado, visita_creada, politica_evaluada)
    tipo_evento = Column(String, nullable=False, index=True)
    
    # -------------------------------------------------------------------------
    # Contexto (QUIÉN, DÓNDE)
    # -------------------------------------------------------------------------
    
    # AUP_IDENTITY: Quién ejecutó la acción
    identity_id = Column(String, nullable=False, index=True)
    
    # AUP_TENANT: Dónde ocurre
    tenant_id = Column(String, nullable=False, index=True)
    
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
    
    # Hash de inmutabilidad (SHA-256 calculado desde campos críticos)
    hash_evento = Column(String, nullable=False, unique=True)
    
    # Metadata adicional estructurada
    metadata_json = Column(JSON, nullable=True)
    
    # -------------------------------------------------------------------------
    # Índices compuestos para queries forenses
    # -------------------------------------------------------------------------
    
    __table_args__ = (
        # Query: "¿Qué hizo este usuario en este tenant?"
        Index('idx_identity_tenant_time', 'identity_id', 'tenant_id', 'timestamp'),
        
        # Query: "¿Qué eventos afectaron esta entidad?"
        Index('idx_entidad_time', 'entidad', 'entidad_id', 'timestamp'),
        
        # Query: "¿Qué eventos fallaron/fueron denegados?"
        Index('idx_resultado_time', 'resultado', 'timestamp'),
        
        # Query: "¿Qué tipo de eventos ocurrieron hoy?"
        Index('idx_tipo_time', 'tipo_evento', 'timestamp'),
    )
