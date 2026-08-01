"""RBAC permission-matrix endpoint — Phase 6.

Exposes the read-only role → permission matrix so the console can render
an audit-friendly overview. Requires ``admin:rbac:read``
(BUSINESS_ADMIN / TECH_ADMIN / SUPER).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_permission
from app.core.database import get_db
from app.core.errors import envelope
from app.core.rbac import Permission, permissions_for_admin
from app.models.admin_user import AdminRole, AdminUser

router = APIRouter()

# Human-readable labels (Chinese) for the permission matrix UI. Keys not
# present here fall back to the raw permission string.
_PERMISSION_LABELS: dict[str, str] = {
    "admin:self:read": "查看个人信息",
    "admin:merchant_application:read": "查看商家入驻申请",
    "admin:merchant_application:review": "审核商家入驻申请",
    "admin:audit_log:read": "查看审计日志",
    "admin:category:manage": "管理商品分类",
    "admin:brand:manage": "管理商品品牌",
    "admin:spu:review": "审核商品",
    "admin:spu:force_offshelf": "强制下架商品",
    "admin:spu:read_all": "查看全部商品",
    "admin:order:read_all": "查看全部订单",
    "admin:order:intervene": "订单干预",
    "admin:order:add_note": "订单备注",
    "admin:task:run": "运行后台任务",
    "admin:aftersales:read_all": "查看全部售后单",
    "admin:aftersales:arbitrate": "仲裁售后单",
    "admin:aftersales:force_refund": "强制退款",
    "admin:aftersales:add_note": "售后备注",
    "admin:aftersales:manage": "管理仲裁派单（释放/重派）",
    "admin:review:moderate": "评价审核",
    "admin:review_report:handle": "评价举报处理",
    "admin:notification:read": "查看系统通知",
    "admin:user:read": "查看管理员账号",
    "admin:user:manage": "管理管理员账号",
    "admin:rbac:read": "查看权限矩阵",
}

_ROLE_LABELS: dict[str, str] = {
    "SUPER_ADMIN": "超级管理员",
    "BUSINESS_ADMIN": "业务管理员",
    "CUSTOMER_SERVICE_ADMIN": "客服主管",
    "CUSTOMER_SERVICE_LEAD": "客服组长",
    "CUSTOMER_SERVICE_AGENT": "普通客服",
    "TECH_ADMIN": "技术管理员",
}


@router.get("", summary="RBAC permission matrix")
async def get_matrix(
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_admin_permission(Permission.ADMIN_RBAC_READ)),
) -> dict[str, Any]:
    roles: dict[str, Any] = {}
    for role in AdminRole:
        perms = sorted(p.value for p in permissions_for_admin(role))
        roles[role.value] = {
            "label": _ROLE_LABELS.get(role.value, role.value),
            "permissions": perms,
        }
    permissions = [
        {
            "key": p.value,
            "label": _PERMISSION_LABELS.get(p.value, p.value),
        }
        for p in Permission
    ]
    return envelope(data={"roles": roles, "permissions": permissions})
