from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from backend.schemas.reglas_acceso import TipoVisita


class SolicitarAcceso(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    solicitud_id: UUID
    destino_id: str = Field(min_length=1, max_length=100)
    nombre_visitante: str = Field(min_length=3, max_length=150)
    tipo_visita: TipoVisita
    proposito: str = Field(min_length=3, max_length=500)
    visita_id: str | None = None


class ResponderAcceso(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["permitida", "rechazada"]
    consentimiento: StrictBool

    @field_validator("consentimiento")
    @classmethod
    def explicit_consent(cls, value):
        if value is not True:
            raise ValueError("Confirma que deseas registrar esta decisión")
        return value
