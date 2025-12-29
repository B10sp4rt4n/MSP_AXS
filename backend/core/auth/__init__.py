"""
Módulo de autenticación para MSP_AXS.
Sistema simple JWT preparado para migración futura a OAuth/SSO.
"""

from .dependencies import get_current_user
from .schemas import LoginRequest, TokenResponse

__all__ = ["get_current_user", "LoginRequest", "TokenResponse"]
