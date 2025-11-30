from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import uuid
from typing import Any, Optional

from ..db.models import Visita, Evidencia
from ..utils.hash_tools import calcular_hash_sha256
from ..utils.file_storage import guardar_archivo
from ..core.config import settings


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def generar_visita_id() -> str:
    return f"VIS-{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------
# Crear visita (ADMIN / CONDOMINIO)
# ---------------------------------------------------------
def crear_visita(db: Session, data: Any, condominio_id: str, casa_unidad: Optional[str] = None) -> Visita:
    visita_id = generar_visita_id()
    visita = Visita(
        visita_id=visita_id,
        condominio_id=condominio_id,
        nombre_visitante=getattr(data, "nombre_visitante", None),
        casa_unidad=casa_unidad,
        tipo_visita=getattr(data, "tipo_visita", None),
        vigencia=getattr(data, "vigencia", None),
        estado="pendiente",
    )
    try:
        db.add(visita)
        db.commit()
        db.refresh(visita)
    except Exception:
        db.rollback()
        raise

    return visita


# ---------------------------------------------------------
# Actualizar QR de una visita
# ---------------------------------------------------------
def actualizar_qr(db: Session, visita_id: str, token: str, qr_vigencia: datetime) -> Optional[Visita]:
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if visita:
        visita.qr_token = token
        visita.qr_vigencia = qr_vigencia
        try:
            db.commit()
            db.refresh(visita)
        except Exception:
            db.rollback()
            raise
    return visita


# ---------------------------------------------------------
# Registrar entrada del visitante
# ---------------------------------------------------------
def registrar_entrada(db: Session, visita_id: str) -> Optional[Visita]:
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if visita:
        visita.estado = "entrada_registrada"
        visita.entrada_registrada_en = datetime.utcnow()
        try:
            db.commit()
            db.refresh(visita)
        except Exception:
            db.rollback()
            raise
    return visita


# ---------------------------------------------------------
# Registrar salida del visitante
# ---------------------------------------------------------
def registrar_salida(db: Session, visita_id: str) -> Optional[Visita]:
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).first()
    if visita:
        visita.estado = "salida_registrada"
        visita.salida_registrada_en = datetime.utcnow()
        try:
            db.commit()
            db.refresh(visita)
        except Exception:
            db.rollback()
            raise
    return visita


# ---------------------------------------------------------
# FIX: Crear visita desde PRE-REGISTRO (RESIDENTE)
# Sin transacciones anidadas, sin with db.begin()
# ---------------------------------------------------------
def crear_desde_preregistro(db: Session, data: Any, usuario: Any) -> Visita:

    # tomar condominio + casa_unidad del usuario
    condominio_id = getattr(usuario, "condominio_id", None)
    casa_unidad = getattr(usuario, "casa_unidad", None)

    # helper interno
    def _normalize_str(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        v = str(val).strip()
        return v if v != "" else None

    # normalizar entradas
    nombre_visitante = _normalize_str(getattr(data, "nombre_visitante", None))
    tipo_visita = _normalize_str(getattr(data, "tipo_visita", None))
    vigencia = getattr(data, "fecha_visita", None)

        # Create visita + optional evidencia without opening a new transaction
        try:
            # create Visita record directly on the session
            visita_id = generar_visita_id()
            visita = Visita(
                visita_id=visita_id,
                condominio_id=condominio_id,
                nombre_visitante=nombre_visitante,
                casa_unidad=casa_unidad,
                tipo_visita=tipo_visita,
                vigencia=vigencia,
                estado="pendiente",
            )
            db.add(visita)

            # Collect optional metadata
            metadata = {}
            notas = _normalize_str(getattr(data, "notas", None))
            placa = _normalize_str(getattr(data, "placa", None))
            documento = _normalize_str(getattr(data, "documento", None))
            if notas:
                metadata["notas"] = notas
            if placa:
                metadata["placa"] = placa
            if documento:
                metadata["documento"] = documento

            if metadata:
                # Ensure metadata-only evidencia stores empty strings for required fields
                evidencia = Evidencia(
                    evidencia_id=str(uuid.uuid4()),
                    visita_id=visita_id,
                    categoria="preregistro",
                    sub_tipo="preregistro_metadata",
                    archivo_url="",
                    hash_sha256="",
                    guardia_id=getattr(usuario, "usuario_id", None),
                    metadata_json={**metadata, "created_by": getattr(usuario, "usuario_id", None)},
                )
                db.add(evidencia)

            # commit the current transaction (may be an existing transaction started by dependencies)
            db.commit()

            # refresh visita to get DB-populated fields
            db.refresh(visita)

        except SQLAlchemyError:
            # ensure session is clean for caller
            db.rollback()
            raise

    return visita


# ---------------------------------------------------------
# Consultar visitas del residente
# ---------------------------------------------------------
def obtener_visitas_residente(db: Session, condominio_id: str, casa_unidad: str):
    return (
        db.query(Visita)
        .filter(
            Visita.condominio_id == condominio_id,
            Visita.casa_unidad == casa_unidad,
        )
        .order_by(Visita.vigencia.desc())
        .all()
    )


# ---------------------------------------------------------
# Consultar visitas del condominio
# ---------------------------------------------------------
def obtener_visitas_condominio(db: Session, condominio_id: str):
    return (
        db.query(Visita)
        .filter(Visita.condominio_id == condominio_id)
        .order_by(Visita.vigencia.desc())
        .all()
    )


# ---------------------------------------------------------
# Consultar visita individual
# ---------------------------------------------------------
def obtener_visita(db: Session, visita_id: str):
    return db.query(Visita).filter(Visita.visita_id == visita_id).first()
