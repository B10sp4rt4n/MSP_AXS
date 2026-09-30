from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class PreregistroCreate(BaseModel):
    nombre_visitante: str
    fecha_visita: Optional[datetime] = None
    tipo_visita: str
    notas: Optional[str] = None
    placa: Optional[str] = None
    documento: Optional[str] = None

    @validator("fecha_visita")
    def fecha_debe_ser_futura(cls, v):
        if v is None:
            return None
        if v.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        else:
            now = datetime.utcnow()
        if v <= now:
            raise ValueError("La fecha de visita debe ser en el futuro")
        if v.tzinfo is not None:
            from datetime import timezone
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v

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
