from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Any, Optional
import uuid

from backend.db.core import Visita, Evidencia, Casa
from fastapi import HTTPException
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
def crear_visita(db: Session, data: Any, condominio_id: str, casa_unidad: Optional[str] = None, *, entrada_inmediata: bool = False, destino: dict | None = None) -> Visita:
    visita_id = generar_visita_id()
    visita = Visita(
        visita_id=visita_id,
        condominio_id=condominio_id,
        nombre_visitante=getattr(data, "nombre_visitante", None),
        casa_unidad=casa_unidad,
        tipo_visita=getattr(data, "tipo_visita", None),
        vigencia=getattr(data, "vigencia", None),
        estado="entrada_registrada" if entrada_inmediata else "pendiente",
        entrada_registrada_en=datetime.utcnow() if entrada_inmediata else None,
        **(destino or {}),
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
def crear_desde_preregistro(db: Session, data: Any, usuario: Any, *, destino: dict | None = None, casa_label: str | None = None) -> Visita:
    """
    Crear una visita desde preregistro.
    Incluye evidencia metadata-only sin archivos (archivo_url='', hash_sha256='').
    Todo se maneja en una sola transacción para evitar commits anidados.
    """

    condominio_id = getattr(usuario, "condominio_id", None)
    casa_unidad = getattr(usuario, "casa_unidad", None)

    if not condominio_id:
        from fastapi import HTTPException
        raise HTTPException(400, detail="El residente no tiene condominio asignado")
    if not casa_unidad:
        from fastapi import HTTPException
        raise HTTPException(400, detail="El residente no tiene casa asignada. Contacta al administrador.")

    def _normalize_str(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        v = str(val).strip()
        return v if v != "" else None

    nombre_visitante = _normalize_str(getattr(data, "nombre_visitante", None))
    tipo_visita = _normalize_str(getattr(data, "tipo_visita", None))
    vigencia = getattr(data, "fecha_visita", None)

    try:
        visita_id = generar_visita_id()
        visita = Visita(
            visita_id=visita_id,
            condominio_id=condominio_id,
            nombre_visitante=nombre_visitante,
            casa_unidad=casa_label or casa_unidad,
            tipo_visita=tipo_visita,
            vigencia=vigencia,
            estado="pendiente",
            **(destino or {}),
        )
        db.add(visita)
        db.flush()  # Persist visita row so FK in evidencias resolves

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

        db.commit()
        db.refresh(visita)

    except SQLAlchemyError:
        db.rollback()
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
            or_(Visita.destino_tipo == "vivienda", Visita.destino_tipo.is_(None)),
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


VIVIENDAS = {"casa", "depto", "local"}
COMUNES = {"administracion", "mantenimiento", "area_comun"}


def resolver_destino(db, condominio_id, *, destino_id=None, casa_unidad=None,
                     motivo=None, residente=False):
    """El texto histórico es una etiqueta; el catálogo decide el destino nuevo."""
    if destino_id == "OTRO":
        reason = (motivo or "").strip()
        if residente or len(reason) < 5 or len(reason) > 500:
            raise HTTPException(400, "Otro destino requiere un motivo de 5 a 500 caracteres")
        return "Otro destino", {"destino_id": None, "destino_tipo": "otro", "destino_motivo": reason}
    query = db.query(Casa).filter(Casa.condominio_id == condominio_id)
    if destino_id:
        query = query.filter(Casa.casa_id == destino_id)
    elif casa_unidad:
        # Compatibilidad limitada: sólo un número exacto existente en catálogo.
        query = query.filter(Casa.numero == casa_unidad.strip())
    else:
        raise HTTPException(400, "Selecciona un destino del catálogo")
    candidates = query.all()
    if len(candidates) != 1:
        raise HTTPException(400, "Destino no encontrado en el catálogo de este condominio")
    casa = candidates[0]
    allowed = VIVIENDAS if residente else VIVIENDAS | COMUNES
    if casa.tipo not in allowed:
        raise HTTPException(400, "El destino no es una vivienda válida" if residente else "Tipo de destino inválido")
    return casa.numero, {"destino_id": casa.casa_id, "destino_tipo": "vivienda" if casa.tipo in VIVIENDAS else "comun",
                         "destino_motivo": None}
