
import base64
import hashlib
import hmac
import json

import pytest

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.services.crypto import encrypt_guacamole_json


TEST_SECRET = "0123456789abcdef0123456789abcdef"


def test_guacamole_json_encryption_round_trip():
    payload = {
        "username": "test-client",
        "expires": 1800000000000,
        "connections": {},
    }

    result = encrypt_guacamole_json(payload, TEST_SECRET)

    encrypted = base64.b64decode(result)

    decryptor = Cipher(
        algorithms.AES(bytes.fromhex(TEST_SECRET)),
        modes.CBC(bytes(16)),
    ).decryptor()

    padded = decryptor.update(encrypted) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    signature = plaintext[:32]
    json_bytes = plaintext[32:]

    expected_signature = hmac.new(
        bytes.fromhex(TEST_SECRET),
        json_bytes,
        hashlib.sha256,
    ).digest()

    assert hmac.compare_digest(signature, expected_signature)
    assert json.loads(json_bytes.decode("utf-8")) == payload


def test_invalid_secret_length():
    with pytest.raises(ValueError):
        encrypt_guacamole_json({}, "invalid")


def test_invalid_secret_characters():
    with pytest.raises(ValueError):
        encrypt_guacamole_json({}, "z" * 32)


def test_payload_must_be_dictionary():
    with pytest.raises(ValueError):
        encrypt_guacamole_json([], TEST_SECRET)
