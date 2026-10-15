from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, BackgroundTasks
import httpx
import pytest

from backend.db.core import AlexaAccount, Casa, Usuario, UserTenantScope, ScopeStatus, EventOutbox
from backend.services import alexa_linking as linking, alexa_notifications as notifications
from backend.core.auth.jwt import create_access_token
from tests.test_alexa_voice import envelope, signer, pilot, invoke, USER


@pytest.fixture
def beta(pilot, db_session, monkeypatch):
    monkeypatch.setenv('AXS_ALEXA_LINKING_ENABLED', 'true')
    monkeypatch.setenv('AXS_ALEXA_BETA_CONDOMINIOS', pilot.condominio_id)
    user = db_session.query(Usuario).filter_by(usuario_id='voice-resident').one()
    user.clerk_id = 'user_clerk_resident'
    db_session.commit()
    monkeypatch.setattr(linking, 'clerk_subject', lambda token: 'user_clerk_resident' if token == 'valid-access-token' else (_ for _ in ()).throw(HTTPException(403, 'invalid')))
    return user


def event(client, signer, envelope, kind, *, minute=0, body=None):
    data = deepcopy(envelope)
    # All creation clocks fit in the last 20 minutes; publishing time is fresh.
    data['request'].update(type='AlexaSkillEvent.' + kind, requestId='evt-' + kind + str(minute),
        eventCreationTime=(datetime.fromisoformat(envelope['request']['timestamp']).replace(microsecond=0) - timedelta(minutes=20-minute)).isoformat(), body=body or {})
    return invoke(client, signer, data)


def grant(client, signer, envelope):
    assert event(client, signer, envelope, 'SkillPermissionAccepted', minute=1,
        body={'acceptedPermissions': [{'scope': linking.PERMISSION}]}).status_code == 200
    assert event(client, signer, envelope, 'ProactiveSubscriptionChanged', minute=2,
        body={'subscriptions': [{'eventName': linking.PUBLICATION}]}).status_code == 200


def link(client, signer, envelope, *, minute=3):
    return event(client, signer, envelope, 'SkillAccountLinked', minute=minute,
                 body={'accessToken': 'valid-access-token'})


@pytest.mark.parametrize('consent_first', [True, False])
def test_automatic_link_without_launch(client, db_session, beta, signer, envelope, consent_first):
    if consent_first:
        grant(client, signer, envelope)
    assert link(client, signer, envelope).status_code == 200
    if not consent_first:
        assert not linking.notifications_active(db_session.query(AlexaAccount).one())
        grant(client, signer, envelope)
    row = db_session.query(AlexaAccount).one()
    assert linking.notifications_active(row)
    assert (row.usuario_id, row.casa_id) == (beta.usuario_id, beta.casa_id)
    assert db_session.query(EventOutbox).filter(EventOutbox.payload['accion'].as_string() == 'vincular').count() == 1
    assert 'valid-access-token' not in str(row.__dict__)
    assert link(client, signer, envelope).status_code == 200
    assert db_session.query(EventOutbox).filter(EventOutbox.payload['accion'].as_string() == 'vincular').count() == 1
    envelope['context']['System']['user']['accessToken'] = 'valid-access-token'
    response = invoke(client, signer, envelope)
    assert response.status_code == 200 and 'Juan Pérez' in response.text


@pytest.mark.parametrize('kind,body', [
    ('SkillPermissionChanged', {'acceptedPermissions': []}),
    ('ProactiveSubscriptionChanged', {'subscriptions': []}),
    ('SkillDisabled', {}), ('SkillAccountUnlinked', {}),
])
def test_revocation_and_out_of_order_events(client, db_session, beta, signer, envelope, kind, body):
    grant(client, signer, envelope)
    assert link(client, signer, envelope).status_code == 200
    assert event(client, signer, envelope, kind, minute=5, body=body).status_code == 200
    row = db_session.query(AlexaAccount).one()
    assert not linking.notifications_active(row)
    grant(client, signer, envelope)  # Older grants must never reverse a revocation.
    assert link(client, signer, envelope).status_code == 200
    db_session.refresh(row)
    assert not linking.notifications_active(row)
    if kind in ('SkillDisabled', 'SkillAccountUnlinked'):
        assert link(client, signer, envelope, minute=6).status_code == 200
        db_session.refresh(row)
        assert linking.active(row) and not linking.notifications_active(row)


