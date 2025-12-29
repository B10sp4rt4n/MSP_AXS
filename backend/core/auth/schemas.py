"""
═══════════════════════════════════════════════════════════════════════════════
Contratos de Autenticación (Pydantic Schemas)
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

  Estos schemas definen los CONTRATOS de comunicación para autenticación.
  
  - LoginRequest: contrato para presentar AUP_CREDENTIAL
  - TokenResponse: contrato para recibir AUP_SESSION serializada

Los contratos son agnósticos al método de autenticación.
En el futuro, LoginRequest podría ser reemplazado por OAuthRequest sin cambiar
TokenResponse.

═══════════════════════════════════════════════════════════════════════════════
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """
    Contrato para presentar credenciales de tipo password_local.
    
    RELACIÓN AUP:
      Cliente presenta → AUP_CREDENTIAL → Sistema valida → AUP_IDENTITY
    """
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "residente@condominio.com",
                "password": "password123"
            }
        }


class TokenResponse(BaseModel):
    """
    Contrato para recibir AUP_SESSION serializada (JWT).
    
    Compatible con estándar OAuth2 RFC 6749.
    Esto facilita migración futura a OAuth/SSO.
    
    RELACIÓN AUP:
      Sistema genera → AUP_SESSION → Serializa → Cliente recibe
    
    USO POSTERIOR:
      Cliente debe enviar en cada request:
        Authorization: Bearer <access_token>
    """
    access_token: str
    token_type: str = "bearer"
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
