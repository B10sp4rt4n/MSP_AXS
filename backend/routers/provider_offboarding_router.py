from typing import Literal
from uuid import UUID
from backend.services.provider_contracts import history, open_contract, grant_staff
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.orm import Session
from backend.core.auth.dependencies import get_current_user
from backend.db.core import get_core_db, Usuario
from backend.db.gov import get_gov_db
from backend.services.provider_offboarding import classify, inventory, offboard

router=APIRouter(prefix='/condominios',tags=['Gobierno de proveedores'])

class OriginBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: Literal['msp','condominio']
    msp_id: str | None = None
    evidence_ref: str = Field(min_length=1,max_length=500)
    @field_validator('evidence_ref')
    @classmethod
    def meaningful(cls,v):
        if not v.strip(): raise ValueError('Referencia requerida')
        return v.strip()

class ExitBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    msp_id: str = Field(min_length=1,max_length=100)
    contract_id: UUID | None = None
    reason: str = Field(min_length=1,max_length=500)
    @field_validator('reason','msp_id')
    @classmethod
    def meaningful(cls,v):
        if not v.strip(): raise ValueError('Valor requerido')
        return v.strip()

@router.get('/{condominio_id}/permisos/procedencia')
def inspect(condominio_id:str,db:Session=Depends(get_core_db),gov:Session=Depends(get_gov_db),actor:Usuario=Depends(get_current_user)):
    return inventory(db,gov,actor,condominio_id)

@router.put('/{condominio_id}/permisos/{scope_id}/procedencia')
def record(condominio_id:str,scope_id:int,body:OriginBody,request:Request,
           db:Session=Depends(get_core_db),gov:Session=Depends(get_gov_db),actor:Usuario=Depends(get_current_user)):
    return classify(db,gov,actor,condominio_id,scope_id,body.kind,body.msp_id,body.evidence_ref,
                    request.headers.get('Authorization',''))

@router.post('/{condominio_id}/proveedor/baja')
def leave(condominio_id:str,body:ExitBody,request:Request,
          db:Session=Depends(get_core_db),gov:Session=Depends(get_gov_db),actor:Usuario=Depends(get_current_user)):
    return offboard(db,gov,actor,condominio_id,body.msp_id,body.reason,request.headers.get('Authorization',''),
                    str(body.contract_id) if body.contract_id else None)


class ContractBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    contract_id: UUID
    msp_id: str = Field(min_length=1, max_length=100)
    evidence_ref: str = Field(min_length=1, max_length=500)
    @field_validator('msp_id', 'evidence_ref')
    @classmethod
    def meaningful(cls, value):
        if not value.strip(): raise ValueError('Valor requerido')
        return value.strip()


class GrantBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    evidence_ref: str = Field(min_length=1, max_length=500)
    @field_validator('evidence_ref')
    @classmethod
    def meaningful(cls, value):
        if not value.strip(): raise ValueError('Referencia requerida')
        return value.strip()


@router.get('/{condominio_id}/proveedor/contratos')
def contracts(condominio_id: str, db: Session = Depends(get_core_db),
              gov: Session = Depends(get_gov_db), actor: Usuario = Depends(get_current_user)):
    return history(db, gov, actor, condominio_id)


@router.post('/{condominio_id}/proveedor/contratos')
def create_contract(condominio_id: str, body: ContractBody, request: Request,
                    db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
                    actor: Usuario = Depends(get_current_user)):
    return open_contract(db, gov, actor, condominio_id, str(body.contract_id), body.msp_id,
                         body.evidence_ref, request.headers.get('Authorization', ''))


@router.post('/{condominio_id}/proveedor/contratos/{contract_id}/personal/{usuario_id}')
def assign_staff(condominio_id: str, contract_id: UUID, usuario_id: str, body: GrantBody, request: Request,
                 db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
                 actor: Usuario = Depends(get_current_user)):
    return grant_staff(db, gov, actor, condominio_id, str(contract_id), usuario_id,
                       body.evidence_ref, request.headers.get('Authorization', ''))
