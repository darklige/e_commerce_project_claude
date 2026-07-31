"""Admin audit-log query endpoints — Phase 6.

Read-only; requires ``admin:audit_log:read`` (TECH_ADMIN / SUPER).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_permission
from app.core.database import get_db
from app.core.errors import envelope
from app.core.rbac import Permission
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditActorType
from app.services import audit_service

router = APIRouter()


@router.get("", summary="List audit logs")
async def list_logs(
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AUDIT_LOG_READ)),
    actor_type: AuditActorType | None = Query(default=None),
    actor_id: int | None = Query(default=None),
    action: str | None = Query(default=None, max_length=100),
    target_type: str | None = Query(default=None, max_length=100),
    target_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    items, total = await audit_service.list_audit_logs(
        session,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        page=page,
        size=size,
    )
    return envelope(
        data={
            "items": [i.model_dump(mode="json") for i in items],
            "total": total,
            "page": page,
            "size": size,
        }
    )
