"""Private assisted ARCO register. No delivery, erasure or public intake automation."""
import os
import uuid
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session
from backend.db.core import get_core_db, Usuario, AccessLevel
from backend.db.core.models import ArcoCase
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import authorized_tenant_context
from backend.core.security import verificar_rol
from backend.services.event_outbox import contexto_evento, encolar_evento


def enabled():
    if os.getenv('AXS_ARCO_CASES_ENABLED', '').lower() != 'true':
        raise HTTPException(404, 'Registro ARCO no habilitado')


def privacy(response: Response):
    response.headers['Cache-Control'] = 'private, no-store'


router = APIRouter(prefix='/arco/{condominio_id}', tags=['ARCO privado'],
                   dependencies=[Depends(enabled), Depends(privacy)])


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Create(Input):
    request_id: uuid.UUID
    received_at: datetime
    right: Literal['acceso', 'rectificacion', 'cancelacion', 'oposicion']
    # Opaque references to a separate private dossier. Never ID images or secrets.
    subject_ref: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    owner_id: str = Field(min_length=1, max_length=100)
    determination_due: datetime

    @field_validator('received_at', 'determination_due')
    @classmethod
    def zoned(cls, v):
        if v.tzinfo is None:
            raise ValueError('Se requiere zona horaria')
        return v.astimezone(timezone.utc).replace(tzinfo=None)


class Transition(Input):
    version: int = Field(ge=1)
    state: Literal['verificada', 'resuelta', 'ejecutando', 'cerrada']
    reference: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    outcome: Literal['procedente', 'parcial', 'improcedente'] | None = None
    execution_due: datetime | None = None
    pending_actions: int = Field(default=0, ge=0, le=10000)
    communication_ref: str | None = Field(default=None, min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')

    @field_validator('execution_due')
    @classmethod
    def zoned(cls, v):
        if v is not None:
            if v.tzinfo is None:
                raise ValueError('Se requiere zona horaria')
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


def actor(condominio_id: str, user: Usuario = Depends(get_current_user),
          _tenant: str = Depends(authorized_tenant_context(AccessLevel.ADMIN_CONDOMINIO, expected_mode=None))):
    # Do not persist the designation on the user model.
    verificar_rol(user, ['ADMIN_CONDOMINIO', 'MSP_ADMIN'])
    allowed = {x.strip() for x in os.getenv('AXS_ARCO_OPERATORS', '').split(',') if x.strip()}
    if f'{user.usuario_id}:{condominio_id}' not in allowed:
        raise HTTPException(403, 'Requiere designación de privacidad para este cliente')
    return user


def view(row):
    return {c.name: getattr(row, c.name) for c in ArcoCase.__table__.columns}


def audit(db, row, user, request, action):
    context = contexto_evento(user, request.headers.get('Authorization', '').removeprefix('Bearer '),
                              entidad='arco', accion=action)
    # No subject reference, decision evidence or dossier contents in general ledger.
    encolar_evento(db, row.condominio_id, row.case_id, context,
                  metadata={'state': row.state, 'version': row.version})


@router.post('')
def create(condominio_id: str, data: Create, request: Request,
           user: Usuario = Depends(actor), db: Session = Depends(get_core_db)):
    values = data.model_dump(exclude={'request_id'})
    if data.received_at > datetime.utcnow() or data.determination_due <= data.received_at:
        raise HTTPException(422, 'Recepción o vencimiento inconsistentes')
    previous = db.query(ArcoCase).filter_by(case_id=str(data.request_id), condominio_id=condominio_id).first()
    if previous:
        if any(getattr(previous, k) != v for k, v in values.items()):
            raise HTTPException(409, 'Referencia ya utilizada con otros datos')
        return view(previous)
    if db.query(ArcoCase).filter_by(case_id=str(data.request_id)).first():
        raise HTTPException(409, 'Referencia no disponible')
    row = ArcoCase(case_id=str(data.request_id), condominio_id=condominio_id,
                   state='recibida', version=1, history=[], pending_actions=0, **values)
    db.add(row)
    audit(db, row, user, request, 'recibir_arco')
    db.commit()
    return view(row)


@router.get('')
def listing(condominio_id: str, offset: int = 0, limit: int = 50,
            user: Usuario = Depends(actor), db: Session = Depends(get_core_db)):
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Paginación inválida')
    return [view(r) for r in db.query(ArcoCase).filter_by(condominio_id=condominio_id)
            .order_by(ArcoCase.received_at, ArcoCase.case_id).offset(offset).limit(limit).all()]


@router.post('/{case_id}/estado')
def transition(condominio_id: str, case_id: uuid.UUID, data: Transition, request: Request,
               user: Usuario = Depends(actor), db: Session = Depends(get_core_db)):
    row = db.query(ArcoCase).filter_by(case_id=str(case_id), condominio_id=condominio_id).with_for_update().first()
    if not row:
        raise HTTPException(404, 'Expediente no encontrado')
    if row.version != data.version:
        raise HTTPException(409, 'El expediente cambió; vuelve a consultarlo')
    next_state = {'recibida': 'verificada', 'verificada': 'resuelta', 'resuelta': 'ejecutando', 'ejecutando': 'cerrada'}
    if next_state.get(row.state) != data.state:
        raise HTTPException(409, 'Transición no permitida')
    if data.state == 'resuelta':
        if not data.outcome or not data.communication_ref:
            raise HTTPException(422, 'Requiere decisión y constancia de comunicación')
        if data.outcome != 'improcedente' and (not data.execution_due or data.execution_due <= datetime.utcnow()):
            raise HTTPException(422, 'Requiere vencimiento de ejecución futuro')
        row.outcome, row.execution_due = data.outcome, data.execution_due
    elif data.outcome is not None or data.execution_due is not None:
        raise HTTPException(422, 'La decisión se registra al resolver')
    if data.state == 'cerrada' and (data.pending_actions or not data.communication_ref):
        raise HTTPException(422, 'No se cierra con pendientes o sin constancia de respuesta')
    row.state = data.state
    row.version += 1
    row.pending_actions = data.pending_actions
    row.history = [*row.history, {**data.model_dump(mode='json'), 'actor': user.usuario_id,
                                 'at': datetime.utcnow().isoformat()}]
    audit(db, row, user, request, 'actualizar_arco')
    db.commit()
    return view(row)
