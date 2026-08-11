"""User-facing (consumer) API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.user import (
    addresses,
    aftersales,
    auth,
    cart,
    discovery,
    me,
    merchant_applications,
    notifications,
    orders,
    payments,
    review_reports,
    reviews,
    uploads,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["user.auth"])
router.include_router(me.router, prefix="/me", tags=["user.me"])
router.include_router(
    merchant_applications.router,
    prefix="/merchant-applications",
    tags=["user.merchant-applications"],
)
router.include_router(addresses.router, prefix="/addresses", tags=["user.addresses"])
router.include_router(cart.router, prefix="/cart", tags=["user.cart"])
router.include_router(orders.router, prefix="/orders", tags=["user.orders"])
router.include_router(payments.router, prefix="", tags=["user.payments"])
router.include_router(aftersales.router, prefix="", tags=["user.aftersales"])
router.include_router(uploads.router, prefix="/uploads", tags=["user.uploads"])
router.include_router(discovery.router, prefix="/engagement", tags=["user.engagement"])
router.include_router(reviews.router, prefix="", tags=["user.reviews"])
router.include_router(review_reports.router, prefix="", tags=["user.review-reports"])
router.include_router(notifications.router, prefix="/notifications", tags=["user.notifications"])

__all__ = ["router"]
