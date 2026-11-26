
"""Apache Guacamole encrypted JSON authentication."""

import base64
import hashlib
import hmac
import json

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def encrypt_guacamole_json(payload: dict, secret_hex: str) -> str:
    """
    Sign and encrypt a Guacamole JSON authentication payload.

    Format:
        HMAC-SHA256(JSON) + JSON
        AES-128-CBC with zero IV
        PKCS7 padding
        Base64 encoding
    """

    if not isinstance(secret_hex, str):
        raise ValueError("Guacamole secret must be a hexadecimal string")

    if len(secret_hex) != 32:
        raise ValueError(
            "Guacamole secret must contain exactly 32 hexadecimal characters"
        )

    try:
        key = bytes.fromhex(secret_hex)
    except ValueError as exc:
        raise ValueError(
            "Guacamole secret contains invalid hexadecimal characters"
        ) from exc

    if len(key) != 16:
        raise ValueError("Guacamole secret must represent exactly 16 bytes")

    if not isinstance(payload, dict):
        raise ValueError("Guacamole payload must be a dictionary")

    json_bytes = json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    signature = hmac.new(
        key,
        json_bytes,
        hashlib.sha256,
    ).digest()

    plaintext = signature + json_bytes

    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()

    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(bytes(16)),
    )

    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()

    return base64.b64encode(encrypted).decode("ascii")
