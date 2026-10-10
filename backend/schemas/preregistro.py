from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime


class PreregistroCreate(BaseModel):
    condominio_id: str | None = Field(default=None, min_length=1, max_length=100)
    destino_id: str | None = Field(default=None, min_length=1, max_length=100)
    nombre_visitante: str
    fecha_visita: Optional[datetime] = None
    tipo_visita: str
    proposito: str | None = Field(default=None, max_length=500)
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
