"""Phase/config/auth regressions without network access."""
import base64
from uuid import uuid4
from unittest.mock import Mock
import pytest
from scripts.check_corporate_sandbox_config import check
from tests.test_corporate_sandbox_config import safe_config


def runtime_config():
    values = safe_config()
    values.update(AXS_CORPORATE_SANDBOX_PHASE='runtime',
        AXS_CORPORATE_SANDBOX_RUN_ID=str(uuid4()), CLERK_JWT_ISSUER='https://axs-test.clerk.accounts.dev',
        ALLOWED_ORIGINS='https://axs-synthetic.example',
        CLERK_PUBLISHABLE_KEY='pk_test_' + base64.b64encode(b'axs-test.clerk.accounts.dev$').decode().rstrip('='))
    for name in ('AXS_CORPORATE_API_ENABLED','AXS_CORPORATE_PROVISIONING_ENABLED','AXS_ARCO_CASES_ENABLED'):
        values[name] = 'true'
    for name in ('DATABASE_CORE_URL','DATABASE_URL'):
        values[name] = values[name].replace('axs_core_app','axs_corp_sandbox_core')
    values['DATABASE_CORPORATE_PROVISIONING_URL'] = values['DATABASE_CORE_URL'].replace('axs_corp_sandbox_core','axs_corporate_provisioner')
    return values


def test_explicit_runtime_accepts_dedicated_roles_and_test_issuer():
    check(runtime_config())


@pytest.mark.parametrize('key,value', [
    ('AXS_CORPORATE_SANDBOX_PHASE','typo'), ('AXS_CORPORATE_SANDBOX_RUN_ID','missing'),
    ('CLERK_JWT_ISSUER','https://production.example'), ('CLERK_JWKS_URL','https://attacker.example/keys'),
    ('ALLOWED_ORIGINS','*'), ('ALLOWED_ORIGINS','https://user:secret@host.example'),
    ('TESTING','1'), ('CLERK_JWT_PUBLIC_KEY','-----BEGIN PUBLIC KEY----- override'),
    ('AXS_ID_RETENTION_SCHEMA_ENABLED','true'), ('AXS_CORPORATE_BOOTSTRAP_CORE_URL','owner-secret'),
])
def test_runtime_rejects_identity_or_owner_configuration(key, value):
    values=runtime_config()
    values[key]=value
    with pytest.raises(RuntimeError):
        check(values)


@pytest.mark.parametrize('key', ['DATABASE_CORE_URL','DATABASE_URL','DATABASE_CORPORATE_PROVISIONING_URL'])
def test_runtime_rejects_shared_legacy_role_and_missing_provisioner(key):
    values=runtime_config()
    values[key]=safe_config()['DATABASE_CORE_URL']
    with pytest.raises(RuntimeError):
        check(values)


@pytest.mark.parametrize('payload', [None, {'sub':'user_not_enrolled'}])
def test_sandbox_unknown_subject_never_links_email_or_decodes_local_token(monkeypatch,payload):
    from backend.core.auth import dependencies as auth
    monkeypatch.setenv('AXS_CORPORATE_SANDBOX_ONLY','true')
    monkeypatch.setattr(auth,'verify_clerk_token',lambda token:payload)
    link=Mock(side_effect=AssertionError('Email linking forbidden'))
    local=Mock(side_effect=AssertionError('Local tokens forbidden'))
    monkeypatch.setattr(auth,'_link_clerk_user_by_email',link)
    monkeypatch.setattr(auth,'decode_access_token',local)
    db=Mock()
    db.query.return_value.filter.return_value.first.return_value=None
    with pytest.raises(auth.SecurityDenial) as denied:
        auth.get_current_user(token='synthetic',db=db)
    assert denied.value.status_code==401
    link.assert_not_called()
    local.assert_not_called()


def test_sandbox_enrolled_subject_is_accepted(monkeypatch):
    from backend.core.auth import dependencies as auth
    monkeypatch.setenv('AXS_CORPORATE_SANDBOX_ONLY','true')
    monkeypatch.setattr(auth,'verify_clerk_token',lambda token:{'sub':'user_synthetic'})
    db=Mock()
    actor=object()
    db.query.return_value.filter.return_value.first.return_value=actor
    assert auth.get_current_user(token='synthetic',db=db) is actor
