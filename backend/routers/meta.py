"""
═══════════════════════════════════════════════════════════════════════════════
Router del Dominio Meta-Operativo v1.0 (CONGELADO)
═══════════════════════════════════════════════════════════════════════════════

Endpoints API del dominio meta-operativo.

Norma: ACTA_CONGELAMIENTO_META_OPERATIVO_v1.0.md

ALCANCE CERRADO:
  POST /meta/assignments        (ASSIGN)
  DELETE /meta/assignments/{id} (REVOKE)
  GET /meta/assignments         (LIST)

NO existen otros endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.connection import get_db
from backend.core.dependencies import get_current_user
from backend.db.models import Usuario, IdentityTenantAssignment
from backend.core.meta import AssignmentType
from backend.core.meta.assignments import (
    assign_identity_to_tenant,
    revoke_identity_from_tenant,
    list_tenant_assignments,
    list_identity_assignments
)
from backend.core.meta.events import (
    registrar_evento_meta_assign,
    registrar_evento_meta_revoke,
    registrar_evento_meta_list,
    registrar_evento_meta_denegado
)


router = APIRouter(prefix="/meta", tags=["Meta-Operativo"])


# ═══════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════

class AssignmentRequest(BaseModel):
    """Request para crear asignación."""
    identity_id: str
    tenant_id: str
    assignment_type: AssignmentType


class RevocationRequest(BaseModel):
    """Request para revocar asignación."""
    reason: Optional[str] = None


class AssignmentResponse(BaseModel):
    """Response de asignación."""
    assignment_id: str
    identity_id: str
    tenant_id: str
    assignment_type: str
    assigned_by: str
    assigned_at: str
    revoked: bool
    
    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    request: AssignmentRequest,
    authorization: str = Header(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acción: ASSIGN_IDENTITY_TO_TENANT.
    
    Crea relación Identity → Tenant de forma auditable.
    
    Norma: Sección 3.1 del acta de congelamiento.
    
    Requiere: Authority GLOBAL activa.
    
    Returns:
        201: Asignación creada
        400: Validación fallida (identity/tenant no existe, self-assignment)
        403: Sin authority GLOBAL
        409: Asignación duplicada
    """
    try:
        # Extraer token completo para evento
        session_token = authorization.replace("Bearer ", "")
        
        # Ejecutar asignación
        assignment = assign_identity_to_tenant(
            db=db,
            actor_identity_id=current_user.usuario_id,
            target_identity_id=request.identity_id,
            target_tenant_id=request.tenant_id,
            assignment_type=request.assignment_type
        )
        
        # Registrar evento (tenant_id = NULL)
        registrar_evento_meta_assign(
            db=db,
            actor=current_user,
            session_token=session_token,
            assignment=assignment
        )
        
        return AssignmentResponse(
            assignment_id=assignment.assignment_id,
            identity_id=assignment.identity_id,
            tenant_id=assignment.tenant_id,
            assignment_type=assignment.assignment_type.value,
            assigned_by=assignment.assigned_by_identity_id,
            assigned_at=assignment.assigned_at.isoformat(),
            revoked=bool(assignment.revoked)
        )
        
    except HTTPException:
        # Re-lanzar HTTPExceptions de validaciones
        raise
    except Exception as e:
        # Registrar fallo
        try:
            registrar_evento_meta_denegado(
                db=db,
                actor_identity_id=current_user.usuario_id,
                session_token=authorization.replace("Bearer ", ""),
                accion="ASSIGN",
                motivo=str(e),
                metadata={
                    "target_identity_id": request.identity_id,
                    "target_tenant_id": request.tenant_id
                }
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear asignación: {str(e)}"
        )


