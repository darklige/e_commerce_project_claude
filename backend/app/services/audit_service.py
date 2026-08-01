"""Audit-log writing service.

Phase 1 is *fire-and-forget*: we insert best-effort and swallow any
DB error rather than letting audit failures break the parent request.
Query UIs are deferred to later phases.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditActorType, AuditLog
from app.schemas.admin import AuditLogOut

logger = logging.getLogger(__name__)


async def write_audit(
    session: AsyncSession,
    *,
    actor_type: AuditActorType,
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Insert an ``AuditLog`` row.

    Safe to call inside a service function — any failure is logged
    but never re-raised.
    """
    try:
        row = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip=ip,
            user_agent=user_agent,
            extra=extra,
        )
        session.add(row)
        await session.flush()
    except Exception as exc:
        logger.warning("audit_log write failed: action=%s err=%s", action, exc)


async def list_audit_logs(
    session: AsyncSession,
    *,
    actor_type: AuditActorType | None = None,
    actor_id: int | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[AuditLogOut], int]:
    """Paginated, filterable audit-log query for the console."""
    where: list[object] = []
    if actor_type is not None:
        where.append(AuditLog.actor_type == actor_type)
    if actor_id is not None:
        where.append(AuditLog.actor_id == actor_id)
    if action:
        where.append(AuditLog.action == action)
    if target_type:
        where.append(AuditLog.target_type == target_type)
    if target_id is not None:
        where.append(AuditLog.target_id == target_id)

    total_stmt = select(func.count(AuditLog.id))
    stmt = select(AuditLog)
    if where:
        total_stmt = total_stmt.where(and_(*where))
        stmt = stmt.where(and_(*where))
    total = int((await session.execute(total_stmt)).scalar_one())
    stmt = (
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [AuditLogOut.model_validate(r) for r in rows], total


__all__ = ["list_audit_logs", "write_audit"]
