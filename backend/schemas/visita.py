from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VisitaBase(BaseModel):
    usuario_id: int
    motivo: Optional[str] = None


class VisitaCreate(VisitaBase):
    pass


class Visita(VisitaBase):
    id: int
    fecha: datetime

    class Config:
        orm_mode = True
