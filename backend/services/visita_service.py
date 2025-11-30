from sqlalchemy.orm import Session
from ..db.models import Visita
from datetime import datetime
import uuid
from typing import Any, Optional
from ..db.models import Evidencia
from ..utils.hash_tools import calcular_hash_sha256
from ..utils.file_storage import guardar_archivo


def generar_visita_id() -> str:
    return f"VIS-{uuid.uuid4().hex[:10]}"


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


def crear_desde_preregistro(db: Session, data: Any, usuario: Any) -> Visita:
    """Crear una visita desde preregistro (usado por RESIDENTE).

    No se añaden columnas nuevas: datos opcionales (notas, placa, documento)
    se guardan como evidencia de tipo 'preregistro' en `Evidencia.metadata_json`.
    """
    # Usar casa_unidad y condominio del usuario si están disponibles
    condominio_id = getattr(usuario, "condominio_id", None)
    casa_unidad = getattr(usuario, "casa_unidad", None)

    # Reutilizar crear_visita para crear la entidad Visita
    visita = crear_visita(db, type("T", (), {
        "nombre_visitante": data.nombre_visitante,
        "tipo_visita": data.tipo_visita,
        "vigencia": data.fecha_visita,
    })(), condominio_id=condominio_id, casa_unidad=casa_unidad)

    # Si hay metadatos opcionales, guardarlos en Evidencia como preregistro
    metadata = {}
    if getattr(data, "notas", None):
        metadata["notas"] = data.notas
    if getattr(data, "placa", None):
        metadata["placa"] = data.placa
    if getattr(data, "documento", None):
        metadata["documento"] = data.documento

    if metadata:
        evidencia = Evidencia(
            evidencia_id=str(uuid.uuid4()),
            visita_id=visita.visita_id,
            categoria="preregistro",
            sub_tipo="preregistro_metadata",
            archivo_url="",
            hash_sha256="",
            guardia_id=getattr(usuario, "usuario_id", None),
            metadata_json={**metadata, "created_by": getattr(usuario, "usuario_id", None)},
        )
        try:
            db.add(evidencia)
            db.commit()
            db.refresh(evidencia)
        except Exception:
            db.rollback()
            raise

    return visita
