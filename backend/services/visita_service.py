from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from typing import Any, Optional
import uuid

from backend.db.core import Visita, Evidencia, Casa
from backend.services.event_outbox import encolar_visita
from backend.services.reglas_acceso import validar_reglas, obtener_reglas
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
def crear_visita(db: Session, data: Any, condominio_id: str, casa_unidad: Optional[str] = None, *, entrada_inmediata: bool = False, destino: dict | None = None, auditoria: dict | None = None, autorizador_id: str | None = None) -> Visita:
    proposito = (getattr(data, "proposito", None) or "").strip() or None
    validar_reglas(db, condominio_id, data.tipo_visita, proposito, entrada=entrada_inmediata)
    visita_id = generar_visita_id()
    visita = Visita(
        visita_id=visita_id,
        condominio_id=condominio_id,
        nombre_visitante=getattr(data, "nombre_visitante", None),
        proposito=proposito,
        autorizada_por=autorizador_id if not entrada_inmediata else None,
        autorizada_en=datetime.utcnow() if autorizador_id and not entrada_inmediata else None,
        casa_unidad=casa_unidad,
        tipo_visita=getattr(data, "tipo_visita", None),
        vigencia=getattr(data, "vigencia", None),
        estado="entrada_registrada" if entrada_inmediata else "pendiente",
        entrada_registrada_en=datetime.utcnow() if entrada_inmediata else None,
        **(destino or {}),
    )
    try:
        db.add(visita)
        if auditoria:
            db.flush()
            encolar_visita(db, visita, auditoria)
        db.commit()
        db.refresh(visita)
    except Exception:
        db.rollback()
        raise
    return visita


# ---------------------------------------------------------
# Actualizar QR
# ---------------------------------------------------------
def actualizar_qr(db: Session, visita_id: str, token: str, qr_vigencia: datetime, *, auditoria: dict | None = None) -> Optional[Visita]:
    query = db.query(Visita).filter(
        Visita.visita_id == visita_id,
        Visita.estado.in_(["pendiente", "activa"]),
        Visita.entrada_registrada_en.is_(None),
        Visita.salida_registrada_en.is_(None),
    )
    return _guardar_transicion(db, visita_id, query,
        {Visita.qr_token: token, Visita.qr_vigencia: qr_vigencia},
        "La visita cambió de estado; no se puede actualizar su QR", auditoria=auditoria)


def _guardar_transicion(db, visita_id, query, values, conflict, *, auditoria=None):
    """Compare-and-set: el estado se comprueba dentro del UPDATE, no en Python.

    Un reintento o una solicitud con una instancia ORM vieja nunca sobrescribe
    el primer registro. El contexto RLS de la sesión sigue siendo obligatorio.
    """
    try:
        changed = query.update(values, synchronize_session=False)
        if changed != 1:
            raise HTTPException(400, conflict)
        visita = db.query(Visita).populate_existing().filter(
            Visita.visita_id == visita_id,
        ).one()
        if auditoria:
            encolar_visita(db, visita, auditoria)
        db.commit()
        db.refresh(visita)
        return visita
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------
# Registrar entrada
# ---------------------------------------------------------
def registrar_entrada(db: Session, visita_id: str, *, qr_token: str | None = None, auditoria: dict | None = None) -> Visita:
    visita = db.query(Visita).filter(Visita.visita_id == visita_id).one_or_none()
    if visita is None:
        raise HTTPException(404, "Visita no encontrada")
    obtener_reglas(db, visita.condominio_id, bloquear=True)
    db.refresh(visita)
    validar_reglas(db, visita.condominio_id, visita.tipo_visita, visita.proposito,
                   entrada=True, autorizada_por=visita.autorizada_por, autorizada_en=visita.autorizada_en,
                   fecha_visita=visita.vigencia)
    now = datetime.utcnow()
    query = db.query(Visita).filter(
        Visita.visita_id == visita_id,
        Visita.estado.in_(["pendiente", "activa"]),
        Visita.entrada_registrada_en.is_(None),
        Visita.salida_registrada_en.is_(None),
    )
    if qr_token is None:
        query = query.filter(Visita.qr_token.is_(None))
        conflict = "La visita ya tiene entrada, requiere QR o está finalizada"
    else:
        # Revalidar token y ventana en el UPDATE evita usar un QR que fue
        # sustituido, cancelado o expiró después de las comprobaciones HTTP.
        query = query.filter(
            Visita.qr_token == qr_token,
            Visita.qr_vigencia > now,
            or_(Visita.vigencia.is_(None), Visita.vigencia > now - timedelta(minutes=60)),
            or_(Visita.vigencia.is_(None), Visita.vigencia <= now + timedelta(minutes=30)),
        )
        conflict = "QR ya utilizado o sin autorización vigente"
    return _guardar_transicion(db, visita_id, query,
        {Visita.estado: "entrada_registrada", Visita.entrada_registrada_en: now}, conflict, auditoria=auditoria)


# ---------------------------------------------------------
# Registrar salida
# ---------------------------------------------------------
def registrar_salida(db: Session, visita_id: str, *, auditoria: dict | None = None) -> Visita:
    query = db.query(Visita).filter(
        Visita.visita_id == visita_id,
        Visita.estado == "entrada_registrada",
        Visita.entrada_registrada_en.is_not(None),
        Visita.salida_registrada_en.is_(None),
    )
    return _guardar_transicion(db, visita_id, query,
        {Visita.estado: "salida_registrada", Visita.salida_registrada_en: datetime.utcnow()},
        "La visita no tiene entrada, ya tiene salida o cambió de estado", auditoria=auditoria)


def cancelar_visita(db: Session, visita_id: str, *, estado_esperado: str, auditoria: dict | None = None) -> Visita:
    if estado_esperado in ["cancelada", "salida_registrada"]:
        raise HTTPException(400, "La visita ya está finalizada")
    query = db.query(Visita).filter(
        Visita.visita_id == visita_id, Visita.estado == estado_esperado,
    )
    return _guardar_transicion(db, visita_id, query, {Visita.estado: "cancelada"},
        "La visita cambió de estado; vuelve a consultar antes de cancelar", auditoria=auditoria)


# ---------------------------------------------------------
# Crear visita desde preregistro (RESIDENTE)
# ---------------------------------------------------------
def crear_desde_preregistro(db: Session, data: Any, usuario: Any, *, destino: dict | None = None, casa_label: str | None = None, auditoria: dict | None = None, generar_qr: bool = False) -> Visita:
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
    proposito = _normalize_str(getattr(data, "proposito", None))
    validar_reglas(db, condominio_id, tipo_visita, proposito)
    vigencia = getattr(data, "fecha_visita", None)

    try:
        visita_id = generar_visita_id()
        visita = Visita(
            visita_id=visita_id,
            condominio_id=condominio_id,
            nombre_visitante=nombre_visitante,
            proposito=proposito,
            autorizada_por=usuario.usuario_id,
            autorizada_en=datetime.utcnow(),
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

        if generar_qr:
            from backend.services import qr_service
            qr_data = qr_service.generar_qr_para_visita(visita_id, fecha_visita=vigencia)
            visita.qr_token = qr_data["token"]
            visita.qr_vigencia = qr_data["qr_vigencia"]
        if auditoria:
            encolar_visita(db, visita, auditoria)
            if generar_qr:
                encolar_visita(db, visita, {**auditoria, "entidad": "qr", "accion": "crear",
                                          "motivo": "QR generado en preregistro"})
        db.commit()
        db.refresh(visita)

    except Exception:
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
