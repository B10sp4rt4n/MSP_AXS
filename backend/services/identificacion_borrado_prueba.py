"""Development-only purge of two allowlisted synthetic fixture pairs. No scheduler."""
import hashlib
import os
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from backend.db.core import Evidencia
from backend.services import identificacion_service as identity_service
from backend.services.event_outbox import encolar_evento

LABEL = "AXS documento ficticio - prueba automatica"
EXPECTED_HASHES = dict.fromkeys(("ine_frente", "ine_reverso"), "5d4f9493923a4d6269234e24c7b591df4f65fe00313ccccbddd95ecf00e23bab")
FIXTURES = {
    "axs_demo_condo_a": {"visita_id": "VIS-4ced9e365c", "actor": "axs_demo_admin_a", "nombre": "AXS AUTO development 20261003-visit-v1 A", "captura_id": "ec042124-9fbf-4b1a-b5fd-792b26dde121"},
    "axs_demo_condo_b": {"visita_id": "VIS-7dad7600d5", "actor": "axs_demo_admin_b", "nombre": "AXS AUTO development 20261003-visit-v1 B", "captura_id": "c51320c8-78c0-42a1-9d1f-26a29940222c"},
}


def gate():
    if (os.getenv("APP_ENV") != "development"
            or os.getenv("NEON_DEV_ENDPOINT") != "ep-withered-resonance-b59tusv3"
            or os.getenv("AXS_ID_PHOTOS_TEST_PURGE_ENABLED", "false").lower() != "true"):
        raise HTTPException(404, "Prueba no disponible")


def read_if_present(store, key):
    try:
        return store.read(key)
    except HTTPException as error:
        if error.status_code == 404:
            return None
        raise


def status(rows):
    meta = rows[0].metadata_json
    return {"estado": "eliminada", "evidencias": [], "fotos_eliminadas": len(rows),
            "operacion_id": meta["purge_id"], "eliminada_en": meta["purged_at"],
            "evento_id": meta["purge_event_uid"], "solo_prueba": True, "proveedor_verificado_ausente": True}


def purge(db, usuario, authorize, context):
    gate()
    visit = authorize()
    tenant, visit_id = visit.condominio_id, visit.visita_id
    fixture = FIXTURES.get(tenant)
    if (not fixture or fixture["visita_id"] != visit_id or fixture["actor"] != usuario.usuario_id
            or visit.nombre_visitante != fixture["nombre"] or visit.estado != "cancelada"):
        raise HTTPException(409, "Sólo se permite borrar el par ficticio autorizado de esta prueba")
    rows = db.query(Evidencia).filter_by(visita_id=visit_id, categoria="identificacion").with_for_update().all()
    if len(rows) != 2 or {row.sub_tipo for row in rows} != {"ine_frente", "ine_reverso"}:
        raise HTTPException(409, "La prueba requiere un par completo")
    if all((row.metadata_json or {}).get("purge_status") == "purged"
           and row.metadata_json.get("synthetic_verified") is True for row in rows):
        return status(rows)
    phases = {(row.metadata_json or {}).get("purge_status") for row in rows}
    if phases not in ({None}, {"pending"}):
        raise HTTPException(409, "Estado de borrado inconsistente")
    pending = phases == {"pending"}
    snapshots = []
    for row in rows:
        meta = row.metadata_json or {}
        expected_key = f"axs-identificaciones/{hashlib.sha256(tenant.encode()).hexdigest()[:24]}/{row.evidencia_id}"
        if (meta.get("nombre") != LABEL or meta.get("captura_id") != fixture["captura_id"]
                or meta.get("condominio_id") != tenant or meta.get("storage") != "vercel_blob_private"
                or row.hash_sha256 != EXPECTED_HASHES[row.sub_tipo] or row.archivo_url != expected_key):
            raise HTTPException(409, "La evidencia no coincide con la imagen ficticia autorizada")
        snapshots.append((row.evidencia_id, row.archivo_url, row.sub_tipo))
    store = identity_service.PrivateIdentityStore()
    for eid, key, side in snapshots:
        data = read_if_present(store, key)
        if data is None and not pending:
            raise HTTPException(409, "El par ficticio no está íntegro; requiere revisión")
        if data is not None and hashlib.sha256(data).hexdigest() != EXPECTED_HASHES[side]:
            raise HTTPException(409, "El contenido no es la imagen ficticia autorizada")
    operation_id = rows[0].metadata_json.get("purge_id") if pending else str(uuid.uuid4())
    if pending and (not operation_id or any(row.metadata_json.get("purge_id") != operation_id for row in rows)):
        raise HTTPException(409, "Operación de borrado inconsistente")
    if not pending:
        try:
            for row in rows:
                row.metadata_json = {**row.metadata_json, "purge_status": "pending", "purge_id": operation_id, "synthetic_verified": True}
            encolar_evento(db, tenant, visit_id, {**context, "accion": "solicitar_eliminacion_identificacion_prueba"},
                          resultado="pendiente", metadata={"operacion_id": operation_id, "fotos": 2, "solo_prueba": True})
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(503, "No se conservó la intención de borrado; no se borraron fotos")
    try:
        # Recheck scope after committing the durable intent; normal reads now deny delivery.
        visit = authorize()
        current_rows = db.query(Evidencia).filter_by(visita_id=visit_id, categoria="identificacion").with_for_update().all()
        if len(current_rows) != 2 or any(row.metadata_json.get("purge_id") != operation_id for row in current_rows):
            raise RuntimeError("Deletion record changed")
        if all(row.metadata_json.get("purge_status") == "purged" for row in current_rows):
            return status(current_rows)
        if any(row.metadata_json.get("purge_status") != "pending" for row in current_rows):
            raise RuntimeError("Deletion phase changed")
        for eid, key, side in snapshots:
            data = read_if_present(store, key)
            if data is not None:
                if hashlib.sha256(data).hexdigest() != EXPECTED_HASHES[side]:
                    raise HTTPException(409, "El contenido cambió; la prueba no permite borrarlo")
                store.delete(key)
            if read_if_present(store, key) is not None:
                raise RuntimeError("Deletion not confirmed")
        visit = authorize()
        rows = db.query(Evidencia).filter_by(visita_id=visit_id, categoria="identificacion").with_for_update().all()
        if len(rows) != 2 or any(row.metadata_json.get("purge_id") != operation_id for row in rows):
            raise RuntimeError("Deletion record changed")
        deleted_at = datetime.now(timezone.utc).isoformat()
        event_uid = encolar_evento(db, tenant, visit_id, {**context, "accion": "eliminar_identificacion_prueba"},
                                  metadata={"operacion_id": operation_id, "fotos": 2, "solo_prueba": True, "estado": visit.estado})
        for row in rows:
            row.archivo_url = None
            row.hash_sha256 = None
            row.metadata_json = {"storage": "vercel_blob_private", "condominio_id": tenant,
                                 "purge_status": "purged", "purge_id": operation_id, "purged_at": deleted_at,
                                 "purge_event_uid": event_uid, "synthetic_verified": True}
        result = status(rows)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(503, "Borrado de prueba pendiente; reintenta la misma operación. No se confirmó la eliminación completa")
