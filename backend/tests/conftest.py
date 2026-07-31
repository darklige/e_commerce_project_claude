"""Pytest fixtures for backend tests.

Uses SQLite (aiosqlite) + fakeredis so tests run without Postgres/Redis.
Each test gets a freshly-migrated in-memory schema so tests are fully
isolated. This mirrors the Postgres schema created by the Phase 1
Alembic migration closely enough for auth/RBAC behaviour, which is
what Phase 1 tests exercise.
"""

from __future__ import annotations

import asyncio
import warnings
from collections.abc import AsyncIterator, Iterator
from typing import Any

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# We patch the `Enum` decorator we compile into Postgres-only options
# to be portable when the test DB is SQLite. Do this before importing
# the models.
warnings.filterwarnings("ignore", category=DeprecationWarning)

from app.api.deps import get_current_admin, get_current_merchant, get_current_user  # noqa: E402
from app.core import database as core_db  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.admin_user import AdminRole, AdminStatus, AdminUser  # noqa: E402
from app.models.brand import Brand  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.merchant import (  # noqa: E402
    MerchantAccount,
    MerchantAccountStatus,
    MerchantRole,
    Shop,
    ShopStatus,
)
from app.models.user import User, UserStatus  # noqa: E402


# ---------------------------------------------------------------------------
# Async event loop (session-scoped so pytest-asyncio uses a single loop)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Fresh in-memory SQLite engine per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture()
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with db_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Redis (fakeredis)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def fake_redis() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


