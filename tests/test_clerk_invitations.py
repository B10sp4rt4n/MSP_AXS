"""Provider failures must never be reported as a delivered email."""
import httpx
import pytest
from fastapi import HTTPException
from backend.services.clerk_invitations import send_invitation


@pytest.mark.parametrize("status,expected", [(429,429), (422,409), (401,502), (500,502)])
def test_provider_error(monkeypatch, status, expected):
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("CLERK_INVITATION_REDIRECT_URL", "https://axs.example/sign-up")
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: httpx.Response(status, json={"errors": []}))
    with pytest.raises(HTTPException) as error:
        send_invitation("resident@example.com")
    assert error.value.status_code == expected


def test_payload_and_config(monkeypatch):
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        send_invitation("resident@example.com")
    assert error.value.status_code == 503
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("CLERK_INVITATION_REDIRECT_URL", "https://axs.example/sign-up")
    def post(url, **kw):
        assert url == "https://api.clerk.com/v1/invitations"
        assert kw["json"] == {"email_address": "resident@example.com",
            "redirect_url": "https://axs.example/sign-up", "notify": True,
            "expires_in_days": 7, "ignore_existing": False}
        return httpx.Response(201, json={"id": "inv_123", "url": "secret-ticket"})
    monkeypatch.setattr(httpx, "post", post)
    assert send_invitation("resident@example.com") == "inv_123"


def test_timeout(monkeypatch):
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("CLERK_INVITATION_REDIRECT_URL", "https://axs.example/sign-up")
    def timeout(*a, **kw):
        raise httpx.ReadTimeout("timeout")
    monkeypatch.setattr(httpx, "post", timeout)
    with pytest.raises(HTTPException) as error:
        send_invitation("resident@example.com")
    assert error.value.status_code == 502


def test_configured_jwks_uses_verified_domain(monkeypatch):
    from backend.core.auth import jwt as auth_jwt
    monkeypatch.setattr(auth_jwt, "_get_clerk_domain", lambda: "clerk.auth.axs-mx.com")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://clerk.auth.axs-mx.com/.well-known/jwks.json")
    monkeypatch.setattr(auth_jwt, "_clerk_jwks_cache", {"keys": None, "fetched_at": 0})
    seen = []
    def fake_get(url, **kwargs):
        seen.append(url)
        return httpx.Response(200, json={"keys": []}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    assert auth_jwt._fetch_clerk_jwks() == {"keys": []}
    assert seen == ["https://clerk.auth.axs-mx.com/.well-known/jwks.json"]


def test_rejects_jwks_from_unrelated_domain(monkeypatch):
    from backend.core.auth import jwt as auth_jwt
    monkeypatch.setattr(auth_jwt, "_get_clerk_domain", lambda: "clerk.auth.axs-mx.com")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://unexpected.example/.well-known/jwks.json")
    monkeypatch.setattr(auth_jwt, "_clerk_jwks_cache", {"keys": None, "fetched_at": 0})
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: pytest.fail("Unexpected external request"))
    assert auth_jwt._fetch_clerk_jwks() is None


def test_offline_clerk_public_key_verifies_signature_and_issuer(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from jose import jwt as jose_jwt
    from backend.core.auth import jwt as auth_jwt
    from datetime import datetime, timezone, timedelta
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public_pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(auth_jwt, "_get_clerk_domain", lambda: "clerk.auth.axs-mx.com")
    monkeypatch.setattr(auth_jwt, "_fetch_clerk_jwks", lambda: pytest.fail("JWKS network should not be called"))
    now = datetime.now(timezone.utc)
    payload = {"sub": "user_test", "iss": "https://clerk.auth.axs-mx.com",
               "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=5)).timestamp())}
    signed = jose_jwt.encode(payload, private_pem, algorithm="RS256")
    assert auth_jwt.verify_clerk_token(signed)["sub"] == "user_test"
    wrong_issuer = jose_jwt.encode({**payload, "iss": "https://another.example"}, private_pem, algorithm="RS256")
    assert auth_jwt.verify_clerk_token(wrong_issuer) is None
    expired = jose_jwt.encode({**payload, "exp": int((now - timedelta(seconds=1)).timestamp())}, private_pem, algorithm="RS256")
    assert auth_jwt.verify_clerk_token(expired) is None
