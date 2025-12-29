"""
═══════════════════════════════════════════════════════════════════════════════
DECLARACIÓN AUP: AUP_EVENT
═══════════════════════════════════════════════════════════════════════════════

Entidad estructural universal que declara que un HECHO ocurrió dentro del 
sistema, con identidad, contexto, alcance y resultado verificables.

AUP_EVENT NO ES:
  ❌ Logging técnico (print, logger.info)
  ❌ Auditoría clásica (quien-cuando-donde manual)
  ❌ Event Sourcing completo (reconstrucción total de estado)

AUP_EVENT ES:
  ✓ Entidad de dominio estructural
  ✓ Declaración de existencia en el tiempo
  ✓ Núcleo de trazabilidad universal
  ✓ Base para compliance y auditoría
  ✓ Inmutable por diseño

═══════════════════════════════════════════════════════════════════════════════
ESTRUCTURA CONCEPTUAL
═══════════════════════════════════════════════════════════════════════════════

AUP_EVENT {
    identity:   AUP_IDENTITY     # QUIÉN actúa
    session:    AUP_SESSION      # CONTEXTO temporal
    scope:      AUP_SCOPE        # ALCANCE sobre tenant
    tenant:     AUP_TENANT       # DÓNDE ocurre
    
    entidad:    ENTITY_TYPE      # QUÉ se afecta (visita, qr, evidencia)
    entidad_id: STRING           # Identificador específico
    accion:     ACTION_TYPE      # QUÉ se hace (crear, validar, denegar)
    resultado:  RESULT_TYPE      # RESULTADO (permitido, denegado, error)
    
    motivo:     STRING?          # POR QUÉ (opcional pero relevante)
    metadata:   JSON?            # Contexto adicional estructurado
    
    timestamp:  DATETIME         # CUÁNDO ocurrió
    hash:       STRING           # Huella de inmutabilidad
}

═══════════════════════════════════════════════════════════════════════════════
RELACIONES AUP
═══════════════════════════════════════════════════════════════════════════════

AUP_IDENTITY --genera→ AUP_EVENT
AUP_SESSION  --contexto→ AUP_EVENT
AUP_SCOPE    --alcance→ AUP_EVENT
AUP_TENANT   --contiene→ AUP_EVENT

AUP_EVENT --afecta→ ENTIDAD (Visita, QR, Evidencia, Usuario, Condominio)

═══════════════════════════════════════════════════════════════════════════════
AXIOMAS (NO NEGOCIABLES)
═══════════════════════════════════════════════════════════════════════════════

1. EXISTENCIA DECLARATIVA
   Si algo ocurre y no genera AUP_EVENT, no ocurrió para el sistema.

2. INMUTABILIDAD
   Un AUP_EVENT nunca se modifica. Solo se agregan nuevos eventos.

3. VALIDEZ ESTRUCTURAL
   Un AUP_EVENT sin identity, tenant o scope es estructuralmente inválido.
   Excepción: eventos de autenticación donde scope aún no existe.

4. RECONSTRUCCIÓN
   El estado del sistema puede reconstruirse a partir de eventos.

5. UNIVERSALIDAD
   Toda acción relevante (crear, validar, revocar, denegar) genera evento.

═══════════════════════════════════════════════════════════════════════════════
TIPOS ESTRUCTURALES
═══════════════════════════════════════════════════════════════════════════════

ENTITY_TYPE:
  - visita
  - qr
  - evidencia
  - usuario
  - condominio
  - scope
  - session

ACTION_TYPE:
  - crear
  - validar
  - registrar
  - revocar
  - denegar
  - modificar
  - eliminar
  - asignar

RESULT_TYPE:
  - permitido
  - denegado
  - error
  - exito
  - fallo

═══════════════════════════════════════════════════════════════════════════════
FUNCIÓN CENTRAL (Declaración)
═══════════════════════════════════════════════════════════════════════════════

registrar_evento(
    db: Session,
    identity: AUP_IDENTITY,
    session_token: str,           # JWT completo para hash
    scope_id: Optional[str],      # Puede ser None en login
    tenant_id: str,
    entidad: str,
    entidad_id: str,
    accion: str,
    resultado: str,
    motivo: Optional[str] = None,
    metadata: Optional[dict] = None
) -> AUP_EVENT

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

═══════════════════════════════════════════════════════════════════════════════
INTEGRACIÓN CON PASOS ANTERIORES
═══════════════════════════════════════════════════════════════════════════════

PASO 1: AUP_SESSION
  → Valida identidad (get_current_user)
  → AUP_EVENT registra intento de login

PASO 2: AUP_SCOPE
  → Valida alcance (validar_scope)
  → AUP_EVENT registra validación de scope

PASO 3: AUP_EVENT (ESTE PASO)
  → Declara el hecho que ocurrió
  → Crea trazabilidad completa

═══════════════════════════════════════════════════════════════════════════════
CASOS DE USO HABILITADOS
═══════════════════════════════════════════════════════════════════════════════

1. AUDITORÍA COMPLIANCE
   ¿Quién accedió a datos del Condominio A en diciembre?
   → Query: eventos WHERE tenant_id='condo_a' AND timestamp >= '2024-12-01'

2. RECONSTRUCCIÓN DE ESTADO
   ¿Cuándo se creó esta visita y quién la validó?
   → Query: eventos WHERE entidad='visita' AND entidad_id='v123'

3. DETECCIÓN DE ANOMALÍAS
   ¿Este usuario intentó acceder sin scope válido?
   → Query: eventos WHERE resultado='denegado' AND motivo LIKE '%scope%'

4. TRAZABILIDAD QR
   ¿Este QR fue validado? ¿Por quién? ¿Cuándo?
   → Query: eventos WHERE entidad='qr' AND entidad_id='qr_xyz'

5. VERIFICACIÓN DE INTEGRIDAD
   ¿Este evento fue alterado?
   → Calcular hash de campos críticos, comparar con hash_evento

═══════════════════════════════════════════════════════════════════════════════
PREPARADO PARA
═══════════════════════════════════════════════════════════════════════════════

- Recordia (memoria estructural temporal)
- HotVault (validación crítica en caliente)
- GDPR compliance (derecho al olvido estructural)
- SOC2 auditoría (histórico inmutable)
- Análisis de patrones (ML sobre eventos)

═══════════════════════════════════════════════════════════════════════════════
"""

# Enum types para consistencia estructural
from enum import Enum

class EventEntity(str, Enum):
    """Tipos de entidad afectada por eventos"""
    VISITA = "visita"
    QR = "qr"
    EVIDENCIA = "evidencia"
    USUARIO = "usuario"
    CONDOMINIO = "condominio"
    SCOPE = "scope"
    SESSION = "session"

class EventAction(str, Enum):
    """Tipos de acción ejecutada"""
    CREAR = "crear"
    VALIDAR = "validar"
    REGISTRAR = "registrar"
    REVOCAR = "revocar"
    DENEGAR = "denegar"
    MODIFICAR = "modificar"
    ELIMINAR = "eliminar"
    ASIGNAR = "asignar"
    LOGIN = "login"
    LOGOUT = "logout"

class EventResult(str, Enum):
    """Resultado de la acción"""
    PERMITIDO = "permitido"
    DENEGADO = "denegado"
    ERROR = "error"
    EXITO = "exito"
    FALLO = "fallo"

__all__ = [
    "EventEntity",
    "EventAction", 
    "EventResult",
]
