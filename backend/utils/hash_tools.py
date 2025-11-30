from ..core.security import get_password_hash, verify_password

# Wrappers simples para uso desde el código del proyecto
def hash_password(password: str) -> str:
    return get_password_hash(password)


def check_password(plain: str, hashed: str) -> bool:
    return verify_password(plain, hashed)


def calcular_hash_sha256(content: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(content)
    return h.hexdigest()