@pytest.mark.parametrize('case', ['scope', 'role', 'house', 'tenant', 'unmapped', 'token'])
def test_link_denied_without_current_resident_binding(client, db_session, beta, signer, envelope, monkeypatch, case):
    if case == 'scope':
        db_session.query(UserTenantScope).update({'estado': ScopeStatus.REVOCADO})
    elif case == 'role':
        beta.rol = 'GUARDIA'
    elif case == 'house':
        beta.casa_id = None
    elif case == 'tenant':
        monkeypatch.setenv('AXS_ALEXA_BETA_CONDOMINIOS', 'other-tenant')
    elif case == 'unmapped':
        beta.clerk_id = None
    else:
        monkeypatch.setattr(linking, 'clerk_subject', lambda token: (_ for _ in ()).throw(HTTPException(403, 'invalid')))
    db_session.commit()
    assert link(client, signer, envelope).status_code == 403
    assert not db_session.query(AlexaAccount).count()


def test_unknown_account_gets_link_card_never_pilot_fallback(client, beta, signer, envelope):
    # Even the configured pilot account must link when multi-resident beta is on.
    response = invoke(client, signer, envelope)
    assert response.status_code == 200
    assert response.json()['response']['card']['type'] == 'LinkAccount'
    assert 'Juan' not in response.text


def test_voice_checks_token_and_house_again(client, db_session, beta, signer, envelope):
    assert link(client, signer, envelope).status_code == 200
    envelope['context']['System']['user']['accessToken'] = 'invalid-token'
    assert invoke(client, signer, envelope).status_code == 403
    envelope['context']['System']['user']['accessToken'] = 'valid-access-token'
    beta.casa_id = None
    db_session.commit()
    response = invoke(client, signer, envelope)
    assert response.status_code == 403 and 'Juan' not in response.text


def test_status_and_self_disconnect(client, db_session, beta, signer, envelope):
    grant(client, signer, envelope)
    link(client, signer, envelope)
    headers = {'Authorization': 'Bearer ' + create_access_token(beta.usuario_id, 'RESIDENTE')}
    assert client.get('/alexa/vinculacion', headers=headers).json()['notificaciones']
    assert client.get('/alexa/vinculacion').status_code == 401
    other = Usuario(usuario_id='other-resident', rol='RESIDENTE')
    db_session.add(other)
    db_session.commit()
    other_headers = {'Authorization': 'Bearer ' + create_access_token(other.usuario_id, 'RESIDENTE')}
    assert not client.get('/alexa/vinculacion', headers=other_headers).json()['vinculada']
    assert client.delete('/alexa/vinculacion', headers=other_headers).status_code == 200
    assert linking.notifications_active(db_session.query(AlexaAccount).one())
    assert client.delete('/alexa/vinculacion', headers=headers).status_code == 200
    assert not linking.active(db_session.query(AlexaAccount).one())
    assert link(client, signer, envelope).status_code == 200  # delayed signed event
    assert not linking.active(db_session.query(AlexaAccount).one())


