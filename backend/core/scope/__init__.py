"""
═══════════════════════════════════════════════════════════════════════════════
AUP_SCOPE - Declaración de Alcance Estructural
═══════════════════════════════════════════════════════════════════════════════

PASO 2 de la Arquitectura AUP

DECLARACIÓN DE ENTIDADES
═════════════════════════

AUP_TENANT
──────────
  Qué es:     Entidad contenedora estructural
  Propósito:  Frontera de datos, operación y auditoría
  En MSP_AXS: Condominio
  
  Atributos:
    - tenant_id (condominio_id)
    - nombre
    - estado
    
  Axioma asociado:
    Ninguna acción ocurre fuera de un tenant.


AUP_SCOPE
─────────
  Qué es:     Entidad relacional viva que declara alcance explícito
  Propósito:  Define DÓNDE una identidad puede actuar
  
  NO ES:
    - Un rol (el rol define QUÉ, el scope define DÓNDE)
    - Permisos RBAC tradicionales
    - Inferible o implícito
  
  ES:
    - Declaración explícita de alcance
    - Validable estructuralmente
    - Dinámico (no se serializa en JWT)
  
  Atributos:
    - identity_id    : AUP_IDENTITY que posee este alcance
    - tenant_id      : AUP_TENANT sobre el que aplica
    - access_level   : Nivel de acceso (admin_condominio, guardia, residente)
    - estado         : activo/inactivo/suspendido
    - created_at     : Timestamp de creación
    - revoked_at     : Timestamp de revocación (si aplica)


RELACIONES AUP
═══════════════

    AUP_IDENTITY
         │
         │ tiene múltiples
         ▼
    AUP_SCOPE ───────────> AUP_TENANT
         │                      │
         │ autoriza             │ contiene
         │ acciones en          │ recursos
         ▼                      ▼
    Acción/Recurso ◄─── pertenece a ─── AUP_TENANT


AXIOMAS (Reglas Inmutables)
════════════════════════════

1. AXIOMA DE FRONTERA
   Ninguna acción ocurre fuera de un AUP_TENANT.
   
2. AXIOMA DE ALCANCE EXPLÍCITO
   El rol define QUÉ puedes hacer.
   El scope define DÓNDE puedes hacerlo.
   
3. AXIOMA DE NO-INFERENCIA
   El sistema NO infiere alcance.
   El sistema VALIDA alcance declarado.
   
4. AXIOMA DE EXISTENCIA OPERATIVA
   Una AUP_IDENTITY sin AUP_SCOPE válido para un tenant
   no existe operativamente en ese tenant.
   
5. AXIOMA DE DINAMISMO
   AUP_SCOPE NO se serializa en AUP_SESSION (JWT).
   Se valida en tiempo de ejecución.


DIFERENCIA CONCEPTUAL CLAVE
════════════════════════════

ANTES (Solo Roles):
    Usuario tiene rol → Puede hacer X
    Problema: ¿En qué condominio? (implícito, inseguro)

AHORA (AUP_SCOPE):
    Usuario tiene:
      - AUP_IDENTITY (quién es)
      - Rol base (qué puede hacer en teoría)
      - AUP_SCOPE (dónde puede hacerlo en práctica)
    
    Validación:
      1. ¿Existe AUP_SESSION válida? (PASO 1)
      2. ¿Existe AUP_SCOPE para este tenant? (PASO 2)
      3. ¿El access_level permite esta acción? (PASO 2)


EJEMPLO REAL
════════════

Caso: Residente de Condominio A intenta ver visitas de Condominio B

Tradicional:
    if usuario.rol == "RESIDENTE":
        # ¿De cuál condominio? (implícito, PELIGRO)
        return visitas

AUP:
    if validar_scope(
        identity=usuario,
        tenant_id="condominio_b",
        access_level="residente"
    ):
        return visitas
    else:
        raise 403  # No tiene scope en ese tenant


CASOS DE USO HABILITADOS
═════════════════════════

1. First Tier Natural
   Un usuario puede tener AUP_SCOPE en múltiples tenants:
     - Guardia en Condominio A
     - Residente en Condominio B
   
2. Revocación Granular
   Revocar acceso a un tenant sin afectar otros.
   
3. Auditoría Estructural
   Quién tuvo acceso a qué tenant, cuándo.
   
4. Delegación Temporal
   Crear scope con vigencia (futuro).


MIGRACIÓN DESDE PASO 1
═══════════════════════

ANTES (Solo AUP_SESSION):
    JWT = { sub: user_id, role: "RESIDENTE" }
    Endpoint confía en el rol implícitamente.

AHORA (AUP_SESSION + AUP_SCOPE):
    JWT = { sub: user_id, role: "RESIDENTE" }  ← No cambia
    Endpoint valida scope explícitamente:
        validar_scope(user_id, tenant_objetivo, action)


NO SE ROMPE NADA
El JWT NO cambia.
Los endpoints SÍ agregan validación adicional.


PREPARACIÓN PARA PASO 3 (AUP_EVENT)
════════════════════════════════════

Cada validación de scope será un evento auditable:
    AUP_EVENT {
      tipo: "scope_validation",
      identity_id: "user123",
      tenant_id: "condo_a",
      accion: "leer_visitas",
      resultado: "permitido"
    }

═══════════════════════════════════════════════════════════════════════════════
"""
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======

from .validator import (
    validar_scope,
    obtener_scopes_usuario,
    obtener_scope_especifico,
    obtener_scope_usuario_en_tenant,
    nivel_suficiente,
    ACCESS_LEVEL_HIERARCHY
)

__all__ = [
    "validar_scope",
    "obtener_scopes_usuario", 
    "obtener_scope_especifico",
    "obtener_scope_usuario_en_tenant",
    "nivel_suficiente",
    "ACCESS_LEVEL_HIERARCHY"
]
>>>>>>> origin/main
>>>>>>> main
