import asyncio
import base64
import hashlib
import hmac
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import OtpChallenge, User, UserRole
from ..schemas import OtpRequest, OtpRequestResponse, OtpVerify
from ..security import create_access_token

OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_SEND_INTERVAL_SECONDS = 60
OTP_HOURLY_LIMIT = 5


def _code_hash(phone: str, code: str) -> str:
    secret = get_settings().signing_secret.encode()
    return hmac.new(secret, f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def _send_twilio_sms(phone: str, code: str) -> None:
    settings = get_settings()
    if not all((settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phone verification is not configured",
        )
    account_sid = settings.twilio_account_sid
    auth_token = settings.twilio_auth_token
    form = urllib.parse.urlencode(
        {
            "To": phone,
            "From": settings.twilio_from_number,
            "Body": f"Your ORT verification code is {code}. It expires in 5 minutes.",
        }
    ).encode()
    request = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        data=form,
        headers={
            "Authorization": "Basic "
            + base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status not in (200, 201):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Phone verification provider rejected the request",
                )
    except urllib.error.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Phone verification provider rejected the request",
        ) from exc
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Phone verification provider is unavailable",
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Phone verification provider timed out",
        ) from exc


async def request_phone_otp(db: AsyncSession, payload: OtpRequest) -> OtpRequestResponse:
    settings = get_settings()
    development_delivery = settings.app_env == "development" and settings.otp_dev_mode
    if not development_delivery and not all(
        (settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number)
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phone verification is not configured",
        )

    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:phone))"), {"phone": payload.phone}
    )
    now = datetime.now(timezone.utc)
    recent = await db.scalar(
        select(func.count())
        .select_from(OtpChallenge)
        .where(
            OtpChallenge.phone == payload.phone,
            OtpChallenge.created_at >= now - timedelta(hours=1),
        )
    )
    if recent and recent >= OTP_HOURLY_LIMIT:
        raise HTTPException(status_code=429, detail="Too many verification requests. Try again later.")
    last_sent = await db.scalar(
        select(OtpChallenge.created_at)
        .where(OtpChallenge.phone == payload.phone)
        .order_by(OtpChallenge.created_at.desc())
        .limit(1)
    )
    if last_sent and (now - last_sent).total_seconds() < OTP_SEND_INTERVAL_SECONDS:
        raise HTTPException(status_code=429, detail="Please wait before requesting another code.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OtpChallenge(
        phone=payload.phone,
        full_name=payload.full_name,
        code_hash=_code_hash(payload.phone, code),
        expires_at=now + timedelta(seconds=OTP_TTL_SECONDS),
    )
    await db.execute(
        update(OtpChallenge)
        .where(
            OtpChallenge.phone == payload.phone,
            OtpChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    db.add(challenge)
    if not development_delivery:
        await asyncio.to_thread(_send_twilio_sms, payload.phone, code)
    await db.commit()
    return OtpRequestResponse(
        expires_in=OTP_TTL_SECONDS,
        dev_code=code if development_delivery else None,
    )


async def verify_phone_otp(db: AsyncSession, payload: OtpVerify) -> tuple[str, int]:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:phone))"), {"phone": payload.phone}
    )
    challenge = await db.scalar(
        select(OtpChallenge)
        .where(
            OtpChallenge.phone == payload.phone,
            OtpChallenge.consumed_at.is_(None),
        )
        .order_by(OtpChallenge.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if not challenge:
        raise HTTPException(status_code=401, detail="Invalid or expired verification code")
    if challenge.expires_at <= now or challenge.attempts >= OTP_MAX_ATTEMPTS:
        challenge.consumed_at = now
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired verification code")
    challenge.attempts += 1
    if not hmac.compare_digest(challenge.code_hash, _code_hash(payload.phone, payload.code)):
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired verification code")

    await db.execute(
        update(OtpChallenge)
        .where(
            OtpChallenge.phone == payload.phone,
            OtpChallenge.id != challenge.id,
            OtpChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    challenge.consumed_at = now
    user = await db.scalar(select(User).where(User.phone == payload.phone).with_for_update())
    if user and user.status.value != "active":
        await db.commit()
        raise HTTPException(status_code=403, detail="User account is not active")
    if not user:
        suffix = hashlib.sha256(payload.phone.encode()).hexdigest()[:16]
        user = User(
            email=f"{suffix}@users.example.com",
            password_hash=secrets.token_urlsafe(32),
            full_name=challenge.full_name or "ORT Driver",
            phone=payload.phone,
            role=UserRole.customer,
        )
        db.add(user)
    await db.flush()
    token, expires_in = create_access_token(str(user.id), user.role.value)
    await db.commit()
    return token, expires_in
