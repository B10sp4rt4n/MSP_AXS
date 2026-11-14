"""Production instance alignment and actual JWT verification with synthetic RSA."""
import base64
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jose import jwt

from scripts.check_runtime_permissions import check_clerk, RuntimeGateError


def configuration():
    host = base64.b64encode(b"clerk.auth.axs-mx.com$").decode()
    return {"ENVIRONMENT": "production", "CLERK_PUBLISHABLE_KEY": "pk_live_" + host,
            "CLERK_JWT_ISSUER": "https://clerk.auth.axs-mx.com",
            "CLERK_JWKS_URL": "https://clerk.auth.axs-mx.com/.well-known/jwks.json",
            "CLERK_JWT_PUBLIC_KEY": "synthetic-present"}


def test_correct_production_configuration_preserves_pinned_key():
    result = check_clerk(configuration())
    assert result["gate"] == "PASS" and result["pinned_public_key_present"]
    assert "synthetic-present" not in str(result)


@pytest.mark.parametrize("key,value", [
    ("CLERK_JWKS_URL", "https://vocal-bee-4163.clerk.accounts.dev/.well-known/jwks.json"),
    ("CLERK_JWKS_URL", "https://clerk.auth.axs-mx.com/.well-known/jwks.json?key=secret"),
    ("CLERK_JWT_ISSUER", "https://wrong.example"),
    ("CLERK_JWT_ISSUER", "http://clerk.auth.axs-mx.com"),
    ("CLERK_JWT_ISSUER", "https://secret@clerk.auth.axs-mx.com"),
    ("CLERK_PUBLISHABLE_KEY", "pk_test_" + base64.b64encode(b"clerk.auth.axs-mx.com$").decode()),
])
def test_misaligned_instance_fails_even_with_pinned_key(key, value):
    values = {**configuration(), key: value}
    with pytest.raises(RuntimeGateError) as error:
        check_clerk(values)
    assert "secret" not in str(error.value)


def test_jwks_path_validates_signature_issuer_and_expiry(monkeypatch):
    from backend.core.auth import jwt as auth
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
    numbers = key.public_key().public_numbers()
    def b64(number):
        return base64.urlsafe_b64encode(number.to_bytes((number.bit_length()+7)//8, "big")).decode().rstrip("=")
    jwks = {"keys": [{"kty": "RSA", "kid": "synthetic", "use": "sig", "alg": "RS256",
                       "n": b64(numbers.n), "e": b64(numbers.e)}]}
    for name, value in configuration().items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("CLERK_JWT_PUBLIC_KEY")
    monkeypatch.setattr(auth, "_clerk_jwks_cache", {"keys": None, "fetched_at": 0})
    requested = []
    def get(url, **kwargs):
        requested.append(url)
        return httpx.Response(200, json=jwks, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", get)
    now = datetime.now(timezone.utc)
    payload = {"sub": "synthetic-user", "iss": configuration()["CLERK_JWT_ISSUER"],
               "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=5)).timestamp())}
    def token(**changes):
        return jwt.encode({**payload, **changes}, private, algorithm="RS256", headers={"kid": "synthetic"})
    assert auth.verify_clerk_token(token())["sub"] == "synthetic-user"
    assert auth.verify_clerk_token(token(iss="https://wrong.example")) is None
    assert auth.verify_clerk_token(token(exp=int(now.timestamp())-1)) is None
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_private = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()).decode()
    assert auth.verify_clerk_token(jwt.encode(payload, other_private, algorithm="RS256")) is None
    assert requested == [configuration()["CLERK_JWKS_URL"]]