# ---------------------------------------------------------------------------
# App + HTTP client
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def client(
    db_session_factory: async_sessionmaker[AsyncSession],
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> AsyncIterator[AsyncClient]:
    """AsyncClient talking to the real FastAPI app with test DB + Redis."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with db_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    async def _override_get_redis() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
        yield fake_redis

    # Also patch the module-level session factory that services import
    # directly (e.g. the seed script). Tests using services through the
    # HTTP layer will hit the DI override; services using
    # ``async_session_factory`` directly hit this patch.
    original_factory = core_db.async_session_factory
    core_db.async_session_factory = db_session_factory  # type: ignore[assignment]

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    fastapi_app.dependency_overrides[get_redis] = _override_get_redis

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.pop(get_db, None)
    fastapi_app.dependency_overrides.pop(get_redis, None)
    fastapi_app.dependency_overrides.pop(get_current_user, None)
    fastapi_app.dependency_overrides.pop(get_current_merchant, None)
    fastapi_app.dependency_overrides.pop(get_current_admin, None)
    core_db.async_session_factory = original_factory  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def seed_admins(db_session: AsyncSession) -> dict[str, AdminUser]:
    """Insert one admin per role, return by role name."""
    admins: dict[str, AdminUser] = {}
    for role, username, pwd in (
        (AdminRole.SUPER_ADMIN, "super", "super_pwd_change_me"),
        (AdminRole.BUSINESS_ADMIN, "biz01", "biz_pwd_change_me"),
        (AdminRole.CUSTOMER_SERVICE_ADMIN, "cs01", "cs_pwd_change_me"),
        (AdminRole.CUSTOMER_SERVICE_LEAD, "cslead01", "cslead_pwd_change_me"),
        (AdminRole.CUSTOMER_SERVICE_AGENT, "csagent01", "csagent_pwd_change_me"),
        (AdminRole.TECH_ADMIN, "tech01", "tech_pwd_change_me"),
    ):
        row = AdminUser(
            username=username,
            password_hash=hash_password(pwd),
            display_name=f"admin-{role.value}",
            role=role,
            status=AdminStatus.ACTIVE,
        )
        db_session.add(row)
        admins[role.value] = row
    await db_session.commit()
    for row in admins.values():
        await db_session.refresh(row)
    return admins


@pytest_asyncio.fixture()
async def seed_user(db_session: AsyncSession) -> User:
    row = User(
        phone="13800000001",
        email=None,
        password_hash=hash_password("Test1234"),
        nickname="老李",
        status=UserStatus.ACTIVE,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest_asyncio.fixture()
async def seed_second_user(db_session: AsyncSession) -> User:
    row = User(
        phone="13800000002",
        email=None,
        password_hash=hash_password("Test1234"),
        nickname="老王",
        status=UserStatus.ACTIVE,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest_asyncio.fixture()
async def seed_merchant_account(
    db_session: AsyncSession, seed_user: User
) -> tuple[MerchantAccount, Shop]:
    shop = Shop(
        name="小李杂货铺",
        description=None,
        contact_name="老李",
        contact_phone="13800000001",
        status=ShopStatus.ACTIVE,
    )
    db_session.add(shop)
    await db_session.flush()
    account = MerchantAccount(
        user_id=seed_user.id,
        login_name=f"shop{shop.id}_owner",
        password_hash=hash_password("Merch1234"),
        shop_id=shop.id,
        role=MerchantRole.SHOP_OWNER,
        status=MerchantAccountStatus.ACTIVE,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    await db_session.refresh(shop)
    return account, shop


@pytest_asyncio.fixture()
async def seed_catalog(
    db_session: AsyncSession,
) -> dict[str, object]:
    """Seed a small 3-level category tree + one brand for Phase 2 tests."""
    # level 1
    root = Category(
        parent_id=None,
        name="数码",
        slug="digital",
        level=1,
        path="pending",
        sort_order=0,
        is_visible=True,
    )
    db_session.add(root)
    await db_session.flush()
    root.path = str(root.id)

    # level 2
    l2 = Category(
        parent_id=root.id,
        name="手机通讯",
        slug="phones-communication",
        level=2,
        path="pending",
        sort_order=0,
        is_visible=True,
    )
    db_session.add(l2)
    await db_session.flush()
    l2.path = f"{root.path}/{l2.id}"

    # level 3 (leaf)
    leaf = Category(
        parent_id=l2.id,
        name="手机",
        slug="phones",
        level=3,
        path="pending",
        sort_order=0,
        is_visible=True,
    )
    db_session.add(leaf)
    await db_session.flush()
    leaf.path = f"{l2.path}/{leaf.id}"

    # a second sibling leaf for edit/moving tests
    leaf2 = Category(
        parent_id=l2.id,
        name="对讲机",
        slug="walkie-talkies",
        level=3,
        path="pending",
        sort_order=1,
        is_visible=True,
    )
    db_session.add(leaf2)
    await db_session.flush()
    leaf2.path = f"{l2.path}/{leaf2.id}"

    brand = Brand(
        name="Apple",
        slug="apple",
        logo_url="brand/seed/apple.png",
        description=None,
        sort_order=0,
        is_visible=True,
    )
    db_session.add(brand)
    await db_session.commit()

    await db_session.refresh(root)
    await db_session.refresh(l2)
    await db_session.refresh(leaf)
    await db_session.refresh(leaf2)
    await db_session.refresh(brand)

    return {
        "root": root,
        "l2": l2,
        "leaf": leaf,
        "leaf2": leaf2,
        "brand": brand,
    }


# ---------------------------------------------------------------------------
# Convenience: auth helpers
# ---------------------------------------------------------------------------
async def _post(client: AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = await client.post(url, json=payload)
    return resp.json()


async def login_user_get_tokens(client: AsyncClient, phone: str, password: str) -> dict[str, Any]:
    body = await _post(
        client, "/api/v1/user/auth/login", {"identifier": phone, "password": password}
    )
    assert body["code"] == 0, body
    return body["data"]


async def login_admin_get_tokens(
    client: AsyncClient, username: str, password: str
) -> dict[str, Any]:
    body = await _post(
        client, "/api/v1/admin/auth/login", {"username": username, "password": password}
    )
    assert body["code"] == 0, body
    return body["data"]


async def login_merchant_get_tokens(
    client: AsyncClient, login_name: str, password: str
) -> dict[str, Any]:
    body = await _post(
        client,
        "/api/v1/merchant/auth/login",
        {"login_name": login_name, "password": password},
    )
    assert body["code"] == 0, body
    return body["data"]


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
