"""
Tests for AUP_SESSION - JWT Token Management

Coverage target: 80%+

Tests:
- create_access_token()
- decode_access_token()
- Token expiration
- Invalid tokens
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError

from backend.core.auth.jwt import (
    create_access_token,
    decode_access_token,
    SECRET_KEY,
    ALGORITHM
)


# ═══════════════════════════════════════════════════════════════════════════
# TEST: create_access_token
# ═══════════════════════════════════════════════════════════════════════════

def test_create_access_token_valido():
    """
    Test: Crear JWT válido con user_id y role.
    """
    # Arrange
    user_id = "user_123"
    role = "ADMIN"
    
    # Act
    token = create_access_token(user_id=user_id, role=role)
    
    # Assert
    assert isinstance(token, str)
    assert len(token) > 50  # JWT should be long
    
    # Decode to verify structure
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "user_123"
    assert decoded["role"] == "ADMIN"
    assert decoded["method"] == "local"
    assert "exp" in decoded  # Expiration timestamp exists
    assert "iat" in decoded  # Issued at timestamp exists


def test_create_access_token_con_expiracion_custom():
    """
    Test: Crear JWT con tiempo de expiración customizado.
    """
    # Arrange
    user_id = "user_456"
    role = "RESIDENTE"
    expires_delta = timedelta(minutes=5)
    
    # Act
    token = create_access_token(user_id=user_id, role=role, expires_delta=expires_delta)
    
    # Assert
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    # Verify expiration is approximately 5 minutes from now
    exp_timestamp = decoded["exp"]
    iat_timestamp = decoded["iat"]
    
    # Both exp and iat are datetime objects when decoded
    # Calculate difference in minutes
    diff_seconds = (exp_timestamp - iat_timestamp).total_seconds() if isinstance(exp_timestamp, datetime) else (exp_timestamp - iat_timestamp)
    diff_minutes = diff_seconds / 60
    
    assert 4.5 < diff_minutes < 5.5  # Allow small time drift


def test_create_access_token_diferentes_roles():
    """
    Test: Crear JWTs con diferentes roles.
    """
    roles = ["ADMIN", "RESIDENTE", "GUARDIA", "SUPER_ADMIN"]
    
    for role in roles:
        # Act
        token = create_access_token(user_id=f"user_{role}", role=role)
        
        # Assert
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["role"] == role


# ═══════════════════════════════════════════════════════════════════════════
# TEST: decode_access_token
# ═══════════════════════════════════════════════════════════════════════════

def test_decode_access_token_valido():
    """
    Test: Decodificar JWT válido retorna datos correctos.
    """
    # Arrange
    user_id = "user_789"
    role = "RESIDENTE"
    token = create_access_token(user_id=user_id, role=role)
    
    # Act
    decoded = decode_access_token(token)
    
    # Assert
    assert decoded is not None
    assert decoded["sub"] == user_id
    assert decoded["role"] == role
    assert decoded["method"] == "local"


def test_decode_access_token_expirado():
    """
    Test: JWT expirado debe retornar None.
    """
    # Arrange
    token = create_access_token(
        user_id="user_expired",
        role="ADMIN",
        expires_delta=timedelta(seconds=-10)  # Expired 10 seconds ago
    )
    
    # Act
    decoded = decode_access_token(token)
    
    # Assert
    assert decoded is None  # Expired tokens return None


def test_decode_access_token_invalido():
    """
    Test: JWT inválido (malformado) debe retornar None.
    """
    # Arrange
    invalid_token = "esto.no.es.un.jwt.valido"
    
    # Act
    decoded = decode_access_token(invalid_token)
    
    # Assert
    assert decoded is None


def test_decode_access_token_firma_incorrecta():
    """
    Test: JWT con firma incorrecta debe retornar None.
    """
    # Arrange
    # Create a token with a different secret
    token = jwt.encode(
        {"sub": "user_fake", "role": "ADMIN"},
        "wrong_secret_key",
        algorithm=ALGORITHM
    )
    
    # Act
    decoded = decode_access_token(token)
    
    # Assert
    assert decoded is None


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

def test_jwt_expiracion_por_defecto():
    """
    Test: JWT sin expires_delta usa el valor por defecto (480 minutos).
    """
    # Arrange & Act
    token = create_access_token(user_id="user_default", role="RESIDENTE")
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    # Assert
    exp_timestamp = decoded["exp"]
    iat_timestamp = decoded["iat"]
    
    # Calculate difference
    diff_seconds = (exp_timestamp - iat_timestamp).total_seconds() if isinstance(exp_timestamp, datetime) else (exp_timestamp - iat_timestamp)
    diff_minutes = diff_seconds / 60
    
    # Should be close to 480 minutes (8 hours)
    assert 475 < diff_minutes < 485


def test_jwt_no_puede_ser_alterado():
    """
    Test: Alterar el payload de un JWT lo invalida.
    
    Axioma AUP: La SESSION es inmutable - cualquier alteración la invalida.
    """
    # Arrange
    token = create_access_token(user_id="user_original", role="RESIDENTE")
    
    # Act: Intentar alterar el token (cambiar payload)
    parts = token.split(".")
    # Decode payload (base64), modify, re-encode
    import base64
    payload = base64.urlsafe_b64decode(parts[1] + "==")  # Add padding
    modified_payload = payload.replace(b"RESIDENTE", b"ADMIN____")  # Same length
    parts[1] = base64.urlsafe_b64encode(modified_payload).decode().rstrip("=")
    tampered_token = ".".join(parts)
    
    # Assert
    decoded = decode_access_token(tampered_token)
    assert decoded is None  # Tampered token is invalid


def test_multiple_tokens_diferentes():
    """
    Test: Generar múltiples tokens produce JWTs únicos.
    """
    # Act
    token1 = create_access_token(user_id="user_1", role="ADMIN")
    token2 = create_access_token(user_id="user_2", role="RESIDENTE")
    
    import time
    time.sleep(1)  # Wait 1 second to get different iat timestamp
    token3 = create_access_token(user_id="user_1", role="ADMIN")
    
    # Assert
    assert token1 != token2  # Different users → different tokens
    assert token1 != token3  # Same user but different iat → different tokens


def test_token_contiene_metodo_local():
    """
    Test: Todos los tokens generados incluyen method='local'.
    
    Esto es requerido por AUP_SESSION para distinguir
    autenticación local vs OAuth vs SSO.
    """
    # Act
    token = create_access_token(user_id="user_method", role="GUARDIA")
    decoded = decode_access_token(token)
    
    # Assert
    assert decoded["method"] == "local"
