"""Parol (argon2id), JWT, API kalitlar, HMAC va simmetrik shifrlash."""
import base64
import hashlib
import hmac
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet

from app.core.config import settings

_ph = PasswordHasher()
_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.APP_SECRET_KEY.encode()).digest()))

JWT_ALG = "HS256"


# ---------- Parollar ----------
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


# ---------- JWT ----------
def create_token(sub: str, kind: str, ttl: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "typ": kind, "iat": now, "exp": now + ttl, "jti": uuid.uuid4().hex}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=JWT_ALG)


def create_access_token(user_id: str) -> str:
    return create_token(user_id, "access", timedelta(minutes=settings.JWT_ACCESS_TTL_MIN))


def create_refresh_token(user_id: str) -> str:
    return create_token(user_id, "refresh", timedelta(days=settings.JWT_REFRESH_TTL_DAYS))


def decode_token(token: str, kind: str) -> dict[str, Any] | None:
    try:
        data = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None
    return data if data.get("typ") == kind else None


# ---------- API kalitlar ----------
def generate_public_key() -> str:
    return "pk_live_" + secrets.token_urlsafe(18)


def generate_secret_key() -> str:
    return "sk_live_" + secrets.token_urlsafe(32)


def generate_webhook_secret() -> str:
    return "whsec_" + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    """Secret key faqat hash ko'rinishida saqlanadi (HMAC-SHA256, server sirli kaliti bilan)."""
    return hmac.new(settings.APP_SECRET_KEY.encode(), key.encode(), hashlib.sha256).hexdigest()


def encrypt(value: str) -> bytes:
    return _fernet.encrypt(value.encode())


def decrypt(value: bytes) -> str:
    return _fernet.decrypt(value).decode()


# ---------- HMAC webhook ----------
def sign_payload(secret: str, timestamp: str, body: bytes) -> str:
    msg = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify_signature(secret: str, timestamp: str | None, body: bytes, signature: str | None,
                     tolerance_s: int = 300) -> bool:
    """HMAC + timestamp (±5 daq) — replay hujumidan himoya."""
    if not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > tolerance_s:
        return False
    expected = sign_payload(secret, timestamp, body)
    return hmac.compare_digest(expected, signature)


def short_hash(value: str, n: int = 4) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:n]
