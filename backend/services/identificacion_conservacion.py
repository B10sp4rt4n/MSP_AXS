"""Durable retention pilot. Enrollment/deletion are restricted to synthetic DEV fixtures.

Read enforcement is independent of the worker switch, so stopping a worker never
restores expired access. No existing IDs are backfilled or production enabled.
"""
import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import or_
from backend.db.core import IdentityRetention, Evidencia, Visita
from backend.core.tenant.context import _set_postgres_tenant
from backend.core.event.registry import hash_session_token
from backend.services.event_outbox import encolar_evento
from backend.services import identificacion_service as identity
from backend.services.qr_service import as_utc

VERSION = "30d-dev-synthetic-v1"
TENANTS = {"axs_demo_condo_a", "axs_demo_condo_b"}
VISIT_PREFIX = "AXS RETENTION development 20261012 "
LABEL = "AXS documento ficticio - prueba automatica"
SYNTHETIC_HASH = "5d4f9493923a4d6269234e24c7b591df4f65fe00313ccccbddd95ecf00e23bab"
logger = logging.getLogger("axs.identity_retention")


def utcnow():
    return datetime.utcnow()


def naive(value):
    return as_utc(value).replace(tzinfo=None)


def development():
    return os.getenv("APP_ENV") == "development" and os.getenv("NEON_DEV_ENDPOINT") == "ep-withered-resonance-b59tusv3"


def schema_enabled():
    return development() and os.getenv("AXS_ID_RETENTION_SCHEMA_ENABLED", "false").lower() == "true"


def pilot_enabled():
    return schema_enabled() and os.getenv("AXS_ID_RETENTION_PILOT_ENABLED", "false").lower() == "true"


def require_pilot():
    if not pilot_enabled():
        raise HTTPException(404, "Piloto no disponible")


def lookup(db, visit, *, lock=False):
    if not schema_enabled():
        return None
    query = db.query(IdentityRetention).filter_by(visita_id=visit.visita_id, condominio_id=visit.condominio_id)
    return (query.with_for_update() if lock else query).first()


def expiry(captured, visit):
    captured = naive(captured)
    exit_at = naive(visit.salida_registrada_en) if visit.salida_registrada_en else None
    if (exit_at and (exit_at < captured or visit.estado != "salida_registrada")) or (visit.estado == "salida_registrada" and not exit_at):
        raise HTTPException(409, "Fechas de visita inconsistentes; revisión requerida")
    base = exit_at or captured
    return base, base + timedelta(days=30)


def enroll(db, visit, rows, context):
    # Automatic pilot enrollment only for exact synthetic fixture names/content.
    if not pilot_enabled() or visit.condominio_id not in TENANTS or not (visit.nombre_visitante or "").startswith(VISIT_PREFIX):
        return None
    if len(rows) != 2 or {r.sub_tipo for r in rows} != {"ine_frente", "ine_reverso"} or any(
            r.metadata_json.get("nombre") != LABEL or r.hash_sha256 != SYNTHETIC_HASH for r in rows):
        raise HTTPException(409, "El piloto admite únicamente las imágenes ficticias verificadas")
    captured = max(naive(r.created_at) for r in rows)
    base, expires = expiry(captured, visit)
    row = IdentityRetention(visita_id=visit.visita_id, condominio_id=visit.condominio_id,
        captura_id=rows[0].metadata_json["captura_id"], policy_version=VERSION,
        captured_at=captured, base_at=base, expires_at=expires, state="active", attempts=0,
        next_attempt_at=expires, snapshots=[{"id":r.evidencia_id,"key":r.archivo_url,"side":r.sub_tipo,"hash":r.hash_sha256} for r in rows],
        audit_context={**context, "entidad":"visita"})
    db.add(row)
    event(db, row, "establecer_conservacion_identificacion", metadata={"version":VERSION,"vencimiento":expires.isoformat()+"Z"})
    return row


def state(row, now=None):
    if not row:
        return None
    now = now or utcnow()
    if row.state == "purged": return "eliminada"
    if row.state in {"pending", "review"}: return "eliminando" if row.state == "pending" else "revision"
    if row.hold_until and row.hold_until > now: return "excepcion"
    return "vencida" if row.expires_at <= now else "vigente"


def describe(row, now=None):
    if not row: return None
    return {"version":row.policy_version,"estado":state(row,now),"vencimiento_en":row.expires_at.isoformat()+"Z",
        "excepcion_hasta":row.hold_until.isoformat()+"Z" if row.hold_until else None,
        "intentos":row.attempts,"requiere_atencion":row.state == "review" or row.attempts >= 5,
        "proximo_intento_en":row.next_attempt_at.isoformat()+"Z" if row.state == "pending" else None,
        "eliminada_en":row.purged_at.isoformat()+"Z" if row.purged_at else None,"solo_prueba":True}


def assert_readable(row, now=None):
    if state(row,now) in {"vencida","eliminando","eliminada","revision"}:
        raise HTTPException(410, "La identificación venció o fue retirada", headers={"Cache-Control":"private, no-store"})


