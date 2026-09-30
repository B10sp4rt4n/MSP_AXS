"""Rechazo de autorización identificable sin usar datos de una entidad ajena."""
from fastapi import HTTPException


class SecurityDenial(HTTPException):
    def __init__(self, status_code, detail, *, reason="SCOPE_DENIED", headers=None):
        super().__init__(status_code, detail, headers)
        self.security_reason = reason
