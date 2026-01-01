"""
═══════════════════════════════════════════════════════════════════════════════
Dominio Meta-Operativo v1.0 (CONGELADO)
═══════════════════════════════════════════════════════════════════════════════

Enumeraciones y constantes del dominio meta-operativo.

Norma: ACTA_CONGELAMIENTO_META_OPERATIVO_v1.0.md

ALCANCE CERRADO:
  - ASSIGN_IDENTITY_TO_TENANT
  - REVOKE_IDENTITY_FROM_TENANT
  - LIST_TENANT_ASSIGNMENTS
  - LIST_IDENTITY_ASSIGNMENTS

NO existen otras acciones.
NO se aceptan extensiones.
"""

from enum import Enum


class MetaAction(str, Enum):
    """
    Acciones meta-operativas permitidas.
    
    Norma: Sección 1.1 del acta de congelamiento.
    ESTAS SON LAS ÚNICAS ACCIONES PERMITIDAS.
    """
    ASSIGN = "ASSIGN"   # Crear relación Identity → Tenant
    REVOKE = "REVOKE"   # Revocar relación Identity → Tenant
    LIST = "LIST"       # Listar relaciones existentes


class AssignmentType(str, Enum):
    """
    Tipos de asignación Identity → Tenant.
    
    Norma: Sección 2.2 del acta de congelamiento.
    """
    FIRST_TIER_ADMIN = "FIRST_TIER_ADMIN"  # Authority FIRST_TIER sobre el tenant
    REGULAR_ADMIN = "REGULAR_ADMIN"        # Scope operativo como admin
    OPERATOR = "OPERATOR"                  # Scope operativo como operador


# Entidad para eventos meta-operativos
META_EVENT_ENTITY = "IDENTITY_TENANT_ASSIGNMENT"

# tenant_id DEBE ser NULL en eventos meta (norma crítica)
META_EVENT_TENANT_ID = None
