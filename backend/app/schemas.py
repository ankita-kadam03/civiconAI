from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["CITIZEN", "OFFICER", "ADMIN", "ADMIN_L1", "ADMIN_L2", "ADMIN_L3"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Status = Literal[
    "SUBMITTED",
    "ACKNOWLEDGED",
    "IN_PROGRESS",
    "MORE_INFO_REQUESTED",
    "ESCALATED",
    "RESOLVED",
    "CLOSED",
    "REJECTED",
]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=2, max_length=80)
    locality: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=72)


class RefreshIn(BaseModel):
    refresh_token: str | None = None


class UserOut(ORM):
    id: str
    email: EmailStr
    display_name: str
    phone: str | None = None
    role: Role
    department_id: str | None = None
    locality: str | None = None
    date_of_birth: str | None = None
    is_active: bool = True
    demo_account: bool = False


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
    reset_token: str | None = None


class ProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    locality: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    date_of_birth: str | None = Field(default=None, max_length=32)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    history: list[dict[str, str]] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


class ComplaintCreate(BaseModel):
    title: str = Field(min_length=6, max_length=140)
    description: str = Field(min_length=12, max_length=4000)
    category_id: str
    locality: str = Field(min_length=2, max_length=160)
    address: str | None = Field(default=None, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    occurred_at: datetime | None = None
    is_public: bool = True
    photo_count: int | None = Field(default=0, ge=0, le=20)

    @field_validator("title", "description", "locality")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class StatusUpdateIn(BaseModel):
    status: Status
    note: str | None = Field(default=None, max_length=1000)


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    is_internal: bool = False


class AssignIn(BaseModel):
    officer_id: str
    note: str | None = Field(default=None, max_length=400)


class EscalateIn(BaseModel):
    reason: str = Field(min_length=8, max_length=400)


class ClassifyIn(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(min_length=8, max_length=4000)
    locality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    photo_count: int | None = Field(default=0, ge=0, le=20)


class RolePatch(BaseModel):
    role: Role
    department_id: str | None = None
    is_active: bool | None = None


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str = Field(min_length=2, max_length=40)
    department_id: str | None = None
    review_hours: int = Field(default=24, ge=1, le=720)
    resolve_hours: int = Field(default=168, ge=1, le=2160)
    icon: str = "map-pin"
    is_active: bool = True


class DepartmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    code: str = Field(min_length=2, max_length=8)
    description: str | None = None
    contact_hint: str | None = None


class EscalationRuleIn(BaseModel):
    category_id: str | None = None
    severity: Severity | None = None
    level: int = Field(default=1, ge=1, le=3)
    review_hours: int = Field(ge=1, le=720)
    resolve_hours: int = Field(ge=1, le=2160)
    reason: str = Field(min_length=4, max_length=240)
    is_active: bool = True


class FcmTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=4096)


class Page(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class VerifyIn(BaseModel):
    answer: Literal["resolved", "unresolved"]


class SavedLocationIn(BaseModel):
    label: str = Field(default="Saved place", max_length=80)
    lat: float
    lng: float
    radius_m: int = Field(default=800, ge=50, le=5000)
