"""
═══════════════════════════════════════════════════════════════════════════════
Registro Central de AUP_EVENT
═══════════════════════════════════════════════════════════════════════════════

Función estructural universal que declara hechos en el sistema.

NO contiene lógica de negocio.
SÍ declara existencia verificable.
"""

import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.db.models import Event, Usuario
from backend.core.event import EventEntity, EventAction, EventResult


def calcular_hash_evento(
    event_id: str,
    identity_id: str,
    session_hash: str,
    tenant_id: str,
    entidad: str,
    entidad_id: str,
    accion: str,
    resultado: str,
    timestamp: datetime
) -> str:
    """
    Calcula hash SHA-256 de campos críticos del evento.
    
    Propósito: Verificar inmutabilidad del evento.
    
    Si el hash no coincide con el calculado desde campos actuales,
    el evento fue alterado (violación de axioma de inmutabilidad).
    
    Args:
        Todos los campos críticos del evento
    
    Returns:
        Hash SHA-256 hexadecimal (64 caracteres)
    """
    # Concatenar campos críticos en orden determinístico
    contenido = "|".join([
        event_id,
        identity_id,
        session_hash,
        tenant_id,
        entidad,
        entidad_id,
        accion,
        resultado,
        timestamp.isoformat()
    ])
    
    # Calcular SHA-256
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()


