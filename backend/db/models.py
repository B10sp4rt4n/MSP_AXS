from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .connection import Base
import datetime


class MSP(Base):
    __tablename__ = "msps"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)


class Visita(Base):
    __tablename__ = "visitas"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    motivo = Column(String, nullable=True)

    usuario = relationship("Usuario")