@pytest.mark.parametrize('case', ['valid', 'other-house', 'moved', 'revoked', 'no-permission', 'recovery'])
def test_notifications_reauthorize_recipients(client, db_session, db_gov_session, beta, signer, envelope, monkeypatch, pilot, case):
    monkeypatch.setenv('AXS_ALEXA_ENABLED', 'true')
    grant(client, signer, envelope)
    link(client, signer, envelope)
    if case == 'moved':
        beta.casa_id = None
    elif case == 'revoked':
        db_session.query(UserTenantScope).update({'estado': ScopeStatus.REVOCADO})
    elif case == 'no-permission':
        db_session.query(AlexaAccount).update({'permission_granted': False})
    elif case == 'recovery':
        monkeypatch.setenv('AXS_RECOVERY_INCIDENT', 'invalid-incident')
    db_session.commit()
    @contextmanager
    def core():
        yield db_session
    @contextmanager
    def gov():
        yield db_gov_session
    import backend.db.core, backend.db.gov
    monkeypatch.setattr(backend.db.core, 'SessionLocal_CORE', core)
    monkeypatch.setattr(backend.db.gov, 'SessionLocal_GOV', gov)
    sent = []
    monkeypatch.setattr(notifications, 'enviar_aviso', lambda *args: sent.append(args))
    notifications.enviar_aviso_vivienda(pilot.condominio_id,
        'other-house' if case == 'other-house' else pilot.destino_id, pilot.visita_id)
    assert len(sent) == (1 if case == 'valid' else 0)
    if sent:
        assert sent[0][0] == USER
    tasks = BackgroundTasks()
    notifications.programar_aviso(tasks, pilot)
    assert tasks.tasks[0].func == notifications.enviar_aviso_vivienda


@pytest.mark.parametrize('case', ['valid', 'inactive', 'client', 'scope', 'subject', 'expired', 'timeout'])
def test_clerk_introspection(monkeypatch, case, caplog):
    monkeypatch.setenv('CLERK_JWT_ISSUER', 'https://clerk.example.test')
    monkeypatch.setenv('AXS_ALEXA_CLERK_CLIENT_ID', 'dedicated-client')
    monkeypatch.setenv('AXS_ALEXA_CLERK_CLIENT_SECRET', 'very-private')
    info = {'active': True, 'client_id': 'dedicated-client', 'sub': 'user_123', 'scope': 'openid'}
    if case == 'inactive': info['active'] = False
    if case == 'client': info['client_id'] = 'other-client'
    if case == 'scope': info['scope'] = 'profile'
    if case == 'subject': info['sub'] = 'other-subject'
    if case == 'expired': info['exp'] = 0
    requests = []
    def handler(request):
        requests.append(request)
        if case == 'timeout': raise httpx.ReadTimeout('very-private', request=request)
        return httpx.Response(200, json=info)
    real_client = httpx.Client
    monkeypatch.setattr(linking.httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    if case == 'valid':
        assert linking.clerk_subject('secret-access-token') == 'user_123'
    else:
        with pytest.raises(HTTPException): linking.clerk_subject('secret-access-token')
    assert str(requests[0].url) == 'https://clerk.example.test/oauth/token_info'
    assert 'very-private' not in caplog.text and 'secret-access-token' not in caplog.text


def test_only_known_lifecycle_events_get_hour_tolerance(envelope, signer):
    from backend.services.alexa_request import verify_request
    envelope['request']['timestamp'] = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    envelope['request']['type'] = 'AlexaSkillEvent.SkillDisabled'
    body, headers = signer(envelope)
    assert verify_request(body, headers)
    envelope['request']['type'] = 'AlexaSkillEvent.Unknown'
    body, headers = signer(envelope)
    with pytest.raises(ValueError): verify_request(body, headers)


def test_link_requires_atomic_audit(client, db_session, beta, signer, envelope, monkeypatch):
    grant(client, signer, envelope)
    def fail(*args):
        raise RuntimeError('audit unavailable')
    monkeypatch.setattr(linking, 'audit', fail)
    with pytest.raises(RuntimeError, match='audit unavailable'):
        link(client, signer, envelope)
    row = db_session.query(AlexaAccount).one()
    assert row.usuario_id is None and not linking.active(row)


def test_revoked_scope_hides_status_but_can_disconnect(client, db_session, beta, signer, envelope):
    grant(client, signer, envelope)
    link(client, signer, envelope)
    db_session.query(UserTenantScope).update({'estado': ScopeStatus.REVOCADO})
    db_session.commit()
    headers = {'Authorization': 'Bearer ' + create_access_token(beta.usuario_id, 'RESIDENTE')}
    assert not client.get('/alexa/vinculacion', headers=headers).json()['notificaciones']
    assert client.delete('/alexa/vinculacion', headers=headers).status_code == 200
    assert not linking.active(db_session.query(AlexaAccount).one())
