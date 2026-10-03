import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Admin, Owner, User, UserRole
from ..schemas import LoginRequest, UserCreate
from ..security import create_access_token, hash_password, verify_password


async def register_user(db: AsyncSession, payload: UserCreate) -> User:
    if payload.role in (UserRole.staff, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff and admin accounts must be provisioned by an existing administrator",
        )
    existing = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    if payload.role == UserRole.owner:
        db.add(Owner(user_id=user.id))
    elif payload.role == UserRole.admin:
        db.add(Admin(user_id=user.id))
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, payload: LoginRequest) -> tuple[str, int, User]:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.status.value != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active")
    token, expires_in = create_access_token(str(user.id), user.role.value)
    return token, expires_in, user


async def get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user