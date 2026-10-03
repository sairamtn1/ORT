from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ...dependencies import get_current_user
from ...schemas import (
    LoginRequest,
    OtpRequest,
    OtpRequestResponse,
    OtpVerify,
    TokenResponse,
    UserCreate,
    UserRead,
)
from ...services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserRead:
    return await register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    token, expires_in, _ = await authenticate_user(db, payload)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserRead)
async def me(user=Depends(get_current_user)) -> UserRead:
    return user


@router.post("/otp/request", response_model=OtpRequestResponse)
async def request_otp(payload: OtpRequest, db: AsyncSession = Depends(get_db)) -> OtpRequestResponse:
    from ...services.otp_service import request_phone_otp

    return await request_phone_otp(db, payload)


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(payload: OtpVerify, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    from ...services.otp_service import verify_phone_otp

    token, expires_in = await verify_phone_otp(db, payload)
    return TokenResponse(access_token=token, expires_in=expires_in)