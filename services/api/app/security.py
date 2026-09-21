from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from .config import get_settings

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_minutes * 60
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.signing_secret, algorithm=settings.jwt_algorithm), expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.signing_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "exp", "type"]},
    )