from pydantic import BaseModel
from datetime import datetime


class VisitaBase(BaseModel):
    nombre_visitante: str
    tipo_visita: str
    vigencia: datetime


class VisitaCreate(VisitaBase):
    condominio_id: str
    casa_unidad: str | None = None


class VisitaResponse(VisitaBase):
    visita_id: str
    condominio_id: str
    casa_unidad: str | None
    estado: str
    qr_token: str | None
    qr_vigencia: datetime | None

    class Config:
        orm_mode = True


class PreregistroCreate(BaseModel):
    nombre_visitante: str
    fecha_visita: datetime
    tipo_visita: str
    notas: str | None = None
    placa: str | None = None
