"""Password hashing (bcrypt), password policy and JWT helpers."""
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# Used when the email is unknown, so response time doesn't reveal whether an account exists.
DUMMY_HASH = hash_password("dummy-password-for-timing-only")


def check_password_policy(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    if len(password.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes (bcrypt limit)")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Password must contain letters and digits")
    return password


def generate_password() -> str:
    while True:
        pw = secrets.token_urlsafe(12)
        try:
            return check_password_policy(pw)
        except ValueError:
            continue


def create_access_token(user) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "tv": user.token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
