"""Admin-facing (platform ops) API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import (
    aftersales,
    audit_logs,
    auth,
    brands,
    categories,
    me,
    merchant_applications,
    notifications,
    orders,
    rbac,
    review_reports,
    reviews,
    spus,
    tasks,
    users,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["admin.auth"])
router.include_router(me.router, prefix="/me", tags=["admin.me"])
# Phase 6 — admin account management / RBAC matrix / audit log console.
router.include_router(users.router, prefix="/users", tags=["admin.users"])
router.include_router(rbac.router, prefix="/rbac", tags=["admin.rbac"])
router.include_router(audit_logs.router, prefix="/audit-logs", tags=["admin.audit-logs"])
router.include_router(
    merchant_applications.router,
    prefix="/merchant-applications",
    tags=["admin.merchant-applications"],
)
router.include_router(categories.router, prefix="/categories", tags=["admin.categories"])
router.include_router(brands.router, prefix="/brands", tags=["admin.brands"])
router.include_router(spus.router, prefix="/spus", tags=["admin.spus"])
router.include_router(orders.router, prefix="/orders", tags=["admin.orders"])
router.include_router(tasks.router, prefix="/tasks", tags=["admin.tasks"])
router.include_router(aftersales.router, prefix="/aftersales", tags=["admin.aftersales"])
# Phase 5 — reviews, review reports, notifications.
router.include_router(reviews.router, prefix="/reviews", tags=["admin.reviews"])
router.include_router(
    review_reports.router, prefix="/review-reports", tags=["admin.review-reports"]
)
router.include_router(notifications.router, prefix="/notifications", tags=["admin.notifications"])

__all__ = ["router"]
