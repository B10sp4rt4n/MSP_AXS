from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from datetime import datetime
from .connection import Base


class MSP(Base):
    __tablename__ = "msps_exo"
    id = Column(Integer, primary_key=True, index=True)
    msp_id = Column(String, unique=True, index=True)
    nombre = Column(String)


class Condominio(Base):
    __tablename__ = "condominios_exo"
    id = Column(Integer, primary_key=True, index=True)
    condominio_id = Column(String, unique=True, index=True)
    msp_id = Column(String, ForeignKey("msps_exo.msp_id"))
    nombre = Column(String)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(String, unique=True, index=True)
    msp_id = Column(String)
    condominio_id = Column(String)
    casa_unidad = Column(String)
    nombre = Column(String)
    email = Column(String)
    rol = Column(String)  # MSP_ADMIN, ADMIN_CONDOMINIO, GUARDIA, RESIDENTE
    password_hash = Column(Text)
    creado = Column(DateTime, default=datetime.utcnow)


class Caseta(Base):
    __tablename__ = "casetas"
    id = Column(Integer, primary_key=True, index=True)
    caseta_id = Column(String, unique=True, index=True)
    condominio_id = Column(String, ForeignKey("condominios_exo.condominio_id"))
    nombre = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Visita(Base):
    __tablename__ = "visitas"
    id = Column(Integer, primary_key=True, index=True)
    visita_id = Column(String, unique=True, index=True)
    condominio_id = Column(String)
    nombre_visitante = Column(String)
    casa_unidad = Column(String)
    tipo_visita = Column(String)
    vigencia = Column(DateTime)
    qr_token = Column(String)
    qr_vigencia = Column(DateTime)
    estado = Column(String, default="pendiente")
    entrada_registrada_en = Column(DateTime)
    salida_registrada_en = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Evidencia(Base):
    __tablename__ = "evidencias"
    id = Column(Integer, primary_key=True, index=True)
    evidencia_id = Column(String, unique=True, index=True)
    visita_id = Column(String, index=True)
    categoria = Column(String)          # entrada / salida
    sub_tipo = Column(String)           # visitante, ine_frente, ine_reverso, placas, vehiculo, documento, foto_salida
    archivo_url = Column(Text)
    hash_sha256 = Column(Text)
    guardia_id = Column(String)
    # Use SQLAlchemy JSON type (works with Postgres JSON/JSONB and falls back on Text for SQLite)
    # JSONB (postgres-only) removed to keep local compatibility with SQLite.
    # If production requires JSONB-specific features, ensure migrations use that type.
    metadata_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
