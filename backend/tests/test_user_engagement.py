from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import bearer, login_user_get_tokens


async def _headers(client: AsyncClient, user: User) -> dict[str, str]:
    tokens = await login_user_get_tokens(client, user.phone or "", "Test1234")
    return bearer(tokens["access_token"])


@pytest.mark.asyncio
async def test_user_engagement_demo_flow(
    client: AsyncClient,
    seed_user: User,
) -> None:
    headers = await _headers(client, seed_user)

    overview = (await client.get("/api/v1/user/engagement/overview", headers=headers)).json()
    assert overview["code"] == 0
    assert overview["data"]["active_campaign"]["id"] == "campaign-818-digital"

    coupons = (await client.get("/api/v1/user/engagement/coupons", headers=headers)).json()
    assert coupons["code"] == 0
    first_coupon = coupons["data"][0]
    assert first_coupon["claimed"] is False

    claim = (
        await client.post(
            f"/api/v1/user/engagement/coupons/{first_coupon['id']}/claim",
            headers=headers,
        )
    ).json()
    assert claim["data"]["claimed"] is True

    favorites = (await client.get("/api/v1/user/engagement/favorites", headers=headers)).json()
    assert favorites["code"] == 0

    favorite_spu_id = favorites["data"][0]["spu"]["id"] if favorites["data"] else 1
    toggle = (
        await client.post(
            f"/api/v1/user/engagement/favorites/{favorite_spu_id}/toggle",
            headers=headers,
        )
    ).json()
    assert toggle["code"] == 0

    follows = (await client.get("/api/v1/user/engagement/follows", headers=headers)).json()
    shop_id = follows["data"][0]["id"] if follows["data"] else 1
    follow_toggle = (
        await client.post(f"/api/v1/user/engagement/follows/{shop_id}/toggle", headers=headers)
    ).json()
    assert follow_toggle["code"] == 0

    footprints = (await client.get("/api/v1/user/engagement/footprints", headers=headers)).json()
    spu_id = footprints["data"][0]["spu"]["id"] if footprints["data"] else 1
    record = (
        await client.post(f"/api/v1/user/engagement/footprints/{spu_id}", headers=headers)
    ).json()
    assert record["data"]["active"] is True
