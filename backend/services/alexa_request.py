"""Autenticar la sesión externa de Alexa antes de acceder a CORE.

Verificación HTTPS de Amazon: certificado CA + SAN, Signature-256 sobre el
cuerpo original, timestamp de 150 segundos y applicationId de nuestra skill.
"""
import base64
from datetime import datetime, timezone
from functools import lru_cache
import json
import os
import posixpath
from urllib.parse import urlsplit, urlunsplit

import certifi
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import httpx
from OpenSSL import crypto

SKILL_EVENTS = frozenset({
    'AlexaSkillEvent.SkillAccountLinked', 'AlexaSkillEvent.SkillAccountUnlinked',
    'AlexaSkillEvent.SkillEnabled', 'AlexaSkillEvent.SkillDisabled',
    'AlexaSkillEvent.SkillPermissionAccepted', 'AlexaSkillEvent.SkillPermissionChanged',
    'AlexaSkillEvent.ProactiveSubscriptionChanged',
})


def certificate_url(value):
    url = urlsplit(value)
    path = posixpath.normpath(url.path)
    if (url.scheme.lower() != 'https' or url.hostname != 's3.amazonaws.com'
            or url.port not in (None, 443) or url.username or url.password
            or not path.startswith('/echo.api/') or '%' in path or '\\' in path
            or url.query):
        raise ValueError('Invalid certificate URL')
    return urlunsplit(('https', 's3.amazonaws.com', path, '', ''))


@lru_cache(maxsize=4)
def certificate_chain(url):
    with httpx.Client(timeout=2.0, follow_redirects=False) as client:
        with client.stream('GET', url) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 65536:
                    raise ValueError('Certificate chain too large')
                chunks.append(chunk)
    return x509.load_pem_x509_certificates(b''.join(chunks))


def verify_chain(chain):
    if not chain:
        raise ValueError('Missing certificate')
    leaf = chain[0]
    names = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if 'echo-api.amazon.com' not in names.get_values_for_type(x509.DNSName):
        raise ValueError('Invalid signing identity')
    # OpenSSL validates signatures, validity dates, CA constraints and trust root.
    # Trust only system roots, never a root supplied by the caller.
    store = crypto.X509Store()
    store.load_locations(certifi.where())
    crypto.X509StoreContext(store, crypto.X509.from_cryptography(leaf),
        [crypto.X509.from_cryptography(cert) for cert in chain[1:]]).verify_certificate()
    key = leaf.public_key()
    if not isinstance(key, rsa.RSAPublicKey):
        raise ValueError('Invalid signing key')
    return key


def verify_request(body, headers, *, now=None):
    skill_id = os.getenv('AXS_ALEXA_SKILL_ID', '').strip()
    if not skill_id:
        raise ValueError('Missing skill configuration')
    # SHA-256 header is the current Amazon web-service signature format.
    url = certificate_url(headers.get('signaturecertchainurl', ''))
    signature = base64.b64decode(headers.get('signature-256', ''), validate=True)
    if not signature:
        raise ValueError('Missing signature')
    key = verify_chain(certificate_chain(url))
    key.verify(signature, body, padding.PKCS1v15(), hashes.SHA256())
    envelope = json.loads(body)
    system = envelope['context']['System']
    if system['application']['applicationId'] != skill_id:
        raise ValueError('Wrong skill')
    session = envelope.get('session', {})
    if session.get('application', {}).get('applicationId', skill_id) != skill_id:
        raise ValueError('Wrong session skill')
    user = system['user']['userId']
    if session.get('user', {}).get('userId', user) != user:
        raise ValueError('Wrong session account')
    stamp = datetime.fromisoformat(envelope['request']['timestamp'].replace('Z', '+00:00'))
    tolerance = 3600 if envelope['request'].get('type') in SKILL_EVENTS else 150
    if stamp.tzinfo is None or abs(((now or datetime.now(timezone.utc)) - stamp).total_seconds()) > tolerance:
        raise ValueError('Stale request')
    if not envelope['request'].get('requestId'):
        raise ValueError('Missing request identity')
    return envelope