def event(db, row, action, *, result="exito", metadata=None):
    context = row.audit_context if action == "establecer_conservacion_identificacion" else {"identity_id":"axs:identity-retention-worker","session_hash":hash_session_token("internal-retention-worker"),"entidad":"visita","motivo":"Conservación automática del piloto ficticio"}
    return encolar_evento(db,row.condominio_id,row.visita_id,
        {**context,"accion":action},resultado=result,
        metadata={"version":row.policy_version,"solo_prueba":True,"operacion_id":row.operation_id,**(metadata or {})})


def set_hold(db, visit, context, *, until=None, owner=None, incident=None, reason=None):
    require_pilot()
    row=lookup(db,visit,lock=True)
    if not row or row.policy_version != VERSION or row.condominio_id not in TENANTS:
        raise HTTPException(404,"Identificación fuera del piloto")
    now=utcnow()
    if row.state != "active":
        raise HTTPException(409,"El borrado ya comenzó; no se puede conservar ni restaurar")
    if until is not None:
        until=naive(until)
        if until <= now or not all(v and v.strip() for v in (owner,incident,reason)):
            raise HTTPException(422,"Indica responsable, incidencia, motivo y una fecha límite futura")
        row.hold_until,row.hold_owner,row.hold_incident,row.hold_reason=until,owner.strip(),incident.strip(),reason.strip()
        action="conservar_identificacion_por_incidencia"
        details={"responsable":owner.strip(),"incidencia":incident.strip(),"motivo":reason.strip()}
    else:
        details={"responsable":row.hold_owner,"incidencia":row.hold_incident,"motivo":row.hold_reason}
        row.hold_until=row.hold_owner=row.hold_incident=row.hold_reason=None
        action="liberar_conservacion_identificacion"
    # Exception details stay in the scoped row; no ID name or storage references in audit.
    encolar_evento(db,visit.condominio_id,visit.visita_id,{**context,"entidad":"visita","accion":action},
        metadata={"hasta":until.isoformat()+"Z" if until else None,"solo_prueba":True,**details})
    result=describe(row,now)
    db.commit()
    return result


def refresh_expiry(db, row, visit, now):
    # A late exit never restores access; pending claims freeze the policy date.
    if row.state != "active" or row.expires_at <= now: return
    base, expires=expiry(row.captured_at,visit)
    if base != row.base_at:
        row.base_at,row.expires_at,row.next_attempt_at=base,expires,expires
        event(db,row,"actualizar_vencimiento_identificacion",metadata={"vencimiento":expires.isoformat()+"Z"})


def access_record(db, visit):
    row=lookup(db,visit,lock=True)
    if row and row.state == "active" and row.expires_at > utcnow():
        original=row.base_at
        try:
            refresh_expiry(db,row,visit,utcnow())
        except HTTPException:
            row.state="review"
            event(db,row,"revisar_conservacion_identificacion",result="pendiente")
        if row.base_at != original or row.state == "review":
            db.commit()
    return row


def claim(db, tenant, *, now=None, limit=100, visit_id=None):
    require_pilot()
    if tenant not in TENANTS: return []
    now=now or utcnow()
    _set_postgres_tenant(db,tenant)
    query=db.query(IdentityRetention).filter(IdentityRetention.condominio_id==tenant,
        IdentityRetention.policy_version==VERSION, IdentityRetention.state.in_(["active","pending"]),
        IdentityRetention.next_attempt_at<=now,
        or_(IdentityRetention.hold_until.is_(None),IdentityRetention.hold_until<=now),
        or_(IdentityRetention.claim_until.is_(None),IdentityRetention.claim_until<=now),
    )
    if visit_id is not None: query=query.filter(IdentityRetention.visita_id==visit_id)
    rows=query.order_by(IdentityRetention.next_attempt_at,IdentityRetention.visita_id).limit(min(limit,100)).with_for_update(skip_locked=True).all()
    claims=[]
    for row in rows:
        visit=db.query(Visita).filter_by(visita_id=row.visita_id,condominio_id=tenant).one()
        try:
            refresh_expiry(db,row,visit,now)
        except HTTPException:
            row.state="review"
            event(db,row,"revisar_conservacion_identificacion",result="pendiente")
            continue
        if row.expires_at>now: continue
        if row.state=="active":
            row.state="pending"
            row.operation_id=str(uuid.uuid4())
            event(db,row,"solicitar_eliminacion_identificacion",result="pendiente",metadata={"fotos":2})
        row.claim_token=str(uuid.uuid4())
        row.claim_until=now+timedelta(minutes=15)
        claims.append((row.visita_id,row.claim_token))
    db.commit()  # No object I/O until the durable claim/intent has committed.
    return claims


def leased(db, tenant, visit_id, token, now):
    _set_postgres_tenant(db,tenant)
    row=db.query(IdentityRetention).filter_by(visita_id=visit_id,condominio_id=tenant).with_for_update().one()
    if row.state!="pending" or row.claim_token!=token or not row.claim_until or row.claim_until<=now:
        raise RuntimeError("ClaimLost")
    return row


