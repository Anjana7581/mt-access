
import pytest

from cryptography.fernet import Fernet

from app.config import settings
from app.services.credential_crypto import (
    decrypt_credential,
    encrypt_credential,
)


def test_credential_encryption_round_trip():
    original = "Test-Windows-Password-123!"

    encrypted = encrypt_credential(original)

    assert encrypted != original
    assert decrypt_credential(encrypted) == original


def test_encryption_uses_randomized_ciphertext():
    value = "Same-Password-123!"

    first = encrypt_credential(value)
    second = encrypt_credential(value)

    assert first != second
    assert decrypt_credential(first) == value
    assert decrypt_credential(second) == value


def test_empty_credential_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        encrypt_credential("")


def test_invalid_encrypted_value_rejected():
    with pytest.raises(ValueError, match="Unable to decrypt"):
        decrypt_credential("not-a-valid-encrypted-value")


def test_missing_encryption_key_rejected(monkeypatch):
    monkeypatch.setattr(settings, "rdp_credential_encryption_key", "")

    with pytest.raises(RuntimeError, match="not configured"):
        encrypt_credential("test-password")


def test_invalid_encryption_key_rejected(monkeypatch):
    monkeypatch.setattr(
        settings,
        "rdp_credential_encryption_key",
        "invalid-key",
    )

    with pytest.raises(RuntimeError, match="Invalid"):
        encrypt_credential("test-password")
