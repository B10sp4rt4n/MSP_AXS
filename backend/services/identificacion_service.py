"""Private ID pairs. No OCR, public delivery or local-disk fallback."""
import hashlib
import io
import logging
import os
import uuid
from urllib.parse import urlparse

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from backend.db.core import Evidencia, Visita
from backend.services.event_outbox import encolar_evento

MAX_BYTES = 8 * 1024 * 1024
logger = logging.getLogger(__name__)


def normalize_image(upload):
    data = upload.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Cada foto debe pesar como máximo 8 MB")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError()
            if source.width * source.height > 25_000_000:
                raise ValueError()
            if min(source.size) < 480:
                raise HTTPException(422, "Foto demasiado pequeña; vuelve a capturar con mayor resolución")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2048, 2048))
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=90)
            return out.getvalue()  # removes EXIF/location metadata
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Usa una foto JPEG, PNG o WebP válida de hasta 25 megapíxeles")


class PrivateIdentityStore:
    def __init__(self):
        if os.getenv("AXS_ID_PHOTOS_ENABLED", "false").lower() != "true":
            raise HTTPException(503, "La captura de identificaciones aún no está habilitada")
        self.token = os.getenv("BLOB_READ_WRITE_TOKEN")
        if not self.token:
            raise HTTPException(503, "Vercel Blob privado no está configurado; conserva las fotos y reintenta")

    def put(self, key, data):
        from vercel import blob
        result = blob.put(key, data, access="private", content_type="image/jpeg",
                          add_random_suffix=False, overwrite=False, token=self.token)
        parsed = urlparse(result.url)
        if (result.pathname != key or parsed.scheme != "https"
                or not (parsed.hostname or "").endswith(".private.blob.vercel-storage.com")):
            raise RuntimeError("Private storage response mismatch")

    def delete(self, key):
        from vercel import blob
        blob.delete(key, token=self.token)

    def read(self, key):
        from vercel import blob
        try:
            result = blob.get(key, access="private", token=self.token, timeout=20, use_cache=False)
        except blob.BlobNotFoundError:
            raise HTTPException(404, "Foto no encontrada")
        if result is None or result.status_code == 404:
            raise HTTPException(404, "Foto no encontrada")
        if result.status_code != 200:
            raise HTTPException(503, "El proveedor no confirmó la lectura de la foto")
        return result.content


def list_pairs(db, visita_id):
    return db.query(Evidencia).filter_by(visita_id=visita_id, categoria="identificacion").order_by(Evidencia.id).all()


def describe(rows):
    return [{"evidencia_id": row.evidencia_id, "lado": row.sub_tipo,
             "nombre": row.metadata_json["nombre"], "captura_id": row.metadata_json["captura_id"],
             "created_at": row.created_at.isoformat() + "Z"} for row in rows]


def save_pair(db, visita, usuario, nombre, captura_id, frente, reverso, audit):
    nombre = " ".join(nombre.split())
    if not 2 <= len(nombre) <= 200:
        raise HTTPException(422, "Escribe un nombre completo de 2 a 200 caracteres")
    try:
        captura_id = str(uuid.UUID(captura_id))
    except ValueError:
        raise HTTPException(422, "Identificador de captura inválido")
    images = {"ine_frente": normalize_image(frente), "ine_reverso": normalize_image(reverso)}
    hashes = {side: hashlib.sha256(data).hexdigest() for side, data in images.items()}
    # Serialize pair creation/retries for this visit, also under PostgreSQL RLS.
    db.query(Visita).filter_by(visita_id=visita.visita_id,
        condominio_id=visita.condominio_id).with_for_update().one()
    existing = list_pairs(db, visita.visita_id)
    if existing:
        from backend.services.identificacion_conservacion import assert_readable, access_record
        assert_readable(access_record(db, visita))
        if any((row.metadata_json or {}).get("purge_status") for row in existing):
            raise HTTPException(409, "Esta identificación fue retirada; no se admite otra captura para esta visita")
        if len(existing) == 2 and all(row.metadata_json.get("captura_id") == captura_id
                and row.metadata_json.get("nombre") == nombre
                and row.hash_sha256 == hashes.get(row.sub_tipo) for row in existing):
            return describe(existing)
        raise HTTPException(409, "Esta visita ya tiene una identificación guardada; consulta el registro")
    store = PrivateIdentityStore()
    keys = []
    rows = []
    try:
        for side, data in images.items():
            eid = str(uuid.uuid4())
            key = f"axs-identificaciones/{hashlib.sha256(visita.condominio_id.encode()).hexdigest()[:24]}/{eid}"
            keys.append(key)  # also clean up an upload whose response times out
            store.put(key, data)
            row = Evidencia(evidencia_id=eid, visita_id=visita.visita_id,
                guardia_id=usuario.usuario_id, categoria="identificacion", sub_tipo=side,
                archivo_url=key, hash_sha256=hashes[side], metadata_json={
                    "storage": "vercel_blob_private", "nombre": nombre,
                    "captura_id": captura_id, "condominio_id": visita.condominio_id})
            db.add(row)
            rows.append(row)
        encolar_evento(db, visita.condominio_id, visita.visita_id, audit,
                      metadata={"evidencia_ids": [r.evidencia_id for r in rows], "captura_id": captura_id})
        db.flush()
        from backend.services.identificacion_conservacion import enroll
        enroll(db, visita, rows, audit)
        result = describe(rows)
        db.commit()
        return result
    except Exception:
        db.rollback()
        for key in keys:
            try:
                store.delete(key)
            except Exception:
                logger.error("ID photo rollback cleanup required: %s", key)
        raise HTTPException(503, "No se confirmó el guardado de las dos fotos; conserva las capturas y reintenta")
