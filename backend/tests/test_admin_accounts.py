"""Phase 6 — admin account management, RBAC matrix, audit-log console.

Covers:
* CRUD on admin accounts (create/list/get/update/disable/enable/reset-password).
* Guard rails: cannot operate self, last-super-admin protection,
  duplicate username, password strength.
* Cascade on disable / role-demotion: claimed arbitration cases released,
  refresh tokens revoked.
* CS_AGENT data scope over the aftersales queue + CS_LEAD release.
* Read-only guards (TECH_ADMIN may read, not manage; CS roles may not
  read the account list).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from app.core import database as core_db
from app.core.errors import AppException, ErrorCode
from app.core.rbac import Permission, permissions_for_admin
from app.models.admin_user import AdminRole, AdminUser
from app.models.user import User
from app.schemas.admin import AdminUpdateIn
from app.services import admin_user_service
from tests.aftersales_helpers import build_paid_order, headers_admin

_SUPER_PWD = "super_pwd_change_me"
_AGENT_PWD = "csagent_pwd_change_me"
_LEAD_PWD = "cslead_pwd_change_me"


async def _create_admin(
    client: AsyncClient,
    super_headers: dict[str, str],
    *,
    username: str,
    role: str,
    password: str = "Passw0rd!",  # noqa: S107  test-only fixture default
    display_name: str = "新管理员",
) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/admin/users",
        headers=super_headers,
        json={
            "username": username,
            "display_name": display_name,
            "role": role,
            "password": password,
        },
    )
    assert resp.json()["code"] == 0, resp.text
    return resp.json()["data"]


async def _create_arbitrating_case(
    client: AsyncClient,
    seed_user: User,
    seed_admins: dict[str, AdminUser],
    seed_merchant_account: tuple[Any, Any],
    seed_catalog: dict[str, Any],
) -> dict[str, Any]:
    """Create a PAID order → aftersales → merchant reject → user appeal.

    Returns the arbitrating-case dict.
    """
    ctx = await build_paid_order(
        client,
        seed_user,
        seed_admins,
        seed_merchant_account,
        seed_catalog,
        stock=5,
        quantity=1,
        price_cents=10000,
    )
    detail = (
        await client.get(f"/api/v1/user/orders/{ctx['order']['id']}", headers=ctx["u_headers"])
    ).json()["data"]
    oi = detail["items"][0]
    case = (
        await client.post(
            f"/api/v1/user/orders/{ctx['order']['id']}/aftersales",
            headers={**ctx["u_headers"], "Idempotency-Key": str(uuid.uuid4())},
            json={
                "type": "refund_only",
                "reason_category": "quality_issue",
                "reason_note": "商品质量问题需要仲裁流程处理",
                "items": [{"order_item_id": oi["id"], "quantity": 1}],
                "refund_amount_cents": oi["subtotal_cents"],
            },
        )
    ).json()["data"]
    await client.post(
        f"/api/v1/merchant/aftersales/{case['id']}/reject",
        headers=ctx["m_headers"],
        json={"review_note": "驳回，理由充分足够长"},
    )
    await client.post(
        f"/api/v1/user/aftersales/{case['id']}/appeal",
        headers=ctx["u_headers"],
        json={
            "reason": "用户申诉理由文本占位符号需要至少二十个中文字符哦哦哦",
            "evidence_image_keys": [],
        },
    )
    return case


# ---------------------------------------------------------------------------
# CRUD + guard rails
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_list_get_update_admin(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    a_headers = await headers_admin(client, "super")

    created = await _create_admin(client, a_headers, username="newbie01", role="TECH_ADMIN")
    assert created["status"] == "active"
    assert created["role"] == "TECH_ADMIN"
    assert "password" not in created

    listed = (await client.get("/api/v1/admin/users", headers=a_headers)).json()["data"]
    assert any(item["username"] == "newbie01" for item in listed["items"])

    got = (await client.get(f"/api/v1/admin/users/{created['id']}", headers=a_headers)).json()[
        "data"
    ]
    assert got["username"] == "newbie01"

    updated = (
        await client.patch(
            f"/api/v1/admin/users/{created['id']}",
            headers=a_headers,
            json={"display_name": "改名了", "role": "CUSTOMER_SERVICE_AGENT"},
        )
    ).json()["data"]
    assert updated["display_name"] == "改名了"
    assert updated["role"] == "CUSTOMER_SERVICE_AGENT"


@pytest.mark.asyncio
async def test_create_duplicate_username_conflict(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    a_headers = await headers_admin(client, "super")
    await _create_admin(client, a_headers, username="dup01", role="TECH_ADMIN")
    resp = await client.post(
        "/api/v1/admin/users",
        headers=a_headers,
        json={
            "username": "dup01",
            "display_name": "撞名",
            "role": "TECH_ADMIN",
            "password": "Passw0rd!",
        },
    )
    assert resp.json()["code"] == 4002  # ADMIN_USERNAME_TAKEN


@pytest.mark.asyncio
async def test_create_weak_password_rejected(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    a_headers = await headers_admin(client, "super")
    resp = await client.post(
        "/api/v1/admin/users",
        headers=a_headers,
        json={
            "username": "weak01",
            "display_name": "弱密码",
            "role": "TECH_ADMIN",
            "password": "123",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cannot_operate_self(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    a_headers = await headers_admin(client, "super")
    super_id = seed_admins["SUPER_ADMIN"].id
    resp = await client.patch(
        f"/api/v1/admin/users/{super_id}",
        headers=a_headers,
        json={"role": "TECH_ADMIN"},
    )
    assert resp.json()["code"] == 4003  # ADMIN_CANNOT_OPERATE_SELF

    resp = await client.post(f"/api/v1/admin/users/{super_id}/disable", headers=a_headers)
    assert resp.json()["code"] == 4003

    resp = await client.post(
        f"/api/v1/admin/users/{super_id}/reset-password",
        headers=a_headers,
        json={"new_password": "Passw0rd!"},
    )
    assert resp.json()["code"] == 4003


@pytest.mark.asyncio
async def test_last_super_admin_cannot_be_demoted_or_disabled(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    a_headers = await headers_admin(client, "super")
    super_id = seed_admins["SUPER_ADMIN"].id

    # Self-operation is blocked with its own code before anything else.
    resp = await client.patch(
        f"/api/v1/admin/users/{super_id}",
        headers=a_headers,
        json={"role": "TECH_ADMIN"},
    )
    assert resp.json()["code"] == 4003

    # Create a second super, then disable it so exactly one active super
    # remains — the guard is defense-in-depth and fires even when a
    # *different* operator targets the last one.
    created = await _create_admin(client, a_headers, username="super2", role="SUPER_ADMIN")
    resp = await client.post(
        f"/api/v1/admin/users/{created['id']}/disable", headers=a_headers
    )
    assert resp.json()["code"] == 0

    fake_operator = AdminUser(id=999999, role=AdminRole.SUPER_ADMIN)
    async with core_db.async_session_factory() as s:
        with pytest.raises(AppException) as ei:
            await admin_user_service.admin_update(
                s, fake_operator, super_id, AdminUpdateIn(role="TECH_ADMIN")
            )
        assert ei.value.code == ErrorCode.ADMIN_LAST_SUPER_ADMIN


@pytest.mark.asyncio
async def test_disable_enable_reset_password_cycle(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    a_headers = await headers_admin(client, "super")
    created = await _create_admin(client, a_headers, username="cycle01", role="TECH_ADMIN")
    aid = created["id"]

    # disable → login with old password now fails (account disabled)
    resp = await client.post(f"/api/v1/admin/users/{aid}/disable", headers=a_headers)
    assert resp.json()["data"]["status"] == "disabled"
    login = await client.post(
        "/api/v1/admin/auth/login", json={"username": "cycle01", "password": "Passw0rd!"}
    )
    assert login.json()["code"] != 0

    # enable
    resp = await client.post(f"/api/v1/admin/users/{aid}/enable", headers=a_headers)
    assert resp.json()["data"]["status"] == "active"

    # reset password → new password works, old is rejected
    resp = await client.post(
        f"/api/v1/admin/users/{aid}/reset-password",
        headers=a_headers,
        json={"new_password": "NewPass9"},
    )
    assert resp.json()["code"] == 0
    login = await client.post(
        "/api/v1/admin/auth/login", json={"username": "cycle01", "password": "NewPass9"}
    )
    assert login.json()["code"] == 0
    login = await client.post(
        "/api/v1/admin/auth/login", json={"username": "cycle01", "password": "Passw0rd!"}
    )
    assert login.json()["code"] != 0


# ---------------------------------------------------------------------------
# RBAC guards
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tech_admin_read_only(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    tech_headers = await headers_admin(client, "tech01")
    listed = (await client.get("/api/v1/admin/users", headers=tech_headers)).json()
    assert listed["code"] == 0

    resp = await client.post(
        "/api/v1/admin/users",
        headers=tech_headers,
        json={
            "username": "nope01",
            "display_name": "无权限",
            "role": "TECH_ADMIN",
            "password": "Passw0rd!",
        },
    )
    assert resp.json()["code"] != 0  # permission denied

    # RBAC matrix readable
    matrix = (await client.get("/api/v1/admin/rbac", headers=tech_headers)).json()
    assert matrix["code"] == 0
    assert "CUSTOMER_SERVICE_AGENT" in matrix["data"]["roles"]


@pytest.mark.asyncio
async def test_cs_agent_cannot_read_account_list(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    agent_headers = await headers_admin(client, "csagent01")
    resp = await client.get("/api/v1/admin/users", headers=agent_headers)
    assert resp.json()["code"] != 0


@pytest.mark.asyncio
async def test_permission_matrix_content() -> None:
    perms = permissions_for_admin(AdminRole.CUSTOMER_SERVICE_AGENT)
    assert Permission.ADMIN_AFTERSALES_ARBITRATE in perms
    assert Permission.ADMIN_AFTERSALES_FORCE_REFUND not in perms
    assert Permission.ADMIN_AFTERSALES_MANAGE not in perms

    lead_perms = permissions_for_admin(AdminRole.CUSTOMER_SERVICE_LEAD)
    assert Permission.ADMIN_AFTERSALES_MANAGE in lead_perms

    super_perms = permissions_for_admin(AdminRole.SUPER_ADMIN)
    assert Permission.ADMIN_USER_MANAGE in super_perms
    assert Permission.ADMIN_RBAC_READ in super_perms


# ---------------------------------------------------------------------------
# Cascade: demote / disable → release arbitration + revoke sessions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_demote_agent_releases_claim_and_revokes_sessions(
    client: AsyncClient,
    seed_user: User,
    seed_admins: dict[str, AdminUser],
    seed_merchant_account: tuple[Any, Any],
    seed_catalog: dict[str, Any],
) -> None:
    case = await _create_arbitrating_case(
        client, seed_user, seed_admins, seed_merchant_account, seed_catalog
    )
    case_id = case["id"]

    # CS_AGENT logs in and claims the case.
    agent_tokens = await login_admin(client, "csagent01", _AGENT_PWD)
    agent_headers = {"Authorization": f"Bearer {agent_tokens['access_token']}"}
    claimed = (
        await client.post(f"/api/v1/admin/aftersales/{case_id}/take-over", headers=agent_headers)
    ).json()["data"]
    assert claimed["arbitrator_admin_id"] == seed_admins["CUSTOMER_SERVICE_AGENT"].id

    # SUPER demotes the agent to a role that cannot arbitrate → case released.
    agent_id = seed_admins["CUSTOMER_SERVICE_AGENT"].id
    super_headers = await headers_admin(client, "super")
    resp = await client.patch(
        f"/api/v1/admin/users/{agent_id}",
        headers=super_headers,
        json={"role": "TECH_ADMIN"},
    )
    assert resp.json()["code"] == 0, resp.text

    detail = (
        await client.get(f"/api/v1/admin/aftersales/{case_id}", headers=super_headers)
    ).json()["data"]
    assert detail["arbitrator_admin_id"] is None

    # The agent's refresh token was revoked.
    refresh = await client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": agent_tokens["refresh_token"]},
    )
    assert refresh.json()["code"] != 0


@pytest.mark.asyncio
async def test_disable_releases_claim(
    client: AsyncClient,
    seed_user: User,
    seed_admins: dict[str, AdminUser],
    seed_merchant_account: tuple[Any, Any],
    seed_catalog: dict[str, Any],
) -> None:
    case = await _create_arbitrating_case(
        client, seed_user, seed_admins, seed_merchant_account, seed_catalog
    )
    case_id = case["id"]

    lead_tokens = await login_admin(client, "cslead01", _LEAD_PWD)
    lead_headers = {"Authorization": f"Bearer {lead_tokens['access_token']}"}
    await client.post(f"/api/v1/admin/aftersales/{case_id}/take-over", headers=lead_headers)

    super_headers = await headers_admin(client, "super")
    resp = await client.post(
        f"/api/v1/admin/users/{seed_admins['CUSTOMER_SERVICE_LEAD'].id}/disable",
        headers=super_headers,
    )
    assert resp.json()["code"] == 0, resp.text

    detail = (
        await client.get(f"/api/v1/admin/aftersales/{case_id}", headers=super_headers)
    ).json()["data"]
    assert detail["arbitrator_admin_id"] is None


# ---------------------------------------------------------------------------
# CS_AGENT data scope
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cs_agent_scope_list_and_detail(
    client: AsyncClient,
    seed_user: User,
    seed_admins: dict[str, AdminUser],
    seed_merchant_account: tuple[Any, Any],
    seed_catalog: dict[str, Any],
) -> None:
    case = await _create_arbitrating_case(
        client, seed_user, seed_admins, seed_merchant_account, seed_catalog
    )
    case_id = case["id"]

    agent_headers = await headers_admin(client, "csagent01")
    listed = (await client.get("/api/v1/admin/aftersales", headers=agent_headers)).json()["data"]
    assert any(item["id"] == case_id for item in listed["items"])

    # CS_LEAD claims it → now out of the agent's scope.
    lead_headers = await headers_admin(client, "cslead01")
    await client.post(f"/api/v1/admin/aftersales/{case_id}/take-over", headers=lead_headers)

    listed = (await client.get("/api/v1/admin/aftersales", headers=agent_headers)).json()["data"]
    assert all(item["id"] != case_id for item in listed["items"])

    detail = (await client.get(f"/api/v1/admin/aftersales/{case_id}", headers=agent_headers)).json()
    assert detail["code"] == 18005  # AFTERSALES_NOT_CLAIMED_BY_SELF


# ---------------------------------------------------------------------------
# CS_LEAD release
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cs_lead_release_claimed_case(
    client: AsyncClient,
    seed_user: User,
    seed_admins: dict[str, AdminUser],
    seed_merchant_account: tuple[Any, Any],
    seed_catalog: dict[str, Any],
) -> None:
    case = await _create_arbitrating_case(
        client, seed_user, seed_admins, seed_merchant_account, seed_catalog
    )
    case_id = case["id"]

    lead_headers = await headers_admin(client, "cslead01")
    resp = await client.post(f"/api/v1/admin/aftersales/{case_id}/take-over", headers=lead_headers)
    assert resp.json()["data"]["arbitrator_admin_id"] is not None

    resp = await client.post(f"/api/v1/admin/aftersales/{case_id}/release", headers=lead_headers)
    assert resp.json()["code"] == 0, resp.text
    assert resp.json()["data"]["arbitrator_admin_id"] is None

    # Releasing an unclaimed case errors.
    resp = await client.post(f"/api/v1/admin/aftersales/{case_id}/release", headers=lead_headers)
    assert resp.json()["code"] == 18005


@pytest.mark.asyncio
async def test_cs_agent_cannot_release(
    client: AsyncClient,
    seed_user: User,
    seed_admins: dict[str, AdminUser],
    seed_merchant_account: tuple[Any, Any],
    seed_catalog: dict[str, Any],
) -> None:
    case = await _create_arbitrating_case(
        client, seed_user, seed_admins, seed_merchant_account, seed_catalog
    )
    agent_headers = await headers_admin(client, "csagent01")
    resp = await client.post(
        f"/api/v1/admin/aftersales/{case['id']}/release", headers=agent_headers
    )
    assert resp.json()["code"] != 0  # permission denied


# ---------------------------------------------------------------------------
# Audit log console
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_audit_log_list(
    client: AsyncClient,
    seed_admins: dict[str, AdminUser],
) -> None:
    super_headers = await headers_admin(client, "super")
    await _create_admin(client, super_headers, username="auditme01", role="TECH_ADMIN")

    listed = (await client.get("/api/v1/admin/audit-logs", headers=super_headers)).json()["data"]
    assert listed["total"] >= 1
    assert any(item["action"] == "admin.user.create" for item in listed["items"])

    tech_headers = await headers_admin(client, "tech01")
    filtered = (
        await client.get(
            "/api/v1/admin/audit-logs", headers=tech_headers, params={"action": "admin.user.create"}
        )
    ).json()["data"]
    assert all(item["action"] == "admin.user.create" for item in filtered["items"])


async def login_admin(client: AsyncClient, username: str, password: str) -> dict[str, Any]:
    body = await client.post(
        "/api/v1/admin/auth/login", json={"username": username, "password": password}
    )
    assert body.json()["code"] == 0, body.text
    return body.json()["data"]
