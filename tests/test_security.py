import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import hash_password, verify_password


def test_hash_password_produces_bcrypt_hash() -> None:
    hashed_first = hash_password("Secret123!")
    hashed_second = hash_password("Secret123!")

    assert hashed_first != "Secret123!"
    assert hashed_first.startswith("$2")
    assert hashed_first != hashed_second


def test_verify_password_success_and_failure() -> None:
    hashed = hash_password("SneakerMonitor2026!")

    assert verify_password("SneakerMonitor2026!", hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password("SneakerMonitor2026!", "not-a-valid-hash") is False


def test_hash_password_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_hash_password_rejects_whitespace_only() -> None:
    with pytest.raises(ValueError):
        hash_password("   \t\n ")


def test_hash_password_rejects_over_72_utf8_bytes() -> None:
    with pytest.raises(ValueError, match="72"):
        hash_password("a" * 73)

    # Multi-byte Unicode characters (each 'ă' is 2 UTF-8 bytes; 37 * 2 = 74 bytes)
    with pytest.raises(ValueError, match="72"):
        hash_password("ă" * 37)

    # Exactly 72 bytes should succeed
    exact_72 = hash_password("a" * 72)
    assert verify_password("a" * 72, exact_72) is True


def test_verify_password_handles_unicode_over_72_bytes_and_invalid_types() -> None:
    hashed_72 = hash_password("a" * 72)
    unicode_pw = "parolă-țară-2026!"
    hashed_unicode = hash_password(unicode_pw)

    assert verify_password(unicode_pw, hashed_unicode) is True
    assert verify_password("a" * 73, hashed_72) is False
    assert verify_password("🔑" * 19, hashed_72) is False
    assert verify_password(None, hashed_72) is False  # type: ignore[arg-type]
    assert verify_password("Secret123!", None) is False  # type: ignore[arg-type]


def test_settings_enforces_d002_politeness_bounds_and_prod_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(DEFAULT_MIN_DELAY_SECONDS=9)

    with pytest.raises(ValidationError):
        Settings(DEFAULT_MAX_REQUESTS_PER_HOUR=31)

    with pytest.raises(ValidationError):
        Settings(DEFAULT_POLLING_INTERVAL_MINUTES=0)

    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production")
