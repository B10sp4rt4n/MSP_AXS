from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime, timezone


class VisitaBase(BaseModel):
    nombre_visitante: str
    tipo_visita: str
    proposito: str | None = Field(default=None, max_length=500)
    vigencia: datetime


class VisitaCreate(VisitaBase):
    condominio_id: str
    casa_unidad: str | None = None
    destino_id: str | None = None
    destino_motivo: str | None = None


class VisitaResponse(VisitaBase):
    visita_id: str
    condominio_id: str
    casa_unidad: str | None
    destino_id: str | None = None
    destino_tipo: str | None = None
    destino_motivo: str | None = None
    autorizada_por: str | None = None
    autorizada_en: datetime | None = None
    estado: str
    qr_token: str | None
    qr_vigencia: datetime | None
    entrada_registrada_en: datetime | None = None
    salida_registrada_en: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("entrada_registrada_en", "salida_registrada_en", "created_at", "autorizada_en")
    @classmethod
    def audit_timestamp_utc(cls, value: datetime | None) -> datetime | None:
        # CORE persists audit timestamps with datetime.utcnow() in naive columns.
        # Declare that offset so browsers do not interpret them as local time.
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class PreregistroCreate(BaseModel):
    nombre_visitante: str
    fecha_visita: datetime
    tipo_visita: str
    notas: str | None = None
    placa: str | None = None
