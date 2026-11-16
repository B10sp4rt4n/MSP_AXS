"""Window boundaries and request-time closure, without remote services."""
import copy
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.core.sandbox_expiry import SandboxExpiryGuard
from scripts import corporate_sandbox_window as windows
from scripts import corporate_sandbox_attestation as attestations


def authorization(now=None):
    now = now or datetime.now(timezone.utc)
    certificate = {'database_name': 'synthetic_db', 'catalog_hash': 'synthetic_hash',
        'certified_at': (now-timedelta(days=2)).isoformat(),
        'expires_at': (now-timedelta(days=1)).isoformat()}
    return {'version': 1, 'authorization_id': str(uuid4()), 'run_id': str(uuid4()),
        'clerk_issuer': 'https://synthetic.clerk.accounts.dev', 'approved_by': 'Synthetic operator',
        'approved_at': now.isoformat(), 'starts_at': now.isoformat(),
        'expires_at': (now+timedelta(days=7)).isoformat(),
        'synthetic_only': True, 'revoked': False, 'reason': 'Synthetic isolation tests',
        'certificates': {domain: dict(certificate) for domain in ('CORE', 'GOV', 'EVENT')}}


def test_explicit_window_is_bounded_and_original_expiry_is_not_renewed():
    now = datetime.now(timezone.utc)
    window = authorization(now)
    before = copy.deepcopy(window)
    assert windows.validate_window(window, run_id=window['run_id'], issuer=window['clerk_issuer'], now=now) == now+timedelta(days=7)
    for instant in (now-timedelta(microseconds=1), now+timedelta(days=7)):
        with pytest.raises(RuntimeError):
            windows.validate_window(window, run_id=window['run_id'], issuer=window['clerk_issuer'], now=instant)
    assert window == before


@pytest.mark.parametrize('key,value', [
    ('run_id', str(uuid4())), ('clerk_issuer', 'https://other.clerk.accounts.dev'),
    ('synthetic_only', False), ('revoked', True), ('approved_by', ''), ('reason', ''),
    ('certificates', {}), ('version', 2),
])
def test_wrong_or_revoked_window_denied(key, value):
    now = datetime.now(timezone.utc)
    window = authorization(now)
    run, issuer = window['run_id'], window['clerk_issuer']
    window[key] = value
    with pytest.raises(RuntimeError):
        windows.validate_window(window, run_id=run, issuer=issuer, now=now)


def test_long_or_ambiguous_window_denied():
    now = datetime.now(timezone.utc)
    window = authorization(now)
    for end in ((now+timedelta(days=7, seconds=1)).isoformat(), now.replace(tzinfo=None).isoformat()):
        window['expires_at'] = end
        with pytest.raises(RuntimeError):
            windows.validate_window(window, run_id=window['run_id'], issuer=window['clerk_issuer'], now=now)


def test_selection_is_explicit_profile_scoped_and_cannot_traverse_paths(monkeypatch, tmp_path):
    window = authorization(datetime.now(timezone.utc)-timedelta(seconds=1))
    monkeypatch.setattr(windows, 'AUTHORIZATION_ROOT', tmp_path)
    (tmp_path / (window['authorization_id']+'.json')).write_text(json.dumps(window))
    values = {'AXS_CORPORATE_SANDBOX_ONLY': 'true', 'AXS_CORPORATE_SANDBOX_PHASE': 'runtime',
        'AXS_CORPORATE_SANDBOX_RUN_PROFILE': 'visits-20261115',
        'AXS_CORPORATE_SANDBOX_RUN_ID': window['run_id'], 'CLERK_JWT_ISSUER': window['clerk_issuer']}
    assert windows.load_window(values) is None
    values[windows.AUTHORIZATION_ENV] = window['authorization_id']
    assert windows.load_window(values) == window
    for key,value in [(windows.AUTHORIZATION_ENV, '../../secret'),
        ('AXS_CORPORATE_SANDBOX_RUN_PROFILE', 'legacy'), ('AXS_CORPORATE_SANDBOX_ONLY', 'false')]:
        with pytest.raises(RuntimeError):
            windows.load_window({**values, key: value})


def test_expired_certificate_requires_exact_independent_authorization(monkeypatch):
    window = authorization(datetime.now(timezone.utc)-timedelta(seconds=1))
    cert = window['certificates']['CORE']
    row = {**cert, 'run_id':window['run_id'], 'domain':'CORE', 'clerk_issuer':window['clerk_issuer'],
           'certified_at':windows.utc(cert['certified_at']), 'expires_at':windows.utc(cert['expires_at'])}
    before = copy.deepcopy(row)
    class Result:
        def one(self): return ('synthetic_db', 'axs_corp_sandbox_core')
        def mappings(self): return self
    class RowResult(Result):
        def one(self): return row
    class Connection:
        def execute(self, statement):
            return RowResult() if 'FROM public.' in str(statement) else Result()
    monkeypatch.setattr(attestations, 'verify_permissions', lambda *a, **k: None)
    monkeypatch.setattr(attestations, 'snapshot', lambda *a: 'synthetic_hash')
    conn = Connection()
    args = (conn, 'CORE', window['run_id'], window['clerk_issuer'])
    with pytest.raises(RuntimeError): attestations.verify_attestation(*args, expected_db='synthetic_db')
    deadline = attestations.verify_attestation(*args, expected_db='synthetic_db', authorization=window)
    assert deadline == windows.utc(window['expires_at'])
    assert row == before
    row['expires_at'] -= timedelta(minutes=1)
    with pytest.raises(RuntimeError):
        attestations.verify_attestation(*args, expected_db='synthetic_db', authorization=window)
    row.update(before)
    monkeypatch.setattr(attestations, 'snapshot', lambda *a: 'changed_catalog')
    with pytest.raises(RuntimeError):
        attestations.verify_attestation(*args, expected_db='synthetic_db', authorization=window)


def test_running_process_closes_operations_at_exact_deadline(monkeypatch):
    now = datetime.now(timezone.utc)
    class Clock:
        @staticmethod
        def now(zone): return now
    import backend.core.sandbox_expiry as guard
    monkeypatch.setattr(guard, 'datetime', Clock)
    app = FastAPI()
    calls = []
    @app.get('/operation')
    def operation():
        calls.append('called')
        return {'ok':True}
    @app.get('/health')
    def health(): return {'ok':True}
    app.add_middleware(SandboxExpiryGuard, deadline=now+timedelta(seconds=1))
    client = TestClient(app)
    assert client.get('/operation').status_code == 200
    now += timedelta(seconds=1)
    response = client.get('/operation')
    assert response.status_code == 503
    assert response.headers['cache-control'] == 'private, no-store'
    assert calls == ['called']
    assert client.get('/health').status_code == 200
