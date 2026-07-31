"""Notification service — Phase 5 contract §6.

Owns the in-app notification inbox. Best-effort semantics:
- ``notify_*`` helpers used by other services **swallow exceptions** so a
  notification failure never breaks a business transaction.
- Callers should invoke these AFTER the parent commit (or at the very end
  of the request scope) so a rollback doesn't leave dangling notifications.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException, ErrorCode
from app.models.admin_user import AdminRole, AdminUser
from app.models.merchant import MerchantAccount, MerchantAccountStatus
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationRecipientType,
)
from app.schemas.notification import NotificationOut

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fire-and-forget helpers
# ---------------------------------------------------------------------------
async def notify_user(
    session: AsyncSession,
    user_id: int,
    category: NotificationCategory,
    title: str,
    body: str,
    *,
    action_url: str | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    """Send a single notification to a user; swallow errors."""
    try:
        row = Notification(
            recipient_type=NotificationRecipientType.USER,
            recipient_id=user_id,
            category=category,
            title=title,
            body=body,
            action_url=action_url,
            related_type=related_type,
            related_id=related_id,
        )
        session.add(row)
        await session.flush()
    except Exception as exc:
        logger.warning("notify_user failed user_id=%s err=%s", user_id, exc)


async def notify_merchants_of_shop(
    session: AsyncSession,
    shop_id: int,
    category: NotificationCategory,
    title: str,
    body: str,
    *,
    action_url: str | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    """Broadcast to every ACTIVE merchant account of ``shop_id``."""
    try:
        stmt = select(MerchantAccount.id).where(
            MerchantAccount.shop_id == shop_id,
            MerchantAccount.deleted_at.is_(None),
            MerchantAccount.status == MerchantAccountStatus.ACTIVE,
        )
        account_ids = list((await session.execute(stmt)).scalars().all())
        for aid in account_ids:
            session.add(
                Notification(
                    recipient_type=NotificationRecipientType.MERCHANT,
                    recipient_id=aid,
                    category=category,
                    title=title,
                    body=body,
                    action_url=action_url,
                    related_type=related_type,
                    related_id=related_id,
                )
            )
        await session.flush()
    except Exception as exc:
        logger.warning("notify_merchants_of_shop failed shop_id=%s err=%s", shop_id, exc)


async def notify_admin(
    session: AsyncSession,
    admin_id: int,
    category: NotificationCategory,
    title: str,
    body: str,
    *,
    action_url: str | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    """Send a single notification to one admin; swallow errors."""
    try:
        session.add(
            Notification(
                recipient_type=NotificationRecipientType.ADMIN,
                recipient_id=admin_id,
                category=category,
                title=title,
                body=body,
                action_url=action_url,
                related_type=related_type,
                related_id=related_id,
            )
        )
        await session.flush()
    except Exception as exc:
        logger.warning("notify_admin failed admin_id=%s err=%s", admin_id, exc)


async def notify_admins(
    session: AsyncSession,
    category: NotificationCategory,
    title: str,
    body: str,
    *,
    role_filter: AdminRole | None = None,
    action_url: str | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    """Broadcast to admin_users, optionally filtered by role."""
    try:
        stmt = select(AdminUser.id).where(AdminUser.deleted_at.is_(None))
        if role_filter is not None:
            stmt = stmt.where(AdminUser.role == role_filter)
        admin_ids = list((await session.execute(stmt)).scalars().all())
        for aid in admin_ids:
            session.add(
                Notification(
                    recipient_type=NotificationRecipientType.ADMIN,
                    recipient_id=aid,
                    category=category,
                    title=title,
                    body=body,
                    action_url=action_url,
                    related_type=related_type,
                    related_id=related_id,
                )
            )
        await session.flush()
    except Exception as exc:
        logger.warning("notify_admins failed err=%s", exc)


# ---------------------------------------------------------------------------
# Inbox queries
# ---------------------------------------------------------------------------
def _parse_category(value: str | None) -> NotificationCategory | None:
    if value is None:
        return None
    try:
        return NotificationCategory(value)
    except ValueError as exc:
        raise AppException(
            ErrorCode.VALIDATION_ERROR, f"unknown notification category '{value}'"
        ) from exc


async def list_(
    session: AsyncSession,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
    is_read: bool | None,
    category: str | None,
    page: int,
    size: int,
) -> tuple[list[NotificationOut], int, int]:
    where: list[Any] = [
        Notification.recipient_type == recipient_type,
        Notification.recipient_id == recipient_id,
    ]
    if is_read is not None:
        where.append(Notification.is_read.is_(is_read))
    cat = _parse_category(category)
    if cat is not None:
        where.append(Notification.category == cat)

    total = int(
        (
            await session.execute(select(func.count(Notification.id)).where(and_(*where)))
        ).scalar_one()
    )
    unread_total = int(
        (
            await session.execute(
                select(func.count(Notification.id)).where(
                    Notification.recipient_type == recipient_type,
                    Notification.recipient_id == recipient_id,
                    Notification.is_read.is_(False),
                )
            )
        ).scalar_one()
    )
    stmt = (
        select(Notification)
        .where(and_(*where))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return [NotificationOut.model_validate(r) for r in rows], total, unread_total


async def get_unread_count(
    session: AsyncSession,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.recipient_type == recipient_type,
        Notification.recipient_id == recipient_id,
        Notification.is_read.is_(False),
    )
    return int((await session.execute(stmt)).scalar_one())


async def _load_owned(
    session: AsyncSession,
    notification_id: int,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
) -> Notification:
    row = await session.get(Notification, notification_id)
    if row is None:
        raise AppException(ErrorCode.NOTIFICATION_NOT_FOUND, "notification not found")
    if row.recipient_type != recipient_type or row.recipient_id != recipient_id:
        raise AppException(
            ErrorCode.NOTIFICATION_PERMISSION_DENIED,
            "notification does not belong to caller",
        )
    return row


async def mark_read(
    session: AsyncSession,
    notification_id: int,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
) -> NotificationOut:
    row = await _load_owned(
        session, notification_id, recipient_type=recipient_type, recipient_id=recipient_id
    )
    if not row.is_read:
        row.is_read = True
        row.read_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(row)
    return NotificationOut.model_validate(row)


async def mark_all_read(
    session: AsyncSession,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
) -> int:
    now = datetime.now(UTC)
    stmt = (
        update(Notification)
        .where(
            Notification.recipient_type == recipient_type,
            Notification.recipient_id == recipient_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now)
    )
    result = await session.execute(stmt)
    await session.flush()
    return int(result.rowcount or 0)


async def delete_(
    session: AsyncSession,
    notification_id: int,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
) -> None:
    row = await _load_owned(
        session, notification_id, recipient_type=recipient_type, recipient_id=recipient_id
    )
    await session.delete(row)
    await session.flush()


async def delete_all_read(
    session: AsyncSession,
    *,
    recipient_type: NotificationRecipientType,
    recipient_id: int,
) -> int:
    stmt = delete(Notification).where(
        Notification.recipient_type == recipient_type,
        Notification.recipient_id == recipient_id,
        Notification.is_read.is_(True),
    )
    result = await session.execute(stmt)
    await session.flush()
    return int(result.rowcount or 0)


__all__ = [
    "delete_",
    "delete_all_read",
    "get_unread_count",
    "list_",
    "mark_all_read",
    "mark_read",
    "notify_admin",
    "notify_admins",
    "notify_merchants_of_shop",
    "notify_user",
]
