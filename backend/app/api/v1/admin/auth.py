"""Admin-domain auth endpoints (contract §5.3)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_client_ip,
    get_current_admin,
    get_user_agent,
)
from app.core.database import get_db
from app.core.errors import envelope
from app.models.admin_user import AdminUser
from app.models.refresh_token import SubjectType
from app.schemas.admin import AdminChangePasswordIn, AdminLoginIn
from app.schemas.auth import LogoutIn, RefreshIn
from app.services import auth_service

router = APIRouter()


@router.post("/login", summary="Admin log in")
async def login(
    payload: AdminLoginIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, tokens = await auth_service.login_admin(
        session,
        payload.username,
        payload.password,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=tokens.model_dump())


@router.post("/refresh", summary="Rotate admin refresh token")
async def refresh(
    payload: RefreshIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tokens = await auth_service.refresh_tokens(
        session,
        payload.refresh_token,
        SubjectType.ADMIN,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=tokens.model_dump())


@router.post("/logout", summary="Admin log out")
async def logout(
    payload: LogoutIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, Any]:
    await auth_service.logout(
        session,
        payload.refresh_token,
        SubjectType.ADMIN,
        admin.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=None)


@router.post("/change-password", summary="Admin change own password")
async def change_password(
    payload: AdminChangePasswordIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, Any]:
    await auth_service.admin_change_password(
        session,
        admin,
        payload.old_password,
        payload.new_password,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=None)
