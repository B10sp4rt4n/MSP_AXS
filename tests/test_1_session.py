"""
GRUPO 1: SESSION (IDENTIDAD CERTIFICADA)

Tests que validan que el sistema maneja identidad correctamente:
- JWT válido con claims necesarios
- Expiración de tokens
- Credenciales incorrectas
- Protección de endpoints
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt

from backend.core.auth.jwt import SECRET_KEY, ALGORITHM


class TestSession:
    """Tests de AUP_SESSION (Identidad certificada)."""
    
    def test_login_genera_token_jwt_valido(self, client, usuario_base):
        """
        TEST 1.1 — Login genera token JWT válido
        
        Objetivo: Verificar que autenticación produce identidad certificada.
        
        Axioma AUP: Toda operación requiere AUP_SESSION válida.
        """
        # 1. POST /auth/login
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # 2. Validar respuesta
        assert response.status_code == 200
        assert "access_token" in response.json()
        token = response.json()["access_token"]
        
        # 3. Decodificar token y validar claims esenciales
        # ⚠️ AJUSTE AUP: No acoplar scope_id en JWT (se resuelve en runtime desde BD)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == usuario_base.usuario_id  # Identity
        assert "exp" in payload  # Expiration timestamp
        assert "role" in payload  # Role base
        assert payload["method"] == "local"  # Authentication method
        
        # Criterio de éxito: Token contiene sub, exp, role, method
        print(f"✅ Token generado con claims: {list(payload.keys())}")
    
    def test_token_expirado_rechaza_acceso(self, client, usuario_base):
        """
        TEST 1.2 — Token expirado rechaza acceso
        
        Objetivo: Verificar que identidad caduca (no es eterna).
        
        Axioma AUP: AUP_SESSION es temporal y expira.
        """
        # 1. Crear token expirado manualmente
        expired_payload = {
            "sub": "test@example.com",
            "role": "ADMIN_CONDOMINIO",
            "method": "local",
            "iat": datetime.utcnow() - timedelta(hours=3),
            "exp": datetime.utcnow() - timedelta(hours=2)  # 2 horas atrás
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # 2. Intentar acceder a endpoint protegido
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        # 3. Validar rechazo
        assert response.status_code == 401
        detail = response.json().get("detail", "").lower()
        # El middleware AUP-01 responde con su contrato de sesión inválida.
        assert "invalid session" in detail
        
        print(f"✅ Token expirado rechazado correctamente: {response.json()['detail']}")
    
    def test_contrasena_incorrecta_deniega_login(self, client, usuario_base):
        """
        TEST 1.3 — Contraseña incorrecta deniega login
        
        Objetivo: Verificar que identidad requiere credencial válida.
        
        Axioma AUP: Identidad no se puede falsificar.
        """
        # 1. POST /auth/login con contraseña incorrecta
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "WRONG_PASSWORD"
        })
        
        # 2. Validar rechazo
        assert response.status_code == 401
        detail = response.json().get("detail", "").lower()
        assert "incorrect" in detail or "invalid" in detail
        
        print(f"✅ Contraseña incorrecta rechazada: {response.json()['detail']}")
    
    def test_endpoint_protegido_sin_token_rechaza(self, client, db_event_session):
        """
        TEST 1.4 — Endpoint protegido sin token rechaza
        
        Objetivo: Verificar que operaciones requieren identidad.
        
        Axioma AUP: Sin AUP_SESSION válida, no hay operación.
        """
        # 1. GET /auth/me SIN header Authorization
        response = client.get("/auth/me")
        
        # 2. Validar rechazo
        assert response.status_code == 401
        detail = response.json().get("detail", "").lower()
        assert "no session" in detail
        from backend.db.event import Event
        from backend.core.event.registry import verificar_integridad_evento
        evento = db_event_session.query(Event).filter_by(accion="denegar").one()
        assert verificar_integridad_evento(evento)
        
        print(f"✅ Acceso sin token rechazado: {response.json()['detail']}")