def hash_session_token(token: str) -> str:
    """
    Hash del JWT completo para trazabilidad sin exponer token.
    
    Args:
        token: JWT completo (Bearer <token>)
    
    Returns:
        SHA-256 del token (primeros 16 caracteres)
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]


def registrar_evento(
    db: Session,
    identity: Usuario,
    session_token: str,
    tenant_id: str,
    entidad: str,
    entidad_id: str,
    accion: str,
    resultado: str,
    scope_id: Optional[str] = None,
    motivo: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Event:
    """
    Función estructural central que declara un hecho en el sistema.
    
    Pregunta que responde:
      "¿Qué hecho estructural acaba de ocurrir y quién/dónde/cómo?"
    
    NO pregunta:
      - ¿Debo permitir esto? (eso es validación)
      - ¿Qué significa esto? (eso es lógica de negocio)
    
    SÍ declara:
      - Este hecho ocurrió
      - Con esta identidad
      - En este tenant
      - Con este resultado
      - En este momento
      - Con esta huella verificable
    
    Axiomas aplicados:
      1. Toda acción relevante genera AUP_EVENT ✓
      2. Sin identidad/tenant = inválido ✓
      3. Evento es inmutable ✓
      4. Hash para verificación ✓
    
    Args:
        db: Sesión de BD
        identity: AUP_IDENTITY (Usuario)
        session_token: JWT completo para hash
        tenant_id: AUP_TENANT donde ocurre
        entidad: Tipo de entidad afectada (visita, qr, evidencia, etc.)
        entidad_id: ID específico de la entidad
        accion: Acción ejecutada (crear, validar, denegar, etc.)
        resultado: Resultado de la acción (permitido, denegado, error, etc.)
        scope_id: AUP_SCOPE (puede ser None en login)
        motivo: Razón estructural del resultado
        metadata: Contexto adicional estructurado
    
    Returns:
        Event: Entidad AUP_EVENT creada e insertada en BD
    
    Raises:
        ValueError: Si faltan campos obligatorios (identidad, tenant)
    """
    # -------------------------------------------------------------------------
    # Validación Estructural (Axioma 3: sin identidad/tenant = inválido)
    # -------------------------------------------------------------------------
    
    if not identity or not identity.usuario_id:
        raise ValueError("AUP_EVENT sin identidad es estructuralmente inválido")
    
    if not tenant_id:
        raise ValueError("AUP_EVENT sin tenant es estructuralmente inválido")
    
    # -------------------------------------------------------------------------
    # Generación de Identificadores
    # -------------------------------------------------------------------------
    
    event_id = f"evt_{uuid.uuid4().hex[:16]}"
    timestamp = datetime.utcnow()
    session_hash = hash_session_token(session_token)
    
    # -------------------------------------------------------------------------
    # Cálculo de Hash de Inmutabilidad (Axioma 2)
    # -------------------------------------------------------------------------
    
    hash_evento = calcular_hash_evento(
        event_id=event_id,
        identity_id=identity.usuario_id,
        session_hash=session_hash,
        tenant_id=tenant_id,
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        resultado=resultado,
        timestamp=timestamp
    )
    
    # -------------------------------------------------------------------------
    # Creación de Entidad AUP_EVENT
    # -------------------------------------------------------------------------
    
    evento = Event(
        event_id=event_id,
        identity_id=identity.usuario_id,
        session_hash=session_hash,
        scope_id=scope_id,
        tenant_id=tenant_id,
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        resultado=resultado,
        motivo=motivo,
        timestamp=timestamp,
        hash_evento=hash_evento,
        metadata=metadata
    )
    
    # -------------------------------------------------------------------------
    # Persistencia (Inmutable)
    # -------------------------------------------------------------------------
    
    db.add(evento)
    db.commit()
    db.refresh(evento)
    
    return evento


def verificar_integridad_evento(evento: Event) -> bool:
    """
    Verifica que el evento no haya sido alterado.
    
    Calcula el hash desde los campos actuales y lo compara con hash_evento.
    
    Args:
        evento: Evento a verificar
    
    Returns:
        True si el hash coincide (evento íntegro)
        False si el hash no coincide (evento alterado)
    """
    hash_calculado = calcular_hash_evento(
        event_id=evento.event_id,
        identity_id=evento.identity_id,
        session_hash=evento.session_hash,
        tenant_id=evento.tenant_id,
        entidad=evento.entidad,
        entidad_id=evento.entidad_id,
        accion=evento.accion,
        resultado=evento.resultado,
        timestamp=evento.timestamp
    )
    
    return hash_calculado == evento.hash_evento


def obtener_eventos_entidad(
    db: Session,
    entidad: str,
    entidad_id: str
) -> list[Event]:
    """
    Obtiene todos los eventos que afectaron una entidad específica.
    
    Caso de uso: "¿Qué le pasó a esta visita?"
    
    Args:
        db: Sesión de BD
        entidad: Tipo de entidad (visita, qr, evidencia)
        entidad_id: ID de la entidad
    
    Returns:
        Lista de eventos ordenados cronológicamente
    """
    return (
        db.query(Event)
        .filter(Event.entidad == entidad, Event.entidad_id == entidad_id)
        .order_by(Event.timestamp.asc())
        .all()
    )


def obtener_eventos_usuario_en_tenant(
    db: Session,
    usuario_id: str,
    tenant_id: str,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None
) -> list[Event]:
    """
    Obtiene eventos de un usuario específico en un tenant.
    
    Caso de uso: Auditoría "¿Qué hizo Juan en Condominio A?"
    
    Args:
        db: Sesión de BD
        usuario_id: ID del usuario
        tenant_id: ID del tenant
        desde: Timestamp inicio (opcional)
        hasta: Timestamp fin (opcional)
    
    Returns:
        Lista de eventos ordenados cronológicamente
    """
    query = db.query(Event).filter(
        Event.identity_id == usuario_id,
        Event.tenant_id == tenant_id
    )
    
    if desde:
        query = query.filter(Event.timestamp >= desde)
    if hasta:
        query = query.filter(Event.timestamp <= hasta)
    
    return query.order_by(Event.timestamp.desc()).all()


def obtener_eventos_denegados(
    db: Session,
    tenant_id: Optional[str] = None,
    limit: int = 100
) -> list[Event]:
    """
    Obtiene eventos con resultado denegado (seguridad).
    
    Caso de uso: Detección de intentos no autorizados.
    
    Args:
        db: Sesión de BD
        tenant_id: Filtrar por tenant específico (opcional)
        limit: Máximo de eventos a retornar
    
    Returns:
        Lista de eventos denegados ordenados por timestamp desc
    """
    query = db.query(Event).filter(Event.resultado == EventResult.DENEGADO.value)
    
    if tenant_id:
        query = query.filter(Event.tenant_id == tenant_id)
    
    return query.order_by(Event.timestamp.desc()).limit(limit).all()


__all__ = [
    "registrar_evento",
    "verificar_integridad_evento",
    "obtener_eventos_entidad",
    "obtener_eventos_usuario_en_tenant",
    "obtener_eventos_denegados",
    "calcular_hash_evento",
    "hash_session_token",
]
