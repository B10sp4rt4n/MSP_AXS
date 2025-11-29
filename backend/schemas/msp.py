from pydantic import BaseModel
from typing import Optional


class MSPBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class MSPCreate(MSPBase):
    pass


class MSP(MSPBase):
    id: int

    class Config:
        orm_mode = True
