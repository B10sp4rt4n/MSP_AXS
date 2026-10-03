"""Reglas operativas elegidas por cada condominio, apagadas por defecto."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

TipoVisita = Literal["eventual", "frecuente", "visita_personal", "proveedor", "entrega"]


class ReglasAcceso(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exigir_proposito: StrictBool = False
    exigir_autorizacion: StrictBool = False
    tipos_visita: list[TipoVisita] = Field(default_factory=lambda: [
        "eventual", "frecuente", "visita_personal", "proveedor", "entrega"], min_length=1)

    @field_validator("tipos_visita")
    @classmethod
    def tipos_unicos(cls, value):
        return list(dict.fromkeys(value))


class AutorizarVisita(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposito: str | None = Field(default=None, max_length=500)
