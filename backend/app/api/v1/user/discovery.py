"""User engagement / marketing demo endpoints for Android."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppException, ErrorCode, envelope
from app.models.user import User
from app.services import discovery_service

router = APIRouter()


@router.get("/overview", summary="User engagement overview")
async def get_overview(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    row = await discovery_service.get_overview(session, user)
    return envelope(data=row.model_dump(mode="json"))


@router.get("/campaigns/active", summary="Get the active simulated campaign hall")
async def get_active_campaign(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    row = await discovery_service.get_active_campaign(session, user)
    return envelope(data=row.model_dump(mode="json"))


@router.get("/coupons", summary="List my demo coupons")
async def list_coupons(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    items = await discovery_service.list_coupons(session, user)
    return envelope(data=[item.model_dump(mode="json") for item in items])


@router.post("/coupons/{coupon_id}/claim", summary="Claim one simulated coupon")
async def claim_coupon(
    coupon_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        item = await discovery_service.claim_coupon(session, user, coupon_id)
    except ValueError as exc:
        raise AppException(ErrorCode.RESOURCE_NOT_FOUND, "coupon not found") from exc
    return envelope(data=item.model_dump(mode="json"))


@router.get("/favorites", summary="List my favorite products")
async def list_favorites(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    items = await discovery_service.list_favorites(session, user)
    return envelope(data=[item.model_dump(mode="json") for item in items])


@router.post("/favorites/{spu_id}/toggle", summary="Toggle favorite state for a product")
async def toggle_favorite(
    spu_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    result = await discovery_service.toggle_favorite(session, user, spu_id)
    return envelope(data=result.model_dump(mode="json"))


@router.get("/follows", summary="List followed shops")
async def list_follows(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    items = await discovery_service.list_follows(session, user)
    return envelope(data=[item.model_dump(mode="json") for item in items])


@router.post("/follows/{shop_id}/toggle", summary="Toggle follow state for a shop")
async def toggle_follow(
    shop_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    result = await discovery_service.toggle_follow(session, user, shop_id)
    return envelope(data=result.model_dump(mode="json"))


@router.get("/footprints", summary="List my recent footprints")
async def list_footprints(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    items = await discovery_service.list_footprints(session, user)
    return envelope(data=[item.model_dump(mode="json") for item in items])


@router.post("/footprints/{spu_id}", summary="Record one product view as a footprint")
async def record_footprint(
    spu_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    result = await discovery_service.record_footprint(session, user, spu_id)
    return envelope(data=result.model_dump(mode="json"))
