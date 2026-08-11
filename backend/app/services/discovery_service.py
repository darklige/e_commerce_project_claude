"""Demo-friendly user engagement service for Android features."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Shop
from app.models.product import SPU, SPUStatus
from app.models.user import User
from app.schemas.product import SPUListItemOut, ShopBriefOut
from app.schemas.discovery import (
    CampaignOut,
    CampaignSectionOut,
    CouponOut,
    EngagementOverviewOut,
    FavoriteSpuOut,
    FollowedShopOut,
    FootprintOut,
    ToggleResultOut,
)

_user_coupon_claims: dict[int, set[str]] = {}
_user_favorites: dict[int, list[int]] = {}
_user_follows: dict[int, list[int]] = {}
_user_footprints: dict[int, list[tuple[int, datetime]]] = {}


def _coupon_defs(now: datetime) -> list[CouponOut]:
    return [
        CouponOut(
            id="newcomer-40",
            title="新人立减券",
            subtitle="下单就能用，适合首单体验",
            discount_label="满199减40",
            threshold_label="订单实付满199元",
            expires_at=now + timedelta(days=7),
            scope_label="全场通用",
        ),
        CouponOut(
            id="digital-120",
            title="数码会场券",
            subtitle="活动会场专属，叠加满减说明展示",
            discount_label="满999减120",
            threshold_label="仅限 818 数码会场",
            expires_at=datetime(2026, 8, 18, 23, 59, tzinfo=UTC),
            scope_label="活动商品",
        ),
        CouponOut(
            id="shipping-free",
            title="包邮券",
            subtitle="小件凑单更划算",
            discount_label="运费减免",
            threshold_label="满69元可用",
            expires_at=now + timedelta(days=5),
            scope_label="自营与演示店",
        ),
    ]


async def _load_spus(session: AsyncSession, ids: Sequence[int]) -> list[SPU]:
    if not ids:
        return []
    rows = (
        await session.execute(
            select(SPU)
            .where(SPU.id.in_(list(ids)))
            .order_by(SPU.updated_at.desc(), SPU.id.desc())
        )
    ).scalars().all()
    by_id = {row.id: row for row in rows}
    return [by_id[i] for i in ids if i in by_id]


async def _load_shops(session: AsyncSession, ids: Sequence[int]) -> list[Shop]:
    if not ids:
        return []
    rows = (await session.execute(select(Shop).where(Shop.id.in_(list(ids))))).scalars().all()
    by_id = {row.id: row for row in rows}
    return [by_id[i] for i in ids if i in by_id]


async def _default_spus(session: AsyncSession, limit: int = 6) -> list[SPU]:
    stmt = (
        select(SPU)
        .where(SPU.status.in_([SPUStatus.APPROVED, SPUStatus.OFF_SHELF]))
        .order_by(SPU.sales_count.desc(), SPU.updated_at.desc(), SPU.id.desc())
        .limit(limit)
    )
    return (await session.execute(stmt)).scalars().all()


async def _default_shops(session: AsyncSession, limit: int = 3) -> list[Shop]:
    stmt = select(Shop).order_by(Shop.sales_count.desc(), Shop.id.desc()).limit(limit)
    return (await session.execute(stmt)).scalars().all()


async def _ensure_user_state(session: AsyncSession, user: User) -> None:
    if user.id not in _user_favorites:
        base_spus = await _default_spus(session, limit=4)
        _user_favorites[user.id] = [spu.id for spu in base_spus[:2]]
    if user.id not in _user_follows:
        base_shops = await _default_shops(session, limit=2)
        _user_follows[user.id] = [shop.id for shop in base_shops[:1]]
    if user.id not in _user_footprints:
        base_spus = await _default_spus(session, limit=4)
        now = datetime.now(UTC)
        _user_footprints[user.id] = [
            (spu.id, now - timedelta(hours=index * 6))
            for index, spu in enumerate(base_spus[:3])
        ]
    _user_coupon_claims.setdefault(user.id, set())


async def list_coupons(session: AsyncSession, user: User) -> list[CouponOut]:
    await _ensure_user_state(session, user)
    claimed = _user_coupon_claims[user.id]
    now = datetime.now(UTC)
    return [item.model_copy(update={"claimed": item.id in claimed}) for item in _coupon_defs(now)]


async def claim_coupon(session: AsyncSession, user: User, coupon_id: str) -> CouponOut:
    await _ensure_user_state(session, user)
    now = datetime.now(UTC)
    for item in _coupon_defs(now):
        if item.id == coupon_id:
            _user_coupon_claims[user.id].add(coupon_id)
            return item.model_copy(update={"claimed": True})
    raise ValueError("coupon not found")


async def list_favorites(session: AsyncSession, user: User) -> list[FavoriteSpuOut]:
    await _ensure_user_state(session, user)
    spus = await _load_spus(session, _user_favorites[user.id])
    now = datetime.now(UTC)
    return [
        FavoriteSpuOut(
            spu=SPUListItemOut.model_validate(spu),
            collected_at=now - timedelta(days=index),
        )
        for index, spu in enumerate(spus)
    ]


async def toggle_favorite(session: AsyncSession, user: User, spu_id: int) -> ToggleResultOut:
    await _ensure_user_state(session, user)
    current = _user_favorites[user.id]
    if spu_id in current:
        current.remove(spu_id)
        return ToggleResultOut(active=False, total=len(current))
    current.insert(0, spu_id)
    return ToggleResultOut(active=True, total=len(current))


async def list_follows(session: AsyncSession, user: User) -> list[FollowedShopOut]:
    await _ensure_user_state(session, user)
    shops = await _load_shops(session, _user_follows[user.id])
    return [FollowedShopOut.model_validate(shop) for shop in shops]


async def toggle_follow(session: AsyncSession, user: User, shop_id: int) -> ToggleResultOut:
    await _ensure_user_state(session, user)
    current = _user_follows[user.id]
    if shop_id in current:
        current.remove(shop_id)
        return ToggleResultOut(active=False, total=len(current))
    current.insert(0, shop_id)
    return ToggleResultOut(active=True, total=len(current))


async def list_footprints(session: AsyncSession, user: User) -> list[FootprintOut]:
    await _ensure_user_state(session, user)
    logs = _user_footprints[user.id]
    spus = await _load_spus(session, [spu_id for spu_id, _ in logs])
    by_id = {spu.id: spu for spu in spus}
    return [
        FootprintOut(
            spu=SPUListItemOut.model_validate(by_id[spu_id]),
            viewed_at=viewed_at,
        )
        for spu_id, viewed_at in logs
        if spu_id in by_id
    ]


async def record_footprint(session: AsyncSession, user: User, spu_id: int) -> ToggleResultOut:
    await _ensure_user_state(session, user)
    logs = [(sid, ts) for sid, ts in _user_footprints[user.id] if sid != spu_id]
    logs.insert(0, (spu_id, datetime.now(UTC)))
    _user_footprints[user.id] = logs[:20]
    return ToggleResultOut(active=True, total=len(_user_footprints[user.id]))


async def get_active_campaign(session: AsyncSession, user: User) -> CampaignOut:
    await _ensure_user_state(session, user)
    featured_spus = await _default_spus(session, limit=6)
    featured_shop_list = await _default_shops(session, limit=1)
    coupons = await list_coupons(session, user)
    return CampaignOut(
        id="campaign-818-digital",
        title="818 数码家电会场",
        subtitle="今天是 2026 年 8 月 10 日，活动会场已开启模拟预热",
        banner_text="跨店每满300减40，上不封顶，今晚 20:00 限时秒杀",
        start_at=datetime(2026, 8, 10, 0, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 18, 23, 59, tzinfo=UTC),
        full_reduction_rules=[
            "每满300减40，可跨店累计",
            "大家电单笔满2000再减200",
            "活动券可与店铺关注券叠加展示",
        ],
        coupons=coupons,
        featured_sections=[
            CampaignSectionOut(
                title="爆款直降",
                subtitle="演示商品用于安卓联调与体验",
                items=[SPUListItemOut.model_validate(spu) for spu in featured_spus[:3]],
            ),
            CampaignSectionOut(
                title="店铺优选",
                subtitle="适合体验收藏、足迹与凑单",
                items=[SPUListItemOut.model_validate(spu) for spu in featured_spus[3:6]],
            ),
        ],
        featured_shop=ShopBriefOut.model_validate(featured_shop_list[0]) if featured_shop_list else None,
    )


async def get_overview(session: AsyncSession, user: User) -> EngagementOverviewOut:
    await _ensure_user_state(session, user)
    coupons = await list_coupons(session, user)
    return EngagementOverviewOut(
        coupon_count=sum(1 for item in coupons if item.claimed),
        favorite_count=len(_user_favorites[user.id]),
        follow_count=len(_user_follows[user.id]),
        footprint_count=len(_user_footprints[user.id]),
        headline="已为你准备活动券、收藏、关注和浏览足迹",
        active_campaign=await get_active_campaign(session, user),
    )
