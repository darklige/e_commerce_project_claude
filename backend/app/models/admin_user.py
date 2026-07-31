"""AdminUser ORM model.

Platform administrator identity. Phase 1 simplification: a single
``role`` column determines the entire permission set (see
``app.core.rbac.ROLE_PERMISSIONS``). Multi-role composition tables are
deferred to later phases.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin


class AdminRole(enum.StrEnum):
    """Platform administrator role."""

    SUPER_ADMIN = "SUPER_ADMIN"
    BUSINESS_ADMIN = "BUSINESS_ADMIN"
    CUSTOMER_SERVICE_ADMIN = "CUSTOMER_SERVICE_ADMIN"
    TECH_ADMIN = "TECH_ADMIN"
    # Phase 6 — subdivided customer-service roles.
    CUSTOMER_SERVICE_LEAD = "CUSTOMER_SERVICE_LEAD"
    CUSTOMER_SERVICE_AGENT = "CUSTOMER_SERVICE_AGENT"


class AdminStatus(enum.StrEnum):
    """Lifecycle status for an AdminUser."""

    ACTIVE = "active"
    DISABLED = "disabled"


class AdminUser(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Platform administrator account."""

    __tablename__ = "admin_users"

    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, name="admin_role", native_enum=True, validate_strings=True),
        nullable=False,
    )
    status: Mapped[AdminStatus] = mapped_column(
        Enum(AdminStatus, name="admin_status", native_enum=True, validate_strings=True),
        nullable=False,
        default=AdminStatus.ACTIVE,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
