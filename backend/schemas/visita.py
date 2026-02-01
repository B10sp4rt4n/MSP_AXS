from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, List


class VisitaBase(BaseModel):
    nombre_visitante: str
    tipo_visita: str
    vigencia: datetime


class VisitaCreate(VisitaBase):
    condominio_id: str
    casa_unidad: str | None = None


class VisitaRapidaCreate(BaseModel):
    """Schema para crear visita en-situ (sin pre-registro) por guardia."""
    nombre_visitante: str = Field(..., min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    casa_unidad: str = Field(..., min_length=1, max_length=50)
    residente_anfitrion: Optional[str] = Field(None, max_length=100)
    tipo_visitante: str = Field(..., description="frecuente, eventual, proveedor, cliente, entrega, consulta, familia")
    motivo: Optional[str] = Field(None, max_length=200)
    placa_vehiculo: Optional[str] = Field(None, max_length=20)
    
    class Config:
        example = {
            "nombre_visitante": "Juan Pérez",
            "telefono": "+57 310 1234567",
            "casa_unidad": "302",
            "residente_anfitrion": "Carlos López",
            "tipo_visitante": "eventual",
            "motivo": "Visita social",
            "placa_vehiculo": "ABC-123"
        }


class VisitaRapidaResponse(BaseModel):
    """Respuesta de creación de visita rápida."""
    visita_id: str
    condominio_id: str
    nombre_visitante: str
    telefono: Optional[str]
    casa_unidad: str
    residente_anfitrion: Optional[str]
    tipo_visitante: str
    motivo: Optional[str]
    placa_vehiculo: Optional[str]
    estado: str  # "creada_sin_qr"
    creada_por: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


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


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMAS PARA MODO GUARDIA - CAPTURA DE EVIDENCIAS Y REGISTRO
# ═══════════════════════════════════════════════════════════════════════════

class CapturaEvidenciasResponse(BaseModel):
    """Respuesta de captura de evidencias."""
    visita_id: str
    total_fotos: int
    fotos_urls: List[str]
    estado: str
    mensaje: str
    
    class Config:
        from_attributes = True


class RegistrarEntradaRequest(BaseModel):
    """Request para registrar entrada de visitante."""
    notas: Optional[str] = Field(None, max_length=500, description="Notas del guardia sobre la entrada")
    
    class Config:
        json_schema_extra = {
            "example": {
                "notas": "Documento válido, vehículo permitido, sin antecedentes"
            }
        }


class RegistrarEntradaResponse(BaseModel):
    """Respuesta de registro de entrada."""
    visita_id: str
    estado: str
    hora_entrada: datetime
    qr_token: Optional[str]
    qr_vigencia: Optional[datetime]
    mensaje: str
    
    class Config:
        from_attributes = True


class RegistrarSalidaRequest(BaseModel):
    """Request para registrar salida de visitante."""
    notas: Optional[str] = Field(None, max_length=500, description="Notas del guardia sobre la salida")
    
    class Config:
        json_schema_extra = {
            "example": {
                "notas": "Salida sin incidentes"
            }
        }


class RegistrarSalidaResponse(BaseModel):
    """Respuesta de registro de salida."""
    visita_id: str
    estado: str
    hora_entrada: Optional[datetime]
    hora_salida: datetime
    duracion_minutos: Optional[int]
    mensaje: str
    
    class Config:
        from_attributes = True

