from pydantic import BaseModel
from typing import Optional


class CondominioBase(BaseModel):
    nombre: str
    direccion: Optional[str] = None


class Condominio(CondominioBase):
    id: int

    class Config:
        orm_mode = True
