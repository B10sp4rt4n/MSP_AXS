"""
Router de Condominios - INTEGRADO CON AUP_GOV

Operaciones críticas:
  - Crear tenant (condominio) → Requiere AUP_GOV
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..core.dependencies import get_db
from ..core.auth.dependencies import get_current_user
from ..core.security import verificar_rol
from ..db.models import Usuario, Condominio
from ..core.gov.facade import puede_ejecutar_accion
import uuid

router = APIRouter(prefix="/condominios", tags=["condominios"])


@router.get("/")
def list_condominios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Lista condominios accesibles por el usuario."""
    verificar_rol(usuario, ["MSP_ADMIN", "ADMIN_CONDOMINIO"])
    
    if usuario.rol_base == "MSP_ADMIN":
        # Admin global ve todos
        condominios = db.query(Condominio).all()
    else:
        # Ver solo su condominio
        condominios = db.query(Condominio).filter(
            Condominio.condominio_id == usuario.condominio_id
        ).all()
    
    return {
        "condominios": [
            {
                "condominio_id": c.condominio_id,
                "nombre": c.nombre,
                "direccion": c.direccion
            }
            for c in condominios
        ]
    }


@router.post("/")
def crear_condominio(
    nombre: str,
    direccion: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo condominio (tenant).
    
    ═══════════════════════════════════════════════════════════════════════
    OPERACIÓN CRÍTICA: Requiere evaluación de AUP_GOV
    ═══════════════════════════════════════════════════════════════════════
    """
    verificar_rol(usuario, ["MSP_ADMIN"])
    
    # ═══════════════════════════════════════════════════════════════════════
    # AUP_GOV: Evaluar política ANTES de crear tenant
    # Axioma: Gobierno precede a operación
    # ═══════════════════════════════════════════════════════════════════════
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # Contar tenants actuales del usuario (si tiene first tier)
    tenants_count = db.query(Condominio).count()
    
    permitido, motivo = puede_ejecutar_accion(
        db=db,
        usuario=usuario,
        session_token=token,
        accion="crear_tenant",
        valor_actual=tenants_count
    )
    
    if not permitido:
        raise HTTPException(403, detail=f"Gobierno denegó creación: {motivo}")
    # ═══════════════════════════════════════════════════════════════════════
    
    # Crear condominio
    nuevo_condo = Condominio(
        condominio_id=f"condo_{uuid.uuid4().hex[:12]}",
        nombre=nombre,
        direccion=direccion
    )
    
    db.add(nuevo_condo)
    db.commit()
    db.refresh(nuevo_condo)
    
    return {
        "status": "ok",
        "condominio_id": nuevo_condo.condominio_id,
        "nombre": nuevo_condo.nombre,
        "mensaje": "Condominio creado (gobernado por AUP_GOV)"
    }

