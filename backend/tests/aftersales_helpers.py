"""Shared helpers for Phase 4 aftersales test suites.

Builds a fully-realized SKU + shipped/paid order via the public HTTP API so
tests focus on aftersales behaviour instead of order-lifecycle plumbing.
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import update

from app.core import database as core_db
from app.models.merchant import MerchantAccount, Shop
from app.models.order import Order, OrderStatus
from app.models.user import User
from tests.conftest import (
    bearer,
    login_admin_get_tokens,
    login_merchant_get_tokens,
    login_user_get_tokens,
)


async def headers_user(client: AsyncClient, user: User) -> dict[str, str]:
    tokens = await login_user_get_tokens(client, user.phone or "", "Test1234")
    return bearer(tokens["access_token"])


async def headers_merchant(
    client: AsyncClient, seed: tuple[MerchantAccount, Shop]
) -> dict[str, str]:
    account, _ = seed
    tokens = await login_merchant_get_tokens(client, account.login_name, "Merch1234")
    return bearer(tokens["access_token"])


async def headers_admin(client: AsyncClient, username: str = "super") -> dict[str, str]:
    pwd_map = {
        "super": "super_pwd_change_me",
        "cs01": "cs_pwd_change_me",
        "cslead01": "cslead_pwd_change_me",
        "csagent01": "csagent_pwd_change_me",
        "tech01": "tech_pwd_change_me",
    }
    tokens = await login_admin_get_tokens(client, username, pwd_map[username])
    return bearer(tokens["access_token"])


async def build_paid_order(
    client: AsyncClient,
    user: User,
    admins: dict[str, Any],
    merchant_seed: tuple[MerchantAccount, Shop],
    catalog: dict[str, Any],
    *,
    stock: int = 5,
    quantity: int = 2,
    price_cents: int = 20000,
    ship: bool = False,
    complete: bool = False,
) -> dict[str, Any]:
    """Return dict with keys: order (dict), sku (dict), headers dict."""
    _ = admins
    u_headers = await headers_user(client, user)
    m_headers = await headers_merchant(client, merchant_seed)
    a_headers = await headers_admin(client)

    spu = (
        await client.post(
            "/api/v1/merchant/spus",
            headers=m_headers,
            json={
                "category_id": catalog["leaf"].id,
                "brand_id": catalog["brand"].id,
                "title": f"售后测试-{uuid.uuid4().hex[:6]}",
                "main_image": "spu/as.jpg",
                "spec_axes": ["color"],
            },
        )
    ).json()["data"]
    sku = (
        await client.post(
            f"/api/v1/merchant/spus/{spu['id']}/skus",
            headers=m_headers,
            json={
                "sku_code": f"AS-{uuid.uuid4().hex[:6]}",
                "specs": {"color": "红"},
                "price_cents": price_cents,
                "stock": stock,
            },
        )
    ).json()["data"]
    await client.post(f"/api/v1/merchant/spus/{spu['id']}/submit-review", headers=m_headers)
    await client.post(f"/api/v1/admin/spus/{spu['id']}/approve", headers=a_headers, json={})

    cart_item = (
        await client.post(
            "/api/v1/user/cart/items",
            headers=u_headers,
            json={"sku_id": sku["id"], "quantity": quantity},
        )
    ).json()["data"]
    addr = (
        await client.post(
            "/api/v1/user/addresses",
            headers=u_headers,
            json={
                "receiver_name": "张三",
                "receiver_phone": "13800000001",
                "province": "浙江省",
                "city": "杭州市",
                "district": "西湖区",
                "detail": "文三路 100 号",
                "is_default": True,
            },
        )
    ).json()["data"]
    idem = str(uuid.uuid4())
    order = (
        await client.post(
            "/api/v1/user/orders",
            headers={**u_headers, "Idempotency-Key": idem},
            json={"cart_item_ids": [cart_item["id"]], "address_id": addr["id"]},
        )
    ).json()["data"]["orders"][0]

    # Pay
    pay = await client.post(
        f"/api/v1/user/orders/{order['id']}/pay",
        headers={**u_headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"channel": "mock_alipay"},
    )
    session_id = pay.json()["data"]["session_id"]
    await client.post(f"/api/v1/user/payment-sessions/{session_id}/mock-succeed", headers=u_headers)

    if ship or complete:
        await client.post(
            f"/api/v1/merchant/orders/{order['id']}/ship",
            headers=m_headers,
            json={"carrier": "SF", "tracking_no": f"SF{uuid.uuid4().hex[:10]}"},
        )
    if complete:
        await client.post(
            f"/api/v1/user/orders/{order['id']}/confirm-receipt",
            headers=u_headers,
        )

    return {
        "order": order,
        "sku": sku,
        "u_headers": u_headers,
        "m_headers": m_headers,
        "a_headers": a_headers,
    }


async def get_order_detail(
    client: AsyncClient, order_id: int, u_headers: dict[str, str]
) -> dict[str, Any]:
    resp = await client.get(f"/api/v1/user/orders/{order_id}", headers=u_headers)
    return resp.json()["data"]


async def set_order_status(order_id: int, new_status: OrderStatus) -> None:
    async with core_db.async_session_factory() as s:
        await s.execute(update(Order).where(Order.id == order_id).values(status=new_status))
        await s.commit()
