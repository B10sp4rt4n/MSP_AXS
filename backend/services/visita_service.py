from sqlalchemy.orm import Session
from ..db.models import Visita
from datetime import datetime
import uuid
from typing import Any, Optional
from ..db.models import Evidencia
from ..utils.hash_tools import calcular_hash_sha256
from ..utils.file_storage import guardar_archivo
from ..core.config import settings
from sqlalchemy.exc import SQLAlchemyError


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

    def _normalize_str(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        v = str(val).strip()
        return v if v != "" else None

    # Normalize inputs
    nombre_visitante = _normalize_str(getattr(data, "nombre_visitante", None))
    tipo_visita = _normalize_str(getattr(data, "tipo_visita", None))
    vigencia = getattr(data, "fecha_visita", None)

    # Use a transaction to ensure atomic creation of visita + metadata evidencia
    try:
        with db.begin():
            # create Visita record
            visita = crear_visita(db, type("T", (), {
                "nombre_visitante": nombre_visitante,
                "tipo_visita": tipo_visita,
                "vigencia": vigencia,
            })(), condominio_id=condominio_id, casa_unidad=casa_unidad)

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
                    visita_id=visita.visita_id,
                    categoria="preregistro",
                    sub_tipo="preregistro_metadata",
                    archivo_url="",
                    hash_sha256="",
                    guardia_id=getattr(usuario, "usuario_id", None),
                    metadata_json={**metadata, "created_by": getattr(usuario, "usuario_id", None)},
                )
                db.add(evidencia)

        # refresh visita to get DB-populated fields
        try:
            db.refresh(visita)
        except Exception:
            # non-fatal if refresh fails
            pass

    except SQLAlchemyError:
        # ensure session is clean for caller
        try:
            db.rollback()
        except Exception:
            pass
        raise

    return visita


from ..db.models import Visita
from sqlalchemy.orm import Session


# ---------------------------------------------------------
# Visitas de un residente (condominio + casa_unidad)
# ---------------------------------------------------------
def obtener_visitas_residente(
    db: Session,
    condominio_id: str,
    casa_unidad: str,
):
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
# Visitas por condominio (Admin y Guardia)
# ---------------------------------------------------------
def obtener_visitas_condominio(
    db: Session,
    condominio_id: str,
):
    return (
        db.query(Visita)
        .filter(Visita.condominio_id == condominio_id)
        .order_by(Visita.vigencia.desc())
        .all()
    )


# ---------------------------------------------------------
# Obtener visita individual
# ---------------------------------------------------------
def obtener_visita(db: Session, visita_id: str):
    return (
        db.query(Visita)
        .filter(Visita.visita_id == visita_id)
        .first()
    )
