from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Any, Optional
import uuid

from ..db.models import Visita, Evidencia
from ..utils.hash_tools import calcular_hash_sha256
from ..utils.file_storage import guardar_archivo
from ..core.config import settings


# ---------------------------------------------------------
# Generador de IDs
# ---------------------------------------------------------
def generar_visita_id() -> str:
    return f"VIS-{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------
# Crear visita (ADMIN_CONDOMINIO)
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
# Actualizar QR
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
# Registrar entrada
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
# Registrar salida
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
# Crear visita desde preregistro (RESIDENTE)
# ---------------------------------------------------------
def crear_desde_preregistro(db: Session, data: Any, usuario: Any) -> Visita:
    """
    Crear una visita desde preregistro.
    Incluye evidencia metadata-only sin archivos (archivo_url='', hash_sha256='').
    Todo se maneja en una sola transacción para evitar commits anidados.
    """

    condominio_id = getattr(usuario, "condominio_id", None)
    casa_unidad = getattr(usuario, "casa_unidad", None)

    def _normalize_str(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        v = str(val).strip()
        return v if v != "" else None

    nombre_visitante = _normalize_str(getattr(data, "nombre_visitante", None))
    tipo_visita = _normalize_str(getattr(data, "tipo_visita", None))
    vigencia = getattr(data, "fecha_visita", None)

    try:
        # Transacción atómica
        with db.begin():

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

            # Metadata opcional
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
                evidencia = Evidencia(
                    evidencia_id=str(uuid.uuid4()),
                    visita_id=visita.visita_id,
                    categoria="preregistro",
                    sub_tipo="preregistro_metadata",
                    archivo_url="",      # ⚠️ Nunca NULL
                    hash_sha256="",      # ⚠️ Nunca NULL
                    guardia_id=getattr(usuario, "usuario_id", None),
                    metadata_json={**metadata, "created_by": getattr(usuario, "usuario_id", None)},
                )
                db.add(evidencia)

        # Refresh fuera de la transacción
        try:
            db.refresh(visita)
        except Exception:
            pass

    except SQLAlchemyError:
        try:
            db.rollback()
        except Exception:
            pass
        raise

    return visita


# ---------------------------------------------------------
# Obtener visitas de residente
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
# Obtener visitas por condominio
# ---------------------------------------------------------
def obtener_visitas_condominio(db: Session, condominio_id: str):
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
    return db.query(Visita).filter(Visita.visita_id == visita_id).first()
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Any, Optional
import uuid

from ..db.models import Visita, Evidencia
from ..utils.hash_tools import calcular_hash_sha256
from ..utils.file_storage import guardar_archivo
from ..core.config import settings


# ---------------------------------------------------------
# Generador de IDs
# ---------------------------------------------------------
def generar_visita_id() -> str:
    return f"VIS-{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------
# Crear visita (ADMIN_CONDOMINIO)
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
# Actualizar QR
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
# Registrar entrada
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
# Registrar salida
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
# Crear visita desde preregistro (RESIDENTE)
# ---------------------------------------------------------
def crear_desde_preregistro(db: Session, data: Any, usuario: Any) -> Visita:
    """
    Crear una visita desde preregistro.
    Incluye evidencia metadata-only sin archivos (archivo_url='', hash_sha256='').
    Todo se maneja en una sola transacción para evitar commits anidados.
    """

    condominio_id = getattr(usuario, "condominio_id", None)
    casa_unidad = getattr(usuario, "casa_unidad", None)

    def _normalize_str(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        v = str(val).strip()
        return v if v != "" else None

    nombre_visitante = _normalize_str(getattr(data, "nombre_visitante", None))
    tipo_visita = _normalize_str(getattr(data, "tipo_visita", None))
    vigencia = getattr(data, "fecha_visita", None)

    try:
        # Transacción atómica
        with db.begin():

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

            # Metadata opcional
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
                evidencia = Evidencia(
                    evidencia_id=str(uuid.uuid4()),
                    visita_id=visita.visita_id,
                    categoria="preregistro",
                    sub_tipo="preregistro_metadata",
                    archivo_url="",      # ⚠️ Nunca NULL
                    hash_sha256="",      # ⚠️ Nunca NULL
                    guardia_id=getattr(usuario, "usuario_id", None),
                    metadata_json={**metadata, "created_by": getattr(usuario, "usuario_id", None)},
                )
                db.add(evidencia)

        # Refresh fuera de la transacción
        try:
            db.refresh(visita)
        except Exception:
            pass

    except SQLAlchemyError:
        try:
            db.rollback()
        except Exception:
            pass
        raise

    return visita


# ---------------------------------------------------------
# Obtener visitas de residente
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
# Obtener visitas por condominio
# ---------------------------------------------------------
def obtener_visitas_condominio(db: Session, condominio_id: str):
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
    return db.query(Visita).filter(Visita.visita_id == visita_id).first()
