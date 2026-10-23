"""App-only authorization. All callers must authorize and lock the tenant first.

Request, decision and physical movement have separate durable transitions.
Condominio lock serializes creation/response/entry; conditional updates protect
against stale retries. External channels have no authority here.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import unicodedata
from fastapi import HTTPException
from backend.db.core import SolicitudAcceso, Visita, Usuario, Casa, UserTenantScope, ScopeStatus, AccessLevel
from backend.core.scope.provider_contract import origin_is_current
from backend.services.event_outbox import encolar_evento
from backend.services.visita_service import resolver_destino, generar_visita_id
from backend.services.reglas_acceso import validar_reglas


def normalizar(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value or "")
                            if not unicodedata.combining(c)).casefold().split())


def residente_vigente(db, usuario, tenant, destino):
    if not usuario or usuario.rol != "RESIDENTE" or usuario.condominio_id != tenant or usuario.casa_id != destino:
        return False
    casa = db.query(Casa).filter_by(casa_id=destino, condominio_id=tenant).first()
    if not casa or casa.tipo not in ("casa", "depto", "local") or usuario.casa_unidad != casa.numero:
        return False
    scopes = db.query(UserTenantScope).filter_by(usuario_id=usuario.usuario_id,
        tenant_id=tenant, estado=ScopeStatus.ACTIVO, access_level=AccessLevel.RESIDENTE).all()
    return any(origin_is_current(db, scope) for scope in scopes)


def auditar(db, row, contexto, accion):
    encolar_evento(db, row.condominio_id, row.solicitud_id,
        {**contexto, "entidad": "solicitud_acceso", "accion": accion},
        metadata={"visita_id": row.visita_id, "destino_id": row.destino_id,
                  "estado": row.estado, "expira_en": row.expira_en.isoformat(),
                  "respondida_por": row.respondida_por, "canal": "app",
                  "consentimiento": row.consentimiento_en is not None})


def expirar(db, row, contexto):
    if row.estado in ("pendiente", "permitida") and row.expira_en <= datetime.utcnow():
        changed = db.query(SolicitudAcceso).filter(
            SolicitudAcceso.solicitud_id == row.solicitud_id,
            SolicitudAcceso.estado.in_(["pendiente", "permitida"]),
            SolicitudAcceso.expira_en <= datetime.utcnow()).update(
                {SolicitudAcceso.estado: "expirada"}, synchronize_session=False)
        db.refresh(row)
        if changed:
            auditar(db, row, contexto, "expirar")


def obtener(db, tenant, request_id):
    row = db.query(SolicitudAcceso).filter_by(condominio_id=tenant, solicitud_id=request_id).populate_existing().first()
    if not row:
        raise HTTPException(404, "Solicitud no encontrada")
    return row


def visible(db, row, usuario):
    return usuario.usuario_id in row.destinatarios and residente_vigente(db, usuario, row.condominio_id, row.destino_id)


def vista(db, row):
    visita = db.query(Visita).filter_by(visita_id=row.visita_id, condominio_id=row.condominio_id).one()
    return {"solicitud_id": row.solicitud_id, "visita_id": row.visita_id,
        "destino_id": row.destino_id, "casa_unidad": visita.casa_unidad,
        "nombre_visitante": visita.nombre_visitante, "proposito": visita.proposito,
        "estado": row.estado, "expira_en": row.expira_en.replace(tzinfo=timezone.utc).isoformat(),
        "entrada_registrada": visita.entrada_registrada_en is not None,
        "salida_registrada": visita.salida_registrada_en is not None}


def crear(db, tenant, data, usuario, contexto):
    request_id = str(data.solicitud_id)
    fingerprint = hashlib.sha256(json.dumps(data.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    previous = db.query(SolicitudAcceso).filter_by(solicitud_id=request_id, condominio_id=tenant).first()
    if previous:
        if previous.fingerprint != fingerprint or previous.solicitada_por != usuario.usuario_id:
            raise HTTPException(409, "La referencia ya pertenece a otra solicitud")
        expirar(db, previous, contexto)
        db.commit()
        return vista(db, previous)
    label, destination = resolver_destino(db, tenant, destino_id=data.destino_id, residente=True)
    validar_reglas(db, tenant, data.tipo_visita, data.proposito)
    # Never replace a QR, an open entry or a resident's rejection with a new visit.
    matches = [v for v in db.query(Visita).filter(Visita.condominio_id == tenant,
        Visita.estado.in_(["pendiente", "activa", "entrada_registrada"])).all()
        if normalizar(v.nombre_visitante) == normalizar(data.nombre_visitante)]
    if any(v.qr_token or v.entrada_registrada_en for v in matches):
        raise HTTPException(409, "Existe una visita con QR obligatorio o entrada abierta. Recupera ese registro.")
    if len(matches) > 1 or any(v.destino_id != data.destino_id for v in matches):
        raise HTTPException(409, "Hay registros que requieren aclarar persona y destino con administración")
    visit = matches[0] if matches else None
    if data.visita_id and (not visit or visit.visita_id != data.visita_id):
        raise HTTPException(409, "La visita cambió o no corresponde al destino y visitante")
    if visit and (visit.tipo_visita != data.tipo_visita or (visit.proposito and visit.proposito != data.proposito)):
        raise HTTPException(409, "Conserva los datos de la visita existente; administración debe resolver diferencias")
    if visit and visit.solicitud_remota_id:
        active = obtener(db, tenant, visit.solicitud_remota_id)
        expirar(db, active, contexto)
        if active.estado in ("pendiente", "permitida"):
            db.commit()
            return vista(db, active)
        if active.estado != "expirada":
            raise HTTPException(409, "El residente ya decidió. No crees otra solicitud para sustituir su decisión")
    residents = db.query(Usuario).filter_by(rol="RESIDENTE", condominio_id=tenant, casa_id=data.destino_id).all()
    recipients = [u.usuario_id for u in residents if residente_vigente(db, u, tenant, data.destino_id)]
    if not recipients:
        raise HTTPException(409, "Esta vivienda no tiene residentes habilitados para responder en la app")
    now = datetime.utcnow()
    if visit is None:
        visit = Visita(visita_id=generar_visita_id(), condominio_id=tenant,
            nombre_visitante=data.nombre_visitante, tipo_visita=data.tipo_visita,
            proposito=data.proposito, casa_unidad=label, estado="pendiente", vigencia=now, **destination)
        db.add(visit)
    visit.proposito = data.proposito
    visit.solicitud_remota_id = request_id
    visit.autorizacion_remota_hasta = None
    visit.autorizada_por = None
    visit.autorizada_en = None
    db.flush()
    row = SolicitudAcceso(solicitud_id=request_id, condominio_id=tenant,
        visita_id=visit.visita_id, destino_id=data.destino_id, solicitada_por=usuario.usuario_id,
        destinatarios=recipients, fingerprint=fingerprint, estado="pendiente",
        creada_en=now, expira_en=now + timedelta(minutes=5))
    db.add(row)
    db.flush()
    auditar(db, row, contexto, "solicitar")
    db.commit()
    return vista(db, row)


def responder(db, row, data, usuario, contexto):
    if not visible(db, row, usuario):
        raise HTTPException(403, "La solicitud no corresponde a tu residencia o permiso vigente")
    expirar(db, row, contexto)
    if row.estado != "pendiente":
        db.commit()  # retain lazy expiry even when the attempted reply is rejected
        if row.estado == data.decision and row.respondida_por == usuario.usuario_id:
            return vista(db, row)
        raise HTTPException(409, "La solicitud venció o ya fue respondida; consulta su estado")
    visit = db.query(Visita).filter_by(visita_id=row.visita_id, condominio_id=row.condominio_id).populate_existing().one()
    if visit.qr_token or visit.entrada_registrada_en or visit.estado not in ("pendiente", "activa") or visit.destino_id != row.destino_id or visit.solicitud_remota_id != row.solicitud_id:
        raise HTTPException(409, "La visita cambió; no se puede responder esta solicitud")
    validar_reglas(db, row.condominio_id, visit.tipo_visita, visit.proposito)
    now = datetime.utcnow()
    changed = db.query(SolicitudAcceso).filter_by(solicitud_id=row.solicitud_id, estado="pendiente").filter(
        SolicitudAcceso.expira_en > now).update({SolicitudAcceso.estado: data.decision,
        SolicitudAcceso.respondida_por: usuario.usuario_id, SolicitudAcceso.respondida_en: now,
        SolicitudAcceso.consentimiento_en: now}, synchronize_session=False)
    if changed != 1:
        raise HTTPException(409, "La solicitud cambió; consulta su estado")
    if data.decision == "permitida":
        visit.autorizada_por = usuario.usuario_id
        visit.autorizada_en = now
        visit.autorizacion_remota_hasta = row.expira_en
        visit.vigencia = now
    db.flush()
    db.refresh(row)
    auditar(db, row, contexto, "responder")
    db.commit()
    return vista(db, row)


def validar_entrada(db, visita, now, contexto):
    if not visita.solicitud_remota_id:
        return
    row = obtener(db, visita.condominio_id, visita.solicitud_remota_id)
    resident = db.query(Usuario).filter_by(usuario_id=row.respondida_por).first()
    if (row.estado != "permitida" or row.expira_en <= now or row.visita_id != visita.visita_id
        or row.destino_id != visita.destino_id or not row.consentimiento_en
        or row.respondida_por not in row.destinatarios
        or not residente_vigente(db, resident, row.condominio_id, row.destino_id)):
        raise HTTPException(403, "No hay autorización remota vigente. Consulta la solicitud antes de ingresar.")
    changed = db.query(SolicitudAcceso).filter_by(solicitud_id=row.solicitud_id, estado="permitida").filter(
        SolicitudAcceso.expira_en > now).update({SolicitudAcceso.estado: "consumida"}, synchronize_session=False)
    if changed != 1:
        raise HTTPException(409, "La autorización ya se utilizó o venció")
    db.refresh(row)
    if contexto:
        auditar(db, row, contexto, "consumir")
    # Caller commits this transition together with the physical movement and EVENT.
