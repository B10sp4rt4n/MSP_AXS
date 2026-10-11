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
