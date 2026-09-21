import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from .models import (
    AccountStatus,
    BookingStatus,
    LotStatus,
    NotificationStatus,
    PaymentStatus,
    ReviewStatus,
    SlotStatus,
    UserRole,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=32)
    role: UserRole = UserRole.customer


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=32)
    status: AccountStatus | None = None
    role: UserRole | None = None


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None
    role: UserRole
    status: AccountStatus
    created_at: datetime
    updated_at: datetime


class OwnerCreate(BaseModel):
    user_id: uuid.UUID
    business_name: str | None = Field(default=None, max_length=200)
    government_id: str | None = Field(default=None, max_length=120)
    verified: bool = False


class OwnerUpdate(BaseModel):
    business_name: str | None = Field(default=None, max_length=200)
    government_id: str | None = Field(default=None, max_length=120)
    verified: bool | None = None


class OwnerRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str | None
    government_id: str | None
    verified: bool
    created_at: datetime
    updated_at: datetime


class AdminCreate(BaseModel):
    user_id: uuid.UUID
    permissions: dict = Field(default_factory=dict)


class AdminUpdate(BaseModel):
    permissions: dict | None = None


class AdminRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    permissions: dict
    created_at: datetime
    updated_at: datetime


class ParkingLotCreate(BaseModel):
    owner_id: uuid.UUID
    name: str = Field(min_length=2, max_length=180)
    address: str = Field(min_length=2, max_length=300)
    city: str = Field(min_length=2, max_length=100)
    latitude: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    description: str | None = None
    status: LotStatus = LotStatus.draft


class ParkingLotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    address: str | None = Field(default=None, min_length=2, max_length=300)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    description: str | None = None
    status: LotStatus | None = None


class ParkingLotRead(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    address: str
    city: str
    latitude: Decimal
    longitude: Decimal
    description: str | None
    status: LotStatus
    created_at: datetime
    updated_at: datetime


class ParkingSlotCreate(BaseModel):
    parking_lot_id: uuid.UUID
    slot_number: str = Field(min_length=1, max_length=40)
    vehicle_type: str = Field(default="car", min_length=2, max_length=40)
    hourly_rate: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)
    status: SlotStatus = SlotStatus.available


class ParkingSlotUpdate(BaseModel):
    slot_number: str | None = Field(default=None, min_length=1, max_length=40)
    vehicle_type: str | None = Field(default=None, min_length=2, max_length=40)
    hourly_rate: Decimal | None = Field(
        default=None, gt=Decimal("0"), max_digits=10, decimal_places=2
    )
    status: SlotStatus | None = None


class ParkingSlotRead(ORMModel):
    id: uuid.UUID
    parking_lot_id: uuid.UUID
    slot_number: str
    vehicle_type: str
    hourly_rate: Decimal
    status: SlotStatus
    created_at: datetime
    updated_at: datetime


class BookingCreate(BaseModel):
    customer_id: uuid.UUID
    parking_slot_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    total_amount: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)
    status: BookingStatus = BookingStatus.pending

    @model_validator(mode="after")
    def validate_interval(self) -> "BookingCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class BookingUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    total_amount: Decimal | None = Field(
        default=None, gt=Decimal("0"), max_digits=10, decimal_places=2
    )
    status: BookingStatus | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> "BookingUpdate":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class BookingRead(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    parking_slot_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    total_amount: Decimal
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


class PaymentCreate(BaseModel):
    booking_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    provider: str | None = Field(default=None, max_length=60)
    provider_reference: str | None = Field(default=None, max_length=180)
    status: PaymentStatus = PaymentStatus.pending


class PaymentUpdate(BaseModel):
    amount: Decimal | None = Field(
        default=None, gt=Decimal("0"), max_digits=10, decimal_places=2
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    provider: str | None = Field(default=None, max_length=60)
    provider_reference: str | None = Field(default=None, max_length=180)
    status: PaymentStatus | None = None


class PaymentRead(ORMModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: Decimal
    currency: str
    provider: str | None
    provider_reference: str | None
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class ReviewCreate(BaseModel):
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    status: ReviewStatus = ReviewStatus.published


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None
    status: ReviewStatus | None = None


class ReviewRead(ORMModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    rating: int
    comment: str | None
    status: ReviewStatus
    created_at: datetime
    updated_at: datetime


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    title: str = Field(min_length=1, max_length=180)
    message: str = Field(min_length=1)
    status: NotificationStatus = NotificationStatus.unread


class NotificationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    message: str | None = Field(default=None, min_length=1)
    status: NotificationStatus | None = None
    read_at: datetime | None = None


class NotificationRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    status: NotificationStatus
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = None