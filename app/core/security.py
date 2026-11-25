import base64
import hashlib
import hmac
import json
import time
from typing import Any

import bcrypt

MAX_BCRYPT_BYTES = 72
_DEFAULT_SESSION_TTL = 60 * 60 * 24 * 7


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


def create_session_token(
    user_id: int,
    role: str,
    secret_key: str,
    expires_in_seconds: int = _DEFAULT_SESSION_TTL,
) -> str:
    """Create an HMAC-SHA256 signed URL-safe session token."""
    payload = {
        "sub": int(user_id),
        "role": str(role),
        "exp": int(time.time()) + int(expires_in_seconds),
    }
    raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def decode_session_token(token: str, secret_key: str) -> dict[str, Any] | None:
    """Verify HMAC signature and expiry; return {'user_id', 'role', 'exp'} or None."""
    if not token or "." not in token or not secret_key:
        return None
    try:
        payload_b64, provided_sig = token.split(".", 1)
        expected_sig = hmac.new(
            secret_key.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(provided_sig, expected_sig):
            return None
        padding = "=" * (-len(payload_b64) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        data = json.loads(decoded_bytes.decode("utf-8"))
        if int(data["exp"]) <= int(time.time()):
            return None
        return {
            "user_id": int(data["sub"]),
            "role": str(data["role"]),
            "exp": int(data["exp"]),
        }
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None
