from pydantic import BaseModel
from typing import Optional


class EvidenciaBase(BaseModel):
    filename: str
    url: Optional[str] = None


class Evidencia(EvidenciaBase):
    id: int

    class Config:
        orm_mode = True
