"""Webhook de consulta con sesión Alexa firmada y vínculo piloto explícito."""
from datetime import datetime, timedelta, timezone
import hmac
import os
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.concurrency import run_in_threadpool

from backend.db.core import AccessLevel, AlexaAccount, Casa, Usuario, Visita, get_core_db
from backend.core.auth.dependencies import get_current_user
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_condominio
from backend.core.tenant.context import _set_postgres_tenant
from backend.services.alexa_request import verify_request, SKILL_EVENTS
from backend.services import alexa_linking
from backend.services.event_outbox import contexto_evento, encolar_evento
from backend.services.security_outbox import guardar_intento

router = APIRouter()


def speech(text):
    return {'version': '1.0', 'response': {
        'outputSpeech': {'type': 'PlainText', 'text': text}, 'shouldEndSession': True}}


def consultar(envelope, request, db, db_gov):
    system = envelope['context']['System']
    user_id = system['user']['userId']
    if alexa_linking.enabled():
        usuario = alexa_linking.resolve_voice(envelope, db, db_gov)
        if usuario is None:
            answer = speech('Vincula tu cuenta AXS en la aplicación Alexa para consultar tu vivienda.')
            answer['response']['card'] = {'type': 'LinkAccount'}
            return answer
        tenant, house = usuario.condominio_id, usuario.casa_id
    else:
        target_user = os.getenv('AXS_ALEXA_PILOT_USER_ID', '').strip()
        tenant = os.getenv('AXS_ALEXA_PILOT_CONDOMINIO_ID', '').strip()
        house = os.getenv('AXS_ALEXA_PILOT_CASA_ID', '').strip()
        resident = os.getenv('AXS_ALEXA_PILOT_RESIDENTE_ID', '').strip()
        if not all((target_user, tenant, house, resident)) or not hmac.compare_digest(user_id, target_user):
            raise HTTPException(403, 'Cuenta Alexa sin vínculo vigente')
        usuario = db.query(Usuario).filter_by(usuario_id=resident, rol='RESIDENTE',
                                            condominio_id=tenant, casa_id=house).one_or_none()
        if usuario is None:
            raise HTTPException(403, 'Vínculo de residente no vigente')
    request.state.verified_identity_id = usuario.usuario_id
    # Una solicitud firmada de Amazon es la sesión externa, nunca un userId del cliente sin validar.
    request.state.session_token = envelope['request']['requestId']
    require_condominio(db, db_gov, usuario, tenant, AccessLevel.RESIDENTE)
    _set_postgres_tenant(db, tenant)
    if db.query(Casa).filter_by(casa_id=house, condominio_id=tenant).one_or_none() is None:
        raise HTTPException(403, 'Vivienda no vigente')
    req = envelope['request']
    kind = req['type']
    intent = req.get('intent', {}).get('name')
    if kind == 'SessionEndedRequest':
        return {'version': '1.0', 'response': {}}
    if kind == 'IntentRequest' and intent in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'):
        return speech('Hasta luego.')
    if kind == 'IntentRequest' and intent == 'AMAZON.HelpIntent':
        return speech('Abre mis visitas para escuchar el último movimiento de tu vivienda en las últimas veinticuatro horas.')
    if kind != 'LaunchRequest' and not (kind == 'IntentRequest' and intent == 'ConsultarVisitaIntent'):
        return speech('Para consultar tu última visita, di: Alexa, abre mis visitas.')
    now = datetime.now(timezone.utc)
    movement_time = func.coalesce(Visita.salida_registrada_en, Visita.entrada_registrada_en)
    visita = db.query(Visita).filter(
        Visita.condominio_id == tenant, Visita.destino_id == house,
        Visita.destino_tipo == 'vivienda',
        Visita.estado.in_(['entrada_registrada', 'salida_registrada']),
        movement_time >= (now - timedelta(hours=24)).replace(tzinfo=None),
        movement_time <= now.replace(tzinfo=None),
    ).order_by(movement_time.desc(), Visita.visita_id).first()
    if visita is None:
        answer = speech('No hay entradas ni salidas registradas para tu vivienda en las últimas veinticuatro horas.')
    else:
        is_exit = visita.salida_registrada_en is not None
        movement = "salida" if is_exit else "entrada"
        entry = visita.salida_registrada_en if is_exit else visita.entrada_registrada_en
        entry = entry.replace(tzinfo=timezone.utc) if entry.tzinfo is None else entry
        local = entry.astimezone(ZoneInfo('America/Mexico_City'))
        today = now.astimezone(ZoneInfo('America/Mexico_City')).date()
        day = 'hoy' if local.date() == today else 'ayer'
        name = ' '.join((visita.nombre_visitante or 'una visita sin nombre registrado').split())[:160]
        text = f'Se registró la {movement} de {name}, {day} a las {local:%H:%M}.'
        if not is_exit:
            text += ' Aún no hay una salida registrada para esta visita.'
        answer = speech(text)
    # EVENT precede a la respuesta; nunca incluye nombre ni el userId de Amazon.
    ctx = contexto_evento(usuario, req['requestId'], accion='consultar',
                          motivo='Consulta por voz de último movimiento de vivienda')
    encolar_evento(db, tenant, visita.visita_id if visita else house, ctx,
                  metadata={'canal': 'alexa', 'casa_id': house, 'encontrada': visita is not None})
    db.commit()
    return answer


