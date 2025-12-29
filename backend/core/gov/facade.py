"""
═══════════════════════════════════════════════════════════════════════════════
AUP_GOV: Fachada de Gobierno (Interfaz Única para Routers)
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

Esta fachada NO contiene lógica de gobierno.
Solo expone UNA función que los routers deben invocar.

Axioma: Los routers NO deciden poder, lo consultan.

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional, Any
from sqlalchemy.orm import Session

from backend.db.models import Usuario
from backend.core.gov.integration import evaluar_politica_con_evento


def puede_ejecutar_accion(
    db: Session,
    usuario: Usuario,
    session_token: str,
    accion: str,
    tenant_id: Optional[str] = None,
    valor_actual: Optional[Any] = None,
    metadata: Optional[dict] = None
) -> tuple[bool, Optional[str]]:
    """
    ═══════════════════════════════════════════════════════════════════════
    INTERFAZ ÚNICA: ¿Puede este usuario ejecutar esta acción?
    ═══════════════════════════════════════════════════════════════════════
    
    Los routers SOLO deben invocar esta función antes de operaciones críticas.
    
    Axiomas aplicados:
      1. Gobierno precede a operación
      2. Toda decisión genera AUP_EVENT
      3. Sin política → denegado (safe by default)
      4. Si AUP_GOV falla → denegado
    
    Args:
        db: Sesión de BD
        usuario: AUP_IDENTITY que intenta la acción
        session_token: JWT para trazabilidad
        accion: Acción a evaluar (crear_tenant, generar_qr, etc.)
        tenant_id: Tenant donde ocurre (si aplica)
        valor_actual: Valor actual para comparar con límites (ej: 5 tenants)
        metadata: Contexto adicional (ej: {dias_vigencia: 7})
    
    Returns:
        (permitido: bool, motivo: str)
        
        Si permitido = False → Router debe abortar con HTTPException(403)
        Si permitido = True  → Router puede continuar
    
    Excepciones:
        Si AUP_GOV falla internamente → devuelve (False, "Error de gobierno")
        NUNCA propaga excepciones hacia routers (safe by default)
    
    Ejemplos:
        # Validar antes de generar QR
        permitido, motivo = puede_ejecutar_accion(
            db, usuario, token,
            accion="generar_qr",
            tenant_id="condo_a",
            metadata={"dias_vigencia": 7}
        )
        if not permitido:
            raise HTTPException(403, detail=motivo)
        
        # Validar antes de crear tenant
        permitido, motivo = puede_ejecutar_accion(
            db, usuario, token,
            accion="crear_tenant",
            valor_actual=usuario_tenants_count
        )
        if not permitido:
            raise HTTPException(403, detail=motivo)
    """
    try:
        # Delegar a función de integración (que registra eventos)
        return evaluar_politica_con_evento(
            db=db,
            ejecutor=usuario,
            session_token=session_token,
            accion=accion,
            tenant_id=tenant_id,
            valor_actual=valor_actual,
            metadata=metadata
        )
    
    except Exception as e:
        # Si AUP_GOV falla → denegar por defecto (safe)
        # NO propagar excepción (axioma: safe by default)
        return (False, f"Error en gobierno: {str(e)}")
