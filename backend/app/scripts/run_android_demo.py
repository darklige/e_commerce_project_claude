"""Run a local backend demo for the Android emulator.

This avoids external infra by default:
- SQLite file DB
- fakeredis in-process
- local seed data

Start with:
    python -m app.scripts.run_android_demo
"""

from __future__ import annotations

import asyncio
import logging
import os


def _apply_demo_env() -> None:
    os.environ.setdefault("ENVIRONMENT", "local")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./jdclone_android_demo.db")
    os.environ.setdefault("REDIS_URL", "fakeredis://local")
    os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
    os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
    os.environ.setdefault("MINIO_BUCKET", "jdclone")
    os.environ.setdefault("MINIO_PUBLIC_BUCKET", "jdclone-public")
    os.environ.setdefault("MINIO_PRIVATE_BUCKET", "jdclone-private")
    os.environ.setdefault("MINIO_PUBLIC_BASE_URL", "http://10.0.2.2:9000/jdclone-public")
    os.environ.setdefault("SECRET_KEY", "android-demo-secret-key-with-at-least-32-chars")
    os.environ.setdefault(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://10.0.2.2:3000",
    )


_apply_demo_env()

import uvicorn

from app.core.database import dispose_engine, engine
from app.models import Base
from app.scripts import seed as seed_script

logger = logging.getLogger(__name__)


async def _bootstrap_demo_data() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_script._seed()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )
    try:
        asyncio.run(_bootstrap_demo_data())
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
    finally:
        asyncio.run(dispose_engine())


if __name__ == "__main__":
    main()