async def read_body(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            raise HTTPException(413, 'Solicitud demasiado grande')
    return bytes(body)


@router.post('/webhooks/alexa')
async def alexa_voice(request: Request, db: Session = Depends(get_core_db),
                      db_gov: Session = Depends(get_gov_db)):
    if os.getenv('AXS_ALEXA_VOICE_ENABLED', '').lower() != 'true' and not alexa_linking.enabled():
        raise HTTPException(503, 'Consulta por voz no habilitada')
    body = await read_body(request)
    try:
        envelope = await run_in_threadpool(verify_request, body, request.headers)
    except Exception:
        await run_in_threadpool(guardar_intento, request, 'INVALID_SESSION')
        raise HTTPException(401, 'Solicitud Alexa no autenticada')
    try:
        if envelope['request']['type'] in SKILL_EVENTS:
            if not alexa_linking.enabled():
                raise HTTPException(503, 'Vinculación beta no habilitada')
            return await run_in_threadpool(alexa_linking.handle_event, envelope, db, db_gov)
        if os.getenv('AXS_ALEXA_VOICE_ENABLED', '').lower() != 'true':
            raise HTTPException(503, 'Consulta por voz no habilitada')
        return await run_in_threadpool(consultar, envelope, request, db, db_gov)
    except HTTPException as exc:
        db.rollback()
        if exc.status_code == 403:
            await run_in_threadpool(guardar_intento, request, 'RESIDENCE_DENIED')
        raise
    except Exception:
        db.rollback()
        raise


@router.get('/alexa/vinculacion')
def linking_status(db: Session = Depends(get_core_db), db_gov: Session = Depends(get_gov_db),
                   usuario: Usuario = Depends(get_current_user)):
    if not alexa_linking.enabled():
        return {'beta_habilitada': False, 'vinculada': False, 'notificaciones': False}
    try:
        alexa_linking.authorized_resident(db, db_gov, resident=usuario.usuario_id)
    except HTTPException as exc:
        if exc.status_code not in (403, 404):
            raise
        return {'beta_habilitada': True, 'vinculada': False, 'notificaciones': False}
    rows = db.query(AlexaAccount).filter_by(usuario_id=usuario.usuario_id,
        condominio_id=usuario.condominio_id, casa_id=usuario.casa_id).all()
    return {'beta_habilitada': True, 'vinculada': any(alexa_linking.active(r) for r in rows),
            'notificaciones': any(alexa_linking.notifications_active(r) for r in rows)}


@router.delete('/alexa/vinculacion')
def disconnect(request: Request, db: Session = Depends(get_core_db),
               db_gov: Session = Depends(get_gov_db), usuario: Usuario = Depends(get_current_user)):
    if not alexa_linking.enabled():
        raise HTTPException(503, 'Vinculación beta no habilitada')
    # Disconnect remains available even if a resident no longer has tenant scope.
    rows = db.query(AlexaAccount).filter_by(usuario_id=usuario.usuario_id).order_by(AlexaAccount.account_key).all()
    for row in rows:
        alexa_linking.lock_account(db, row.account_key)
        db.refresh(row)
        if row.usuario_id != usuario.usuario_id:
            continue
        row.disabled_at = datetime.utcnow()
        alexa_linking.audit(db, row, usuario, request.state.session_token, 'desvincular')
    db.commit()
    return {'vinculada': False, 'notificaciones': False}
