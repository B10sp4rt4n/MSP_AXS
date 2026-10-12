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