@router.delete("/assignments/{assignment_id}", response_model=AssignmentResponse)
def revoke_assignment(
    assignment_id: str,
    request: RevocationRequest,
    authorization: str = Header(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acción: REVOKE_IDENTITY_FROM_TENANT.
    
    Revoca relación Identity → Tenant de forma auditable.
    
    Norma: Sección 3.2 del acta de congelamiento.
    
    Requiere: Authority GLOBAL activa.
    
    Returns:
        200: Asignación revocada
        403: Sin authority GLOBAL
        404: Asignación no existe o ya revocada
    """
    try:
        # Extraer token completo para evento
        session_token = authorization.replace("Bearer ", "")
        
        # Ejecutar revocación
        assignment = revoke_identity_from_tenant(
            db=db,
            actor_identity_id=current_user.usuario_id,
            assignment_id=assignment_id,
            revocation_reason=request.reason
        )
        
        # Registrar evento (tenant_id = NULL)
        registrar_evento_meta_revoke(
            db=db,
            actor=current_user,
            session_token=session_token,
            assignment=assignment
        )
        
        return AssignmentResponse(
            assignment_id=assignment.assignment_id,
            identity_id=assignment.identity_id,
            tenant_id=assignment.tenant_id,
            assignment_type=assignment.assignment_type.value,
            assigned_by=assignment.assigned_by_identity_id,
            assigned_at=assignment.assigned_at.isoformat(),
            revoked=bool(assignment.revoked)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        try:
            registrar_evento_meta_denegado(
                db=db,
                actor_identity_id=current_user.usuario_id,
                session_token=authorization.replace("Bearer ", ""),
                accion="REVOKE",
                motivo=str(e),
                metadata={"assignment_id": assignment_id}
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al revocar asignación: {str(e)}"
        )


@router.get("/assignments", response_model=List[AssignmentResponse])
def list_assignments(
    identity_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    include_revoked: bool = Query(False),
    authorization: str = Header(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acción: LIST_ASSIGNMENTS.
    
    Lista asignaciones por identity_id o tenant_id.
    
    Norma: Secciones 3.3 y 3.4 del acta de congelamiento.
    
    Requiere: Authority GLOBAL activa.
    
    Query params:
        identity_id: Listar asignaciones de una identidad (XOR con tenant_id)
        tenant_id: Listar asignaciones de un tenant (XOR con identity_id)
        include_revoked: Incluir asignaciones revocadas
    
    Returns:
        200: Lista de asignaciones
        400: Debe especificar identity_id o tenant_id
        403: Sin authority GLOBAL
    """
    # Validación: Debe especificar uno de los filtros
    if not identity_id and not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe especificar identity_id o tenant_id"
        )
    
    if identity_id and tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puede especificar identity_id o tenant_id, no ambos"
        )
    
    try:
        # Extraer token para evento
        session_token = authorization.replace("Bearer ", "")
        
        # Ejecutar consulta
        if tenant_id:
            assignments = list_tenant_assignments(
                db=db,
                actor_identity_id=current_user.usuario_id,
                tenant_id=tenant_id,
                include_revoked=include_revoked
            )
            query_type = "BY_TENANT"
            filter_value = tenant_id
        else:
            assignments = list_identity_assignments(
                db=db,
                actor_identity_id=current_user.usuario_id,
                identity_id=identity_id,
                include_revoked=include_revoked
            )
            query_type = "BY_IDENTITY"
            filter_value = identity_id
        
        # Registrar evento (tenant_id = NULL)
        registrar_evento_meta_list(
            db=db,
            actor=current_user,
            session_token=session_token,
            query_type=query_type,
            filter_value=filter_value,
            include_revoked=include_revoked,
            result_count=len(assignments)
        )
        
        return [
            AssignmentResponse(
                assignment_id=a.assignment_id,
                identity_id=a.identity_id,
                tenant_id=a.tenant_id,
                assignment_type=a.assignment_type.value,
                assigned_by=a.assigned_by_identity_id,
                assigned_at=a.assigned_at.isoformat(),
                revoked=bool(a.revoked)
            )
            for a in assignments
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        try:
            registrar_evento_meta_denegado(
                db=db,
                actor_identity_id=current_user.usuario_id,
                session_token=authorization.replace("Bearer ", ""),
                accion="LIST",
                motivo=str(e),
                metadata={
                    "identity_id": identity_id,
                    "tenant_id": tenant_id
                }
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar asignaciones: {str(e)}"
        )
