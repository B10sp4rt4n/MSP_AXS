from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PreregistroCreate(BaseModel):
    nombre_visitante: str
    fecha_visita: datetime
    tipo_visita: str
    notas: Optional[str] = None
    placa: Optional[str] = None
    documento: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "nombre_visitante": "Juan Perez",
                "fecha_visita": "2025-12-01T10:00:00Z",
                "tipo_visita": "visita_personal",
                "notas": "Llega con retraso",
                "placa": "ABC123",
                "documento": "INE"
            }
        }
