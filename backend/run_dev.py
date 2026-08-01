"""Development entry point — runs without Docker/PostgreSQL/Redis/MinIO.

Usage:
    uv run uvicorn run_dev:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dev.db"
os.environ["ENVIRONMENT"] = "local"

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import fakeredis.aioredis
from passlib.context import CryptContext
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.core.redis import close_redis, get_redis
from app.main import create_app
from app.models.base import Base

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def _init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.commit()


async def _seed_defaults():
    from app.models.admin_user import AdminRole, AdminStatus, AdminUser
    from app.models.user import User, UserStatus

    async with async_session_factory() as session:
        r = await session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        if not r.scalar_one_or_none():
            session.add(AdminUser(
                username="admin",
                password_hash=_pwd_ctx.hash("admin123"),
                display_name="Super Admin",
                role=AdminRole.SUPER_ADMIN,
                status=AdminStatus.ACTIVE,
            ))
            print("Created admin: admin / admin123")

        r = await session.execute(select(User).where(User.email == "user@test.com"))
        if not r.scalar_one_or_none():
            session.add(User(
                email="user@test.com",
                phone="13800000001",
                password_hash=_pwd_ctx.hash("user123"),
                nickname="TestUser",
                status=UserStatus.ACTIVE,
            ))
            print("Created user: user@test.com / user123")

        await session.commit()


fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)


async def _override_get_redis():
    yield fake_redis


@asynccontextmanager
async def _dev_lifespan(_app) -> AsyncIterator[None]:
    print("Initializing dev database...")
    await _init_db()
    await _seed_defaults()
    print(f"Ready! Docs at http://localhost:{os.environ.get('BACKEND_PORT', '8000')}/docs")
    yield
    await close_redis()


app = create_app()
app.dependency_overrides[get_redis] = _override_get_redis

# replace lifespan
from app.main import lifespan as _orig_lifespan  # noqa: E402

app.router.lifespan_context = _dev_lifespan
