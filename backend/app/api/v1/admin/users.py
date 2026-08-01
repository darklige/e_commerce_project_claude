"""Admin account-management endpoints — Phase 6.

Routes under :mod:`users` manage platform admin accounts. Mutating
operations require ``admin:user:manage`` (SUPER only); read/list requires
``admin:user:read`` (SUPER + TECH_ADMIN). Self-service password change is
available to every authenticated admin.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_client_ip,
    get_user_agent,
    require_admin_permission,
)
from app.core.database import get_db
from app.core.errors import envelope
from app.core.rbac import Permission
from app.models.admin_user import AdminRole, AdminStatus, AdminUser
from app.schemas.admin import (
    AdminCreateIn,
    AdminResetPasswordIn,
    AdminUpdateIn,
)
from app.services import admin_user_service

router = APIRouter()


@router.get("", summary="List admin accounts")
async def list_admins(
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_admin_permission(Permission.ADMIN_USER_READ)),
    role: AdminRole | None = Query(default=None),
    status_: AdminStatus | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    items, total = await admin_user_service.admin_list(
        session,
        role=role,
        status_=status_,
        keyword=keyword,
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


@router.post("", summary="Create an admin account")
async def create_admin(
    payload: AdminCreateIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_USER_MANAGE)),
) -> dict[str, Any]:
    row = await admin_user_service.admin_create(
        session,
        admin,
        payload,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=row.model_dump(mode="json"))


@router.get("/{admin_id}", summary="Get one admin account")
async def get_admin(
    admin_id: int,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_admin_permission(Permission.ADMIN_USER_READ)),
) -> dict[str, Any]:
    row = await admin_user_service.admin_get(session, admin_id)
    return envelope(data=row.model_dump(mode="json"))


@router.patch("/{admin_id}", summary="Update display_name / role")
async def update_admin(
    admin_id: int,
    payload: AdminUpdateIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_USER_MANAGE)),
) -> dict[str, Any]:
    row = await admin_user_service.admin_update(
        session,
        admin,
        admin_id,
        payload,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=row.model_dump(mode="json"))


@router.post("/{admin_id}/disable", summary="Disable an admin account")
async def disable_admin(
    admin_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_USER_MANAGE)),
) -> dict[str, Any]:
    row = await admin_user_service.admin_disable(
        session,
        admin,
        admin_id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=row.model_dump(mode="json"))


@router.post("/{admin_id}/enable", summary="Enable an admin account")
async def enable_admin(
    admin_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_USER_MANAGE)),
) -> dict[str, Any]:
    row = await admin_user_service.admin_enable(
        session,
        admin,
        admin_id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=row.model_dump(mode="json"))


@router.post("/{admin_id}/reset-password", summary="Reset another admin's password")
async def reset_password(
    admin_id: int,
    payload: AdminResetPasswordIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_USER_MANAGE)),
) -> dict[str, Any]:
    row = await admin_user_service.admin_reset_password(
        session,
        admin,
        admin_id,
        payload.new_password,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=row.model_dump(mode="json"))
