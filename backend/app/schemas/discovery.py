"""User discovery / engagement demo schemas for Android experience."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import SPUListItemOut, ShopBriefOut


class CouponOut(BaseModel):
    id: str
    title: str
    subtitle: str
    discount_label: str
    threshold_label: str
    claimed: bool = False
    expires_at: datetime
    scope_label: str


class FollowedShopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    logo_url: str | None = None
    announcement: str | None = None
    sales_count: int = 0
    rating_avg: float = 5.0
    rating_count: int = 0
    followed: bool = True


class FavoriteSpuOut(BaseModel):
    spu: SPUListItemOut
    collected_at: datetime


class FootprintOut(BaseModel):
    spu: SPUListItemOut
    viewed_at: datetime


class CampaignSectionOut(BaseModel):
    title: str
    subtitle: str
    items: list[SPUListItemOut] = Field(default_factory=list)


class CampaignOut(BaseModel):
    id: str
    title: str
    subtitle: str
    banner_text: str
    start_at: datetime
    end_at: datetime
    full_reduction_rules: list[str] = Field(default_factory=list)
    coupons: list[CouponOut] = Field(default_factory=list)
    featured_sections: list[CampaignSectionOut] = Field(default_factory=list)
    featured_shop: ShopBriefOut | None = None


class EngagementOverviewOut(BaseModel):
    coupon_count: int
    favorite_count: int
    follow_count: int
    footprint_count: int
    headline: str
    active_campaign: CampaignOut | None = None


class ToggleResultOut(BaseModel):
    active: bool
    total: int
