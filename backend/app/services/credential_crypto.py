
"""Encrypt and decrypt Windows RDP credentials at rest."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    key = settings.rdp_credential_encryption_key

    if not key:
        raise RuntimeError("RDP credential encryption is not configured.")

    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("Invalid RDP credential encryption key.") from exc


def encrypt_credential(value: str) -> str:
    """Encrypt one Windows credential for database storage."""

    if not isinstance(value, str) or not value:
        raise ValueError("Credential must be a non-empty string.")

    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_credential(encrypted_value: str) -> str:
    """Decrypt a stored Windows credential."""

    if not isinstance(encrypted_value, str) or not encrypted_value:
        raise ValueError("Encrypted credential is required.")

    try:
        decrypted = _fernet().decrypt(encrypted_value.encode("ascii"))
        return decrypted.decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError, UnicodeEncodeError) as exc:
        raise ValueError("Unable to decrypt stored credential.") from exc