def verified_snapshots(db,row):
    visit=db.query(Visita).filter_by(visita_id=row.visita_id,condominio_id=row.condominio_id).one()
    if row.policy_version!=VERSION or row.condominio_id not in TENANTS or not (visit.nombre_visitante or "").startswith(VISIT_PREFIX):
        raise RuntimeError("FixtureMismatch")
    rows=identity.list_pairs(db,row.visita_id)
    by_id={r.evidencia_id:r for r in rows}
    if len(rows)!=2 or len(row.snapshots)!=2 or {s["side"] for s in row.snapshots}!={"ine_frente","ine_reverso"}:
        raise RuntimeError("PairMismatch")
    for item in row.snapshots:
        evidence=by_id.get(item["id"])
        expected=f"axs-identificaciones/{hashlib.sha256(row.condominio_id.encode()).hexdigest()[:24]}/{item['id']}"
        if not evidence or item["key"]!=expected or evidence.archivo_url!=expected or evidence.hash_sha256!=SYNTHETIC_HASH or item["hash"]!=SYNTHETIC_HASH or evidence.sub_tipo!=item["side"] or evidence.metadata_json.get("captura_id")!=row.captura_id or evidence.metadata_json.get("condominio_id")!=row.condominio_id or evidence.metadata_json.get("storage")!="vercel_blob_private" or evidence.metadata_json.get("nombre")!=LABEL or evidence.metadata_json.get("purge_status"):
            raise RuntimeError("FixtureMismatch")
    return rows


def present(store,key):
    try: return store.read(key)
    except HTTPException as exc:
        if exc.status_code==404: return None
        raise


def process(factory,tenant,visit_id,token,*,now=None,store=None):
    require_pilot()
    clock=(lambda: now) if now is not None else utcnow
    now=clock()
    try:
        with factory() as db:
            row=leased(db,tenant,visit_id,token,clock())
            verified_snapshots(db,row)
            snapshots=list(row.snapshots)
            db.rollback()
        store=store or identity.PrivateIdentityStore()
        # Validate both before deleting either. Absent objects are safe retry progress.
        for item in snapshots:
            data=present(store,item["key"])
            if data is not None and hashlib.sha256(data).hexdigest()!=SYNTHETIC_HASH:
                raise RuntimeError("ContentMismatch")
        for item in snapshots:
            with factory() as db:
                row=leased(db,tenant,visit_id,token,clock())
                verified_snapshots(db,row)
                db.rollback()
            data=present(store,item["key"])
            if data is not None:
                if hashlib.sha256(data).hexdigest()!=SYNTHETIC_HASH: raise RuntimeError("ContentMismatch")
                store.delete(item["key"])
            if present(store,item["key"]) is not None: raise RuntimeError("DeletionUnconfirmed")
        with factory() as db:
            row=leased(db,tenant,visit_id,token,clock())
            rows=verified_snapshots(db,row)
            uid=event(db,row,"eliminar_identificacion",metadata={"fotos":2})
            row.state,row.purged_at,row.event_uid="purged",now,uid
            row.claim_token=row.claim_until=None
            row.last_error=None
            row.snapshots=[]
            row.hold_until=row.hold_owner=row.hold_incident=row.hold_reason=None
            for evidence in rows:
                evidence.archivo_url=evidence.hash_sha256=None
                evidence.metadata_json={"storage":"vercel_blob_private","condominio_id":tenant,"purge_status":"purged",
                    "purge_id":row.operation_id,"purged_at":now.isoformat()+"Z","purge_event_uid":uid}
            db.commit()
        return True
    except Exception as exc:
        with factory() as db:
            _set_postgres_tenant(db,tenant)
            row=db.query(IdentityRetention).filter_by(visita_id=visit_id,condominio_id=tenant).with_for_update().first()
            if row and row.state=="pending" and row.claim_token==token:
                row.attempts+=1
                delays=[60,300,900,3600]
                row.next_attempt_at=now+timedelta(seconds=delays[row.attempts-1] if row.attempts<=4 else 21600)
                row.last_error=type(exc).__name__  # Never persist provider messages or credentials.
                row.claim_token=row.claim_until=None
                event(db,row,"fallar_eliminacion_identificacion",result="pendiente",metadata={"intento":row.attempts})
                db.commit()
        logger.warning("Retención pendiente (%s)",type(exc).__name__)
        return False


def cycle(factory):
    if not pilot_enabled(): return
    from backend.core.recovery_gate import recovery_allowed
    if not recovery_allowed(core_factory=factory): return
    for tenant in sorted(TENANTS):
        with factory() as db:
            claims=claim(db,tenant)
        for visit_id,token in claims:
            if not pilot_enabled(): return
            process(factory,tenant,visit_id,token)


async def worker(factory):
    while True:
        try: await asyncio.to_thread(cycle,factory)
        except Exception as exc: logger.warning("Trabajador de conservación pendiente (%s)",type(exc).__name__)
        await asyncio.sleep(900)
