"""Admin-domain request/response schemas."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.admin_user import AdminRole, AdminStatus
from app.models.audit_log import AuditActorType

# Matches the admin-web frontend strength rule: 8-64 non-space chars with
# at least one letter and one digit.
_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[\S]{8,64}$")


def _validate_password(value: str) -> str:
    if not _PASSWORD_RE.match(value):
        raise ValueError("password must be 8-64 characters with letters and digits")
    return value


class AdminLoginIn(BaseModel):
    """Admin login payload."""

    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=64)


class AdminOut(BaseModel):
    """Admin projection."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: AdminRole
    status: AdminStatus


class AdminMeOut(BaseModel):
    """``GET /admin/me`` response — admin + perms."""

    admin: AdminOut
    permissions: list[str]


class AdminUserOut(AdminOut):
    """Full admin projection for the account-management console."""

    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None
    created_at: datetime


class AdminCreateIn(BaseModel):
    """Create an admin account (SUPER only, Phase 6)."""

    username: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=60)
    role: AdminRole
    password: str = Field(min_length=8, max_length=64)

    _password = field_validator("password")(_validate_password)


class AdminUpdateIn(BaseModel):
    """Update an admin account — display_name and/or role."""

    display_name: str | None = Field(default=None, min_length=1, max_length=60)
    role: AdminRole | None = None


class AdminResetPasswordIn(BaseModel):
    """Reset another admin's password (operator supplies the new one)."""

    new_password: str = Field(min_length=8, max_length=64)

    _new_password = field_validator("new_password")(_validate_password)


class AdminChangePasswordIn(BaseModel):
    """Self-service password change."""

    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)

    _new_password = field_validator("new_password")(_validate_password)


class AuditLogOut(BaseModel):
    """Projection of one audit_logs row for the console."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_type: AuditActorType
    actor_id: int | None = None
    action: str
    target_type: str | None = None
    target_id: int | None = None
    ip: str | None = None
    created_at: datetime
    extra: dict[str, object] | None = None


__all__ = [
    "AdminChangePasswordIn",
    "AdminCreateIn",
    "AdminLoginIn",
    "AdminMeOut",
    "AdminOut",
    "AdminResetPasswordIn",
    "AdminUpdateIn",
    "AdminUserOut",
    "AuditLogOut",
]
