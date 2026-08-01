"""Admin account management service — Phase 6.

Owns create / update / disable / enable / reset-password for platform
admins, plus the *cascade* that runs whenever an admin is disabled or
demoted:

1. Release any ``admin_arbitrating`` cases they claimed (back to the pool).
2. Revoke every refresh token they hold (kick them out within the
   access-token TTL).
3. Write an audit trail.
4. Notify the affected admin and CS leads when cases were released.

Only SUPER_ADMIN holds ``admin:user:manage``; every mutating endpoint
forbids operating on your own account.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException, ErrorCode
from app.core.rbac import Permission, permissions_for_admin
from app.core.security import hash_password
from app.models.admin_user import AdminRole, AdminStatus, AdminUser
from app.models.aftersales import Aftersales, AftersalesStatus
from app.models.aftersales_message import (
    AftersalesMessage,
    AftersalesMessageKind,
    AftersalesMessageSenderType,
)
from app.models.audit_log import AuditActorType
from app.schemas.admin import (
    AdminCreateIn,
    AdminUpdateIn,
    AdminUserOut,
)
from app.services.audit_service import write_audit
from app.services.auth_service import revoke_all_sessions_for_admin


def _now() -> datetime:
    return datetime.now(UTC)


def _can_arbitrate(role: AdminRole) -> bool:
    return Permission.ADMIN_AFTERSALES_ARBITRATE in permissions_for_admin(role)


async def _load_admin(session: AsyncSession, admin_id: int) -> AdminUser:
    row = await session.get(AdminUser, admin_id)
    if row is None or row.deleted_at is not None:
        raise AppException(ErrorCode.ADMIN_NOT_FOUND, "admin not found")
    return row


async def _count_active_super(session: AsyncSession) -> int:
    stmt = select(func.count(AdminUser.id)).where(
        AdminUser.role == AdminRole.SUPER_ADMIN,
        AdminUser.status == AdminStatus.ACTIVE,
        AdminUser.deleted_at.is_(None),
    )
    return int((await session.execute(stmt)).scalar_one())


async def _guard_not_last_super(
    session: AsyncSession,
    target: AdminUser,
    new_role: AdminRole | None = None,
) -> None:
    """Refuse to demote/disable the only remaining ACTIVE super admin."""
    if target.role != AdminRole.SUPER_ADMIN:
        return
    if new_role == AdminRole.SUPER_ADMIN:
        return
    if await _count_active_super(session) <= 1:
        raise AppException(
            ErrorCode.ADMIN_LAST_SUPER_ADMIN,
            "cannot demote or disable the last active super admin",
        )


async def _release_claimed_arbitrations(session: AsyncSession, admin_id: int) -> int:
    """Release in-progress arbitration cases claimed by ``admin_id``.

    Only touches cases still awaiting a verdict
    (``status = admin_arbitrating`` and ``arbitrated_at IS NULL``).
    Returns how many were released.
    """
    stmt = select(Aftersales).where(
        Aftersales.arbitrator_admin_id == admin_id,
        Aftersales.status == AftersalesStatus.ADMIN_ARBITRATING,
        Aftersales.arbitrated_at.is_(None),
        Aftersales.deleted_at.is_(None),
    )
    rows = list((await session.execute(stmt)).scalars().all())
    for row in rows:
        row.arbitrator_admin_id = None
        session.add(
            AftersalesMessage(
                aftersales_id=row.id,
                sender_type=AftersalesMessageSenderType.SYSTEM,
                sender_id=None,
                kind=AftersalesMessageKind.SYSTEM_NOTICE,
                content="case released back to the pool (handler disabled / demoted)",
            )
        )
    await session.flush()
    return len(rows)


async def _notify_target_admin(session: AsyncSession, admin_id: int, title: str, body: str) -> None:
    """Best-effort notification to one admin."""
    try:
        from app.models.notification import NotificationCategory
        from app.services import notification_service

        await notification_service.notify_admin(
            session,
            admin_id,
            NotificationCategory.SYSTEM,
            title,
            body,
        )
    except Exception:
        pass


async def _notify_release(session: AsyncSession, released: int, admin_id: int) -> None:
    """Best-effort broadcast to CS leads when cases hit the pool."""
    if released <= 0:
        return
    try:
        from app.models.notification import NotificationCategory
        from app.services import notification_service

        await notification_service.notify_admins(
            session,
            NotificationCategory.AFTERSALES,
            title="仲裁单已释放回待认领池",
            body=f"管理员 #{admin_id} 被禁用/降权，{released} 张未完成仲裁单已释放",
            role_filter=AdminRole.CUSTOMER_SERVICE_LEAD,
            action_url="/admin/aftersales",
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
async def admin_list(
    session: AsyncSession,
    *,
    role: AdminRole | None,
    status_: AdminStatus | None,
    keyword: str | None,
    page: int,
    size: int,
) -> tuple[list[AdminUserOut], int]:
    where: list[object] = [AdminUser.deleted_at.is_(None)]
    if role is not None:
        where.append(AdminUser.role == role)
    if status_ is not None:
        where.append(AdminUser.status == status_)
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append(or_(AdminUser.username.ilike(kw), AdminUser.display_name.ilike(kw)))
    total_stmt = select(func.count(AdminUser.id)).where(and_(*where))
    total = int((await session.execute(total_stmt)).scalar_one())
    stmt = (
        select(AdminUser)
        .where(and_(*where))
        .order_by(AdminUser.created_at.desc(), AdminUser.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [AdminUserOut.model_validate(r) for r in rows], total


async def admin_get(session: AsyncSession, admin_id: int) -> AdminUserOut:
    row = await _load_admin(session, admin_id)
    return AdminUserOut.model_validate(row)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------
async def admin_create(
    session: AsyncSession,
    operator: AdminUser,
    payload: AdminCreateIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AdminUserOut:
    exists = (
        await session.execute(select(AdminUser.id).where(AdminUser.username == payload.username))
    ).scalar_one_or_none()
    if exists is not None:
        raise AppException(ErrorCode.ADMIN_USERNAME_TAKEN, "username already taken")

    now = _now()
    row = AdminUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=payload.role,
        status=AdminStatus.ACTIVE,
        password_changed_at=now,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)

    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=operator.id,
        action="admin.user.create",
        target_type="admin_user",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"username": row.username, "role": row.role.value},
    )
    return AdminUserOut.model_validate(row)


async def admin_update(
    session: AsyncSession,
    operator: AdminUser,
    admin_id: int,
    payload: AdminUpdateIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AdminUserOut:
    if admin_id == operator.id:
        raise AppException(
            ErrorCode.ADMIN_CANNOT_OPERATE_SELF,
            "cannot change your own role through the console",
        )
    row = await _load_admin(session, admin_id)

    changed: list[str] = []
    released = 0
    if payload.display_name is not None and payload.display_name != row.display_name:
        row.display_name = payload.display_name
        changed.append("display_name")
    if payload.role is not None and payload.role != row.role:
        await _guard_not_last_super(session, row, payload.role)
        old_role = row.role
        row.role = payload.role
        changed.append(f"role:{old_role.value}->{payload.role.value}")
        if not _can_arbitrate(payload.role):
            released = await _release_claimed_arbitrations(session, row.id)
        await revoke_all_sessions_for_admin(session, row.id)

    if not changed:
        return AdminUserOut.model_validate(row)

    await session.flush()
    await session.refresh(row)

    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=operator.id,
        action="admin.user.role_change",
        target_type="admin_user",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"changes": changed, "released_arbitrations": released},
    )
    await _notify_target_admin(
        session,
        row.id,
        "您的管理员角色已变更",
        f"当前角色：{row.role.value}",
    )
    if released:
        await _notify_release(session, released, row.id)
    return AdminUserOut.model_validate(row)


async def admin_disable(
    session: AsyncSession,
    operator: AdminUser,
    admin_id: int,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AdminUserOut:
    if admin_id == operator.id:
        raise AppException(
            ErrorCode.ADMIN_CANNOT_OPERATE_SELF,
            "cannot disable your own account",
        )
    row = await _load_admin(session, admin_id)
    if row.status != AdminStatus.ACTIVE:
        raise AppException(ErrorCode.VALIDATION_ERROR, "admin is not active")
    await _guard_not_last_super(session, row)

    row.status = AdminStatus.DISABLED
    released = await _release_claimed_arbitrations(session, row.id)
    await revoke_all_sessions_for_admin(session, row.id)
    await session.flush()
    await session.refresh(row)

    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=operator.id,
        action="admin.user.disable",
        target_type="admin_user",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"released_arbitrations": released},
    )
    await _notify_target_admin(
        session,
        row.id,
        "您的管理员账号已被禁用",
        "如需恢复请与超级管理员联系",
    )
    if released:
        await _notify_release(session, released, row.id)
    return AdminUserOut.model_validate(row)


async def admin_enable(
    session: AsyncSession,
    operator: AdminUser,
    admin_id: int,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AdminUserOut:
    if admin_id == operator.id:
        raise AppException(
            ErrorCode.ADMIN_CANNOT_OPERATE_SELF,
            "cannot enable your own account",
        )
    row = await _load_admin(session, admin_id)
    if row.status != AdminStatus.DISABLED:
        raise AppException(ErrorCode.VALIDATION_ERROR, "admin is not disabled")

    row.status = AdminStatus.ACTIVE
    await session.flush()
    await session.refresh(row)

    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=operator.id,
        action="admin.user.enable",
        target_type="admin_user",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    await _notify_target_admin(session, row.id, "您的管理员账号已启用", "您现在可以正常登录")
    return AdminUserOut.model_validate(row)


async def admin_reset_password(
    session: AsyncSession,
    operator: AdminUser,
    admin_id: int,
    new_password: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AdminUserOut:
    if admin_id == operator.id:
        raise AppException(
            ErrorCode.ADMIN_CANNOT_OPERATE_SELF,
            "reset your own password through change-password instead",
        )
    row = await _load_admin(session, admin_id)

    row.password_hash = hash_password(new_password)
    row.password_changed_at = _now()
    await revoke_all_sessions_for_admin(session, row.id)
    await session.flush()
    await session.refresh(row)

    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=operator.id,
        action="admin.user.reset_password",
        target_type="admin_user",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    await _notify_target_admin(
        session,
        row.id,
        "您的管理员密码已被重置",
        "请使用新密码重新登录",
    )
    return AdminUserOut.model_validate(row)


__all__ = [
    "admin_create",
    "admin_disable",
    "admin_enable",
    "admin_get",
    "admin_list",
    "admin_reset_password",
    "admin_update",
]
