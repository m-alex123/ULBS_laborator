import bcrypt

MAX_BCRYPT_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt after validating non-empty <=72 UTF-8 bytes."""
    if not isinstance(password, str) or not password.strip():
        raise ValueError("Password cannot be empty or whitespace-only")
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_BYTES:
        raise ValueError(f"Password cannot exceed {MAX_BCRYPT_BYTES} UTF-8 bytes")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    if not isinstance(plain_password, str) or not isinstance(password_hash, str):
        return False
    if not plain_password or not password_hash:
        return False
    try:
        password_bytes = plain_password.encode("utf-8")
        if len(password_bytes) > MAX_BCRYPT_BYTES:
            return False
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (ValueError, TypeError, UnicodeEncodeError):
        return False
