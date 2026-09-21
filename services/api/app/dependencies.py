import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import User, UserRole
from .security import bearer_scheme, decode_access_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError, TypeError, jwt.PyJWTError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user or user.status.value != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active")
    return user


def require_roles(*roles: UserRole) -> Callable:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency
