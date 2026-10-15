"""Webhook de consulta con sesión Alexa firmada y vínculo piloto explícito."""
from datetime import datetime, timedelta, timezone
import hmac
import os
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.db.core import AccessLevel, Casa, Usuario, Visita, get_core_db
from backend.db.gov import get_gov_db
from backend.core.scope.msp_boundary import require_condominio
from backend.core.tenant.context import _set_postgres_tenant
from backend.services.alexa_request import verify_request
from backend.services.event_outbox import contexto_evento, encolar_evento
from backend.services.security_outbox import guardar_intento

router = APIRouter()


def speech(text):
    return {'version': '1.0', 'response': {
        'outputSpeech': {'type': 'PlainText', 'text': text}, 'shouldEndSession': True}}


def consultar(envelope, request, db, db_gov):
    system = envelope['context']['System']
    user_id = system['user']['userId']
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
        return speech('Abre accesos condominio para escuchar la última entrada de tu vivienda en las últimas veinticuatro horas.')
    if kind != 'LaunchRequest' and not (kind == 'IntentRequest' and intent == 'ConsultarVisitaIntent'):
        return speech('Para consultar tu última visita, di: Alexa, abre accesos condominio.')
    now = datetime.now(timezone.utc)
    visita = db.query(Visita).filter(
        Visita.condominio_id == tenant, Visita.destino_id == house,
        Visita.destino_tipo == 'vivienda',
        Visita.estado.in_(['entrada_registrada', 'salida_registrada']),
        Visita.entrada_registrada_en >= (now - timedelta(hours=24)).replace(tzinfo=None),
        Visita.entrada_registrada_en <= now.replace(tzinfo=None),
    ).order_by(Visita.entrada_registrada_en.desc(), Visita.visita_id).first()
    if visita is None:
        answer = speech('No hay entradas registradas para tu vivienda en las últimas veinticuatro horas.')
    else:
        entry = visita.entrada_registrada_en
        entry = entry.replace(tzinfo=timezone.utc) if entry.tzinfo is None else entry
        local = entry.astimezone(ZoneInfo('America/Mexico_City'))
        today = now.astimezone(ZoneInfo('America/Mexico_City')).date()
        day = 'hoy' if local.date() == today else 'ayer'
        name = ' '.join((visita.nombre_visitante or 'una visita sin nombre registrado').split())[:160]
        text = f'Se registró la entrada de {name}, {day} a las {local:%H:%M}.'
        if visita.salida_registrada_en is not None:
            text += ' Su salida ya fue registrada.'
        answer = speech(text)
    # EVENT precede a la respuesta; nunca incluye nombre ni el userId de Amazon.
    ctx = contexto_evento(usuario, req['requestId'], accion='consultar',
                          motivo='Consulta por voz de última entrada de vivienda')
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
    if os.getenv('AXS_ALEXA_VOICE_ENABLED', '').lower() != 'true':
        raise HTTPException(503, 'Consulta por voz no habilitada')
    body = await read_body(request)
    try:
        envelope = await run_in_threadpool(verify_request, body, request.headers)
    except Exception:
        await run_in_threadpool(guardar_intento, request, 'INVALID_SESSION')
        raise HTTPException(401, 'Solicitud Alexa no autenticada')
    try:
        return await run_in_threadpool(consultar, envelope, request, db, db_gov)
    except HTTPException as exc:
        db.rollback()
        if exc.status_code == 403:
            await run_in_threadpool(guardar_intento, request, 'RESIDENCE_DENIED')
        raise
