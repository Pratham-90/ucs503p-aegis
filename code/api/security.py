"""Password hashing (argon2id, NFR-SEC-3), session JWTs, secret comparison."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Response

from .config import Settings

COOKIE_NAME = "aegis_session"
_hasher = PasswordHasher()  # argon2id with the library's current recommended parameters


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def make_session_token(owner_id: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {"sub": owner_id, "iat": now, "exp": now + timedelta(hours=settings.session_hours)}
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def read_session_token(token: str, settings: Settings) -> str | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        return None


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite="lax",
                        max_age=settings.session_hours * 3600, path="/")


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax")


def secrets_match(provided: str | None, expected: str) -> bool:
    """Constant-time comparison; an unset secret never matches."""
    return bool(expected) and provided is not None and hmac.compare_digest(provided, expected)
