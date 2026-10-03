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


class OtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    full_name: str | None = Field(default=None, min_length=2, max_length=150)


class OtpRequestResponse(BaseModel):
    expires_in: int
    dev_code: str | None = None


class OtpVerify(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    code: str = Field(pattern=r"^\d{6}$")


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
    parking_type: str = Field(default="mall", pattern=r"^(mall|hospital|airport|hotel|restaurant|valet|corporate|event)$")
    parking_mode: str = Field(default="paid", pattern=r"^(free|paid|valet|hybrid)$")
    identification_method: str = Field(default="qr_code", pattern=r"^(qr_code|session_id|vehicle_number)$")
    is_closed: bool = False
    closure_message: str | None = Field(default=None, max_length=240)


class ParkingLotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    address: str | None = Field(default=None, min_length=2, max_length=300)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    description: str | None = None
    status: LotStatus | None = None
    parking_type: str | None = Field(default=None, pattern=r"^(mall|hospital|airport|hotel|restaurant|valet|corporate|event)$")
    parking_mode: str | None = Field(default=None, pattern=r"^(free|paid|valet|hybrid)$")
    identification_method: str | None = Field(default=None, pattern=r"^(qr_code|session_id|vehicle_number)$")
    is_closed: bool | None = None
    closure_message: str | None = Field(default=None, max_length=240)


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
    parking_type: str
    parking_mode: str
    identification_method: str
    is_closed: bool
    closure_message: str | None
    created_at: datetime
    updated_at: datetime


class ParkingSlotCreate(BaseModel):
    parking_lot_id: uuid.UUID
    slot_number: str = Field(min_length=1, max_length=40)
    vehicle_type: str = Field(default="car", min_length=2, max_length=40)
    hourly_rate: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
    status: SlotStatus = SlotStatus.available
    category: str = Field(default="regular", pattern=r"^(regular|ev|disabled|vip|visitor)$")
    level_name: str | None = Field(default=None, max_length=40)
    zone_name: str | None = Field(default=None, max_length=40)
    level_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None


class ParkingSlotUpdate(BaseModel):
    slot_number: str | None = Field(default=None, min_length=1, max_length=40)
    vehicle_type: str | None = Field(default=None, min_length=2, max_length=40)
    hourly_rate: Decimal | None = Field(
        default=None, ge=Decimal("0"), max_digits=10, decimal_places=2
    )
    status: SlotStatus | None = None
    category: str | None = Field(default=None, pattern=r"^(regular|ev|disabled|vip|visitor)$")
    level_name: str | None = Field(default=None, max_length=40)
    zone_name: str | None = Field(default=None, max_length=40)
    level_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None


class ParkingSlotRead(ORMModel):
    id: uuid.UUID
    parking_lot_id: uuid.UUID
    slot_number: str
    vehicle_type: str
    hourly_rate: Decimal
    status: SlotStatus
    category: str
    level_name: str | None
    zone_name: str | None
    level_id: uuid.UUID | None
    zone_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ParkingZoneRead(ORMModel):
    id: uuid.UUID
    parking_level_id: uuid.UUID
    zone_code: str
    display_name: str


class ParkingLevelRead(ORMModel):
    id: uuid.UUID
    parking_lot_id: uuid.UUID
    level_code: str
    display_name: str
    sort_order: int
    zones: list[ParkingZoneRead]


class BookingCreate(BaseModel):
    customer_id: uuid.UUID
    parking_slot_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    total_amount: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
    status: BookingStatus = BookingStatus.pending

    @model_validator(mode="after")
    def validate_interval(self) -> "BookingCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.status != BookingStatus.pending:
            raise ValueError("New reservations must start as pending")
        return self


class BookingUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    total_amount: Decimal | None = Field(
        default=None, ge=Decimal("0"), max_digits=10, decimal_places=2
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
    corporate_pass_id: uuid.UUID | None
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


class VehicleCreate(BaseModel):
    plate_number: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9 -]+$")
    label: str = Field(default="My vehicle", min_length=1, max_length=60)
    vehicle_type: str = Field(default="car", pattern=r"^(car|motorcycle|suv|van|truck)$")
    is_default: bool = False


class VehicleRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    plate_number: str
    label: str
    vehicle_type: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ParkingSearchRead(ParkingLotRead):
    available_slots: int
    starting_hourly_rate: Decimal | None


class ParkingSessionCreate(BaseModel):
    parking_lot_id: uuid.UUID
    vehicle_id: uuid.UUID
    parking_slot_id: uuid.UUID | None = None
    entry_method: str = Field(default="online", pattern=r"^(online|walk_in|offline)$")
    emergency_priority: bool = False
    override_reason: str | None = Field(default=None, min_length=8, max_length=500)
    notes: str | None = Field(default=None, max_length=500)


class ParkingSessionAssign(BaseModel):
    parking_slot_id: uuid.UUID
    override_reason: str | None = Field(default=None, min_length=8, max_length=500)


class ParkingSessionRead(ORMModel):
    id: uuid.UUID
    public_id: str
    parking_lot_id: uuid.UUID
    parking_slot_id: uuid.UUID | None
    vehicle_id: uuid.UUID
    customer_id: uuid.UUID
    staff_user_id: uuid.UUID | None
    status: str
    entry_method: str
    entry_at: datetime
    exit_at: datetime | None
    synced_at: datetime | None
    valet_status: str
    valet_handover_at: datetime | None
    valet_retrieval_requested_at: datetime | None
    valet_retrieved_at: datetime | None
    emergency_priority: bool
    slot_override: bool
    override_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ParkingSessionCreated(ParkingSessionRead):
    qr_token: str


class IncidentCreate(BaseModel):
    parking_lot_id: uuid.UUID
    parking_session_id: uuid.UUID | None = None
    category: str = Field(pattern=r"^(safety|facility|payment|vehicle|staff|other)$")
    description: str = Field(min_length=8, max_length=4000)


class IncidentRead(ORMModel):
    id: uuid.UUID
    parking_lot_id: uuid.UUID
    reporter_id: uuid.UUID
    parking_session_id: uuid.UUID | None
    category: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class StaffAssignmentCreate(BaseModel):
    staff_user_id: uuid.UUID
    parking_lot_id: uuid.UUID


class CorporatePassCreate(BaseModel):
    parking_lot_id: uuid.UUID
    holder_user_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None
    pass_type: str = Field(pattern=r"^(permanent|visitor|executive|employee)$")
    visitor_name: str | None = Field(default=None, min_length=2, max_length=150)
    visitor_phone: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")
    starts_at: datetime
    expires_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_pass(self) -> "CorporatePassCreate":
        if self.starts_at.tzinfo is None or self.starts_at.utcoffset() is None:
            raise ValueError("starts_at must include a timezone")
        if self.expires_at and (
            self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None
        ):
            raise ValueError("expires_at must include a timezone")
        if self.expires_at and self.expires_at <= self.starts_at:
            raise ValueError("expires_at must be after starts_at")
        if self.pass_type == "visitor" and not self.visitor_name:
            raise ValueError("visitor_name is required for visitor passes")
        if self.pass_type in {"permanent", "executive", "employee"} and not self.holder_user_id:
            raise ValueError("holder_user_id is required for employee passes")
        return self


class CorporatePassRead(ORMModel):
    id: uuid.UUID
    pass_code: str
    parking_lot_id: uuid.UUID
    created_by: uuid.UUID
    holder_user_id: uuid.UUID | None
    vehicle_id: uuid.UUID | None
    pass_type: str
    visitor_name: str | None
    visitor_phone: str | None
    starts_at: datetime
    expires_at: datetime | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CorporateReservationCreate(BaseModel):
    parking_slot_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    vehicle_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> "CorporateReservationCreate":
        if any(
            value.tzinfo is None or value.utcoffset() is None
            for value in (self.starts_at, self.ends_at)
        ):
            raise ValueError("Reservation times must include a timezone")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EmergencyPriorityUpdate(BaseModel):
    emergency_priority: bool
    override_reason: str | None = Field(default=None, min_length=8, max_length=500)

    @model_validator(mode="after")
    def require_reason_for_priority(self) -> "EmergencyPriorityUpdate":
        if self.emergency_priority and not self.override_reason:
            raise ValueError("override_reason is required for emergency priority")
        return self


class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = None