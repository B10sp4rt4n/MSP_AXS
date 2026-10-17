import base64
from datetime import datetime, timedelta, timezone
import json

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from OpenSSL import crypto
import pytest

from backend.db.core import Casa, Usuario, UserTenantScope, AccessLevel, ScopeStatus, Visita, EventOutbox
from backend.services import alexa_request as auth

SKILL = 'amzn1.ask.skill.test'
USER = 'amzn1.ask.account.test'


@pytest.fixture
def envelope(monkeypatch):
    monkeypatch.setenv('AXS_ALEXA_SKILL_ID', SKILL)
    return {'version': '1.0', 'context': {'System': {
        'application': {'applicationId': SKILL}, 'user': {'userId': USER}}},
        'request': {'type': 'LaunchRequest', 'requestId': 'req-test',
                    'timestamp': datetime.now(timezone.utc).isoformat()}}


@pytest.fixture
def signer(monkeypatch):
    now = datetime.now(timezone.utc)
    root_key = rsa.generate_private_key(65537, 2048)
    leaf_key = rsa.generate_private_key(65537, 2048)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Unit Test Root')])
    root = (x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name)
        .public_key(root_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(root_key, hashes.SHA256()))
    leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Alexa')]))
        .issuer_name(root_name).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(hours=1)).not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('echo-api.amazon.com')]), critical=False)
        .sign(root_key, hashes.SHA256()))
    monkeypatch.setattr(auth, 'certificate_chain', lambda url: [leaf, root])
    # Test-only CA trust; production loads the real system roots.
    real_store = crypto.X509Store
    def test_store():
        store = real_store()
        store.add_cert(crypto.X509.from_cryptography(root))
        return store
    monkeypatch.setattr(auth.crypto, 'X509Store', test_store)
    def sign(envelope):
        body = json.dumps(envelope).encode()
        signature = leaf_key.sign(body, padding.PKCS1v15(), hashes.SHA256())
        return body, {'signaturecertchainurl': 'https://s3.amazonaws.com/echo.api/test.pem',
                      'signature-256': base64.b64encode(signature).decode()}
    sign.real_store = real_store
    sign.chain = [leaf, root]
    return sign


def test_firma_real_y_cadena_de_confianza(envelope, signer):
    body, headers = signer(envelope)
    assert auth.verify_request(body, headers) == envelope
    with pytest.raises(Exception):
        auth.verify_request(body + b' ', headers)


@pytest.mark.parametrize('url', ['http://s3.amazonaws.com/echo.api/x', 'https://localhost/echo.api/x',
    'https://s3.amazonaws.com:444/echo.api/x', 'https://s3.amazonaws.com/echo.api/../../x',
    'https://s3.amazonaws.com/echo.api/%2e%2e/x', 'https://s3.amazonaws.com@localhost/echo.api/x'])
def test_certificado_no_permite_ssrf(url):
    with pytest.raises(ValueError):
        auth.certificate_url(url)


@pytest.mark.parametrize('case', ['old', 'future', 'skill', 'signature', 'account'])
def test_rechaza_sesion_invalida(envelope, signer, case):
    if case in ('old', 'future'):
        envelope['request']['timestamp'] = (datetime.now(timezone.utc) + timedelta(minutes=-3 if case == 'old' else 3)).isoformat()
    elif case == 'skill':
        envelope['context']['System']['application']['applicationId'] = 'other-skill'
    elif case == 'account':
        envelope['session'] = {'user': {'userId': 'other-user'}}
    body, headers = signer(envelope)
    if case == 'signature':
        headers['signature-256'] = base64.b64encode(b'forged').decode()
    with pytest.raises(Exception):
        auth.verify_request(body, headers)


@pytest.fixture
def pilot(db_session, condominio_base, monkeypatch):
    for key, value in {'AXS_ALEXA_VOICE_ENABLED': 'true', 'AXS_ALEXA_PILOT_USER_ID': USER,
            'AXS_ALEXA_PILOT_CONDOMINIO_ID': condominio_base.condominio_id,
            'AXS_ALEXA_PILOT_CASA_ID': 'voice-house', 'AXS_ALEXA_PILOT_RESIDENTE_ID': 'voice-resident'}.items():
        monkeypatch.setenv(key, value)
    db_session.add(Casa(casa_id='voice-house', condominio_id=condominio_base.condominio_id, numero='36', tipo='casa'))
    db_session.add(Usuario(usuario_id='voice-resident', nombre='Residente', rol='RESIDENTE',
                           condominio_id=condominio_base.condominio_id, casa_id='voice-house', casa_unidad='36'))
    db_session.flush()
    db_session.add(UserTenantScope(usuario_id='voice-resident', tenant_id=condominio_base.condominio_id,
                                  access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO))
    row = Visita(visita_id='voice-visit', condominio_id=condominio_base.condominio_id, destino_id='voice-house',
        destino_tipo='vivienda', nombre_visitante='Juan Pérez', estado='entrada_registrada',
        entrada_registrada_en=datetime.utcnow() - timedelta(minutes=5))
    db_session.add(row)
    db_session.commit()
    return row


def invoke(client, signer, envelope):
    body, headers = signer(envelope)
    return client.post('/webhooks/alexa', content=body, headers={**headers, 'Content-Type': 'application/json'})


def test_lectura_y_evento_sin_nombre(client, db_session, pilot, envelope, signer):
    response = invoke(client, signer, envelope)
    assert response.status_code == 200, response.text
    text = response.json()['response']['outputSpeech']
    assert text['type'] == 'PlainText' and 'Juan Pérez' in text['text'] and 'a las' in text['text']
    event = db_session.query(EventOutbox).one()
    assert event.payload['identity_id'] == 'voice-resident'
    assert event.payload['accion'] == 'consultar'
    assert 'Juan Pérez' not in str(event.payload) and USER not in str(event.payload)


@pytest.mark.parametrize('case', ['other-house', 'other-tenant', 'old', 'pending', 'future'])
def test_no_revela_otras_viviendas_ni_preregistros(client, db_session, pilot, envelope, signer, case):
    if case == 'other-house':
        pilot.destino_id = 'other-house'
    elif case == 'other-tenant':
        pilot.condominio_id = 'other-tenant'
    elif case == 'pending':
        pilot.estado, pilot.entrada_registrada_en = 'pendiente', None
    else:
        pilot.entrada_registrada_en = datetime.utcnow() + timedelta(hours=-25 if case == 'old' else 1)
    db_session.commit()
    response = invoke(client, signer, envelope)
    assert response.status_code == 200, response.text
    assert 'Juan' not in response.text
    assert 'No hay entradas' in response.text


@pytest.mark.parametrize('case', ['account', 'resident', 'scope', 'unsigned', 'disabled'])
def test_denegaciones_no_revelan_nombre(client, db_session, pilot, envelope, signer, monkeypatch, case):
    if case == 'account':
        envelope['context']['System']['user']['userId'] = 'another-account'
    elif case == 'resident':
        db_session.query(Usuario).filter_by(usuario_id='voice-resident').update({'casa_id': 'other-house'})
    elif case == 'scope':
        db_session.query(UserTenantScope).update({'estado': ScopeStatus.REVOCADO})
    elif case == 'disabled':
        monkeypatch.delenv('AXS_ALEXA_VOICE_ENABLED')
    db_session.commit()
    response = (client.post('/webhooks/alexa', json=envelope) if case == 'unsigned'
                else invoke(client, signer, envelope))
    assert response.status_code in (401, 403, 503), response.text
    assert 'Juan' not in response.text
    assert db_session.query(EventOutbox).count() == 0


def test_salida_se_informa(client, db_session, pilot, envelope, signer):
    pilot.estado = 'salida_registrada'
    pilot.salida_registrada_en = datetime.utcnow()
    db_session.commit()
    assert 'Se registró la salida de Juan Pérez, hoy a las' in invoke(client, signer, envelope).text


def test_fallo_auditoria_no_retorna_nombre(client, db_session, pilot, envelope, signer, monkeypatch):
    from backend.routers import alexa_router
    monkeypatch.setattr(alexa_router, 'encolar_evento', lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('audit down')))
    with pytest.raises(RuntimeError):
        invoke(client, signer, envelope)


def test_certificado_sin_ca_confiable_rechazado(signer, monkeypatch):
    monkeypatch.setattr(auth.crypto, 'X509Store', signer.real_store)
    with pytest.raises(crypto.X509StoreContextError):
        auth.verify_chain(signer.chain)


def test_cuerpo_excesivo_rechazado(client, pilot):
    response = client.post('/webhooks/alexa', content=b'x' * 65537)
    assert response.status_code == 413


def test_recovery_bloquea_webhook(client, pilot, monkeypatch):
    monkeypatch.setenv('AXS_RECOVERY_INCIDENT', 'malformed')
    response = client.post('/webhooks/alexa', content=b'{}')
    assert response.status_code == 503
    assert response.json()['code'] == 'RECOVERY_LOCKED'


def test_salida_reciente_prioriza_visita_con_entrada_antigua(client, db_session, pilot, envelope, signer):
    pilot.entrada_registrada_en = datetime.utcnow() - timedelta(days=2)
    pilot.estado = 'salida_registrada'
    pilot.salida_registrada_en = datetime.utcnow()
    db_session.add(Visita(visita_id='newer-entry', condominio_id=pilot.condominio_id,
        destino_id=pilot.destino_id, destino_tipo='vivienda', nombre_visitante='Otra persona',
        estado='entrada_registrada', entrada_registrada_en=datetime.utcnow() - timedelta(minutes=10)))
    db_session.commit()
    response = invoke(client, signer, envelope)
    assert response.status_code == 200
    assert 'Se registró la salida de Juan Pérez, hoy a las' in response.text
    assert 'Otra persona' not in response.text
