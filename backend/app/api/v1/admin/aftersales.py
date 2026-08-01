"""Admin aftersales endpoints — Phase 4 §9."""

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
from app.models.admin_user import AdminUser
from app.schemas.aftersales import (
    AftersalesForceRefundIn,
    AftersalesNoteIn,
    AftersalesResolveIn,
)
from app.services import aftersales_service

router = APIRouter()


@router.get("", summary="List all aftersales cases")
async def list_aftersales(
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_READ_ALL)),
    status_: str | None = Query(default=None, alias="status"),
    type_: str | None = Query(default=None, alias="type"),
    shop_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    escalation_reason: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    items, total = await aftersales_service.admin_list(
        session,
        admin,
        status_filter=status_,
        type_filter=type_,
        shop_id=shop_id,
        user_id=user_id,
        escalation_reason=escalation_reason,
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


@router.get("/stats/overview", summary="Aftersales work-station overview")
async def stats_overview(
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_READ_ALL)),
) -> dict[str, Any]:
    result = await aftersales_service.admin_stats_overview(session, admin)
    return envelope(data=result.model_dump(mode="json"))


@router.get("/{aftersales_id}", summary="Aftersales detail (admin)")
async def get_aftersales(
    aftersales_id: int,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_READ_ALL)),
) -> dict[str, Any]:
    detail = await aftersales_service.admin_get_detail(session, admin, aftersales_id)
    return envelope(data=detail.model_dump(mode="json"))


@router.post("/{aftersales_id}/release", summary="Release a claimed case back to the pool")
async def release_aftersales(
    aftersales_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_ARBITRATE)),
) -> dict[str, Any]:
    detail = await aftersales_service.admin_release(
        session,
        admin,
        aftersales_id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=detail.model_dump(mode="json"))


@router.post("/{aftersales_id}/take-over", summary="Claim arbitration")
async def take_over(
    aftersales_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_ARBITRATE)),
) -> dict[str, Any]:
    detail = await aftersales_service.admin_take_over(
        session,
        admin,
        aftersales_id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=detail.model_dump(mode="json"))


@router.post("/{aftersales_id}/resolve", summary="Arbitration verdict")
async def resolve(
    aftersales_id: int,
    payload: AftersalesResolveIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_ARBITRATE)),
) -> dict[str, Any]:
    detail = await aftersales_service.admin_resolve(
        session,
        admin,
        aftersales_id,
        payload,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=detail.model_dump(mode="json"))


@router.post("/{aftersales_id}/force-refund", summary="Force refund (admin)")
async def force_refund(
    aftersales_id: int,
    payload: AftersalesForceRefundIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_FORCE_REFUND)),
) -> dict[str, Any]:
    detail = await aftersales_service.admin_force_refund(
        session,
        admin,
        aftersales_id,
        payload,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=detail.model_dump(mode="json"))


@router.post("/{aftersales_id}/note", summary="Admin note / internal reply")
async def note_aftersales(
    aftersales_id: int,
    payload: AftersalesNoteIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin_permission(Permission.ADMIN_AFTERSALES_ADD_NOTE)),
) -> dict[str, Any]:
    detail = await aftersales_service.admin_note(
        session,
        admin,
        aftersales_id,
        payload.note,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return envelope(data=detail.model_dump(mode="json"))
