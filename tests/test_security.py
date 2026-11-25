import pytest

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
