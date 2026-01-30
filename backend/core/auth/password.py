"""
═══════════════════════════════════════════════════════════════════════════════
AUP_CREDENTIAL - Entidad de Validación de Identidad
═══════════════════════════════════════════════════════════════════════════════

DECLARACIÓN AUP:

  AUP_CREDENTIAL existe para validar AUP_IDENTITY.
  
  - No ES la identidad
  - VALIDA la identidad
  - Puede tener múltiples tipos (password_local, oauth_assertion, cert)
  
  En esta implementación:
    tipo: password_local
    método: bcrypt (passlib)

AXIOMA:
  Una AUP_IDENTITY solo puede ser validada si existe una AUP_CREDENTIAL válida.

MIGRACIÓN FUTURA:
  - oauth_assertion → validar con provider externo
  - cert → validar certificado x509
  - mfa_token → segundo factor
  
  Todos conviven sin romper el contrato.

═══════════════════════════════════════════════════════════════════════════════
"""

from passlib.context import CryptContext

# Configuración bcrypt: balance seguridad/performance
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Genera AUP_CREDENTIAL de tipo password_local.
    
    Args:
        password: Secreto en texto plano
        
    Returns:
        Credencial serializada (hash bcrypt)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Valida AUP_CREDENTIAL contra secreto proporcionado.
    
    Soporta:
    - Bcrypt (producción)
    - SHA256 (fallback para desarrollo)
    
    Args:
        plain_password: Secreto presentado
        hashed_password: AUP_CREDENTIAL almacenada
        
    Returns:
        True si la credencial valida la identidad, False si no
        
    AXIOMA APLICADO:
        Esta función es el único punto de validación de identidad local.
    """
    import hashlib
    
    # Intentar bcrypt directo
    import bcrypt
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        pass
    
    # Intentar con passlib
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except:
        pass
    
    # Fallback: SHA256 (para desarrollo con SQLite)
    try:
        sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        return sha256_hash == hashed_password
    except:
        return False

