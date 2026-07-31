"""Authentication service.

Home of the register / login / refresh / logout / forgot-password /
reset-password business logic across all three identity domains.

Design notes:
- Access tokens are 15-minute HS256 JWTs (contract §10).
- Refresh tokens are opaque 48-byte URL-safe random strings; only the
  SHA-256 hash is persisted (contract §4.6).
- Login failures merge "unknown identifier" and "wrong password" into
  the same error to prevent user enumeration.
- Forgot-password always returns 200 regardless of whether the account
  exists — the actual code is written to Redis + logger.info.
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Literal

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException, ErrorCode
from app.core.security import (
    Audience,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.admin_user import AdminStatus, AdminUser
from app.models.audit_log import AuditActorType
from app.models.merchant import MerchantAccount, MerchantAccountStatus
from app.models.refresh_token import RefreshToken, SubjectType
from app.models.user import User, UserStatus
from app.schemas.auth import (
    ForgotPasswordIn,
    ResetPasswordIn,
    TokenPairOut,
    UserAuthOut,
    UserBrief,
    UserLoginIn,
    UserRegisterIn,
)
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)

# 15 minutes — matches JWT exp in create_access_token.
ACCESS_TOKEN_TTL = timedelta(minutes=15)
# 30 days — matches contract §10.
REFRESH_TOKEN_TTL = timedelta(days=30)
# Forgot-password verification code TTL.
FORGOT_PASSWORD_TTL_SECONDS = 300


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _redis_key_pwreset(scope: Literal["user"], identifier: str) -> str:
    return f"pwreset:{scope}:{identifier}"


def _default_nickname(user_id: int) -> str:
    """Contract §5.1: ``用户{id 后 6 位}`` when nickname not provided."""
    return f"用户{user_id % 1_000_000:06d}"


def _identifier_is_email(identifier: str) -> bool:
    return "@" in identifier


async def _find_user_by_identifier(session: AsyncSession, identifier: str) -> User | None:
    if _identifier_is_email(identifier):
        stmt = select(User).where(User.email == identifier, User.deleted_at.is_(None))
    else:
        stmt = select(User).where(User.phone == identifier, User.deleted_at.is_(None))
    return (await session.execute(stmt)).scalar_one_or_none()


def _generate_random_password(length: int = 12) -> str:
    """Generate a URL-safe random password (letters + digits)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _persist_refresh_token(
    session: AsyncSession,
    *,
    subject_type: SubjectType,
    subject_id: int,
    ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Create + persist a refresh token; return the plaintext to caller."""
    plaintext = generate_refresh_token()
    now = datetime.now(UTC)
    session.add(
        RefreshToken(
            token_hash=hash_refresh_token(plaintext),
            subject_type=subject_type,
            subject_id=subject_id,
            issued_at=now,
            expires_at=now + REFRESH_TOKEN_TTL,
            ip=ip,
            user_agent=user_agent,
        )
    )
    await session.flush()
    return plaintext


async def _revoke_refresh_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        await session.flush()
    return row


async def _revoke_all_refresh_for_subject(
    session: AsyncSession, subject_type: SubjectType, subject_id: int
) -> None:
    stmt = select(RefreshToken).where(
        RefreshToken.subject_type == subject_type,
        RefreshToken.subject_id == subject_id,
        RefreshToken.revoked_at.is_(None),
    )
    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(UTC)
    for row in rows:
        row.revoked_at = now
    await session.flush()


async def revoke_all_sessions_for_admin(session: AsyncSession, admin_id: int) -> None:
    """Revoke every outstanding refresh token for an admin (kicks them out).

    Access tokens keep working until their own 15-minute ``exp`` — no
    central blacklist (Phase 6 decision)."""
    await _revoke_all_refresh_for_subject(session, SubjectType.ADMIN, admin_id)


def _build_user_brief(user: User) -> UserBrief:
    return UserBrief(
        id=user.id,
        phone=user.phone,
        email=user.email,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
    )


def _seconds(td: timedelta) -> int:
    return int(td.total_seconds())


# ---------------------------------------------------------------------------
# User: register / login / refresh / logout
# ---------------------------------------------------------------------------
async def register_user(
    session: AsyncSession,
    payload: UserRegisterIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> UserAuthOut:
    """Create a new consumer account and immediately issue tokens."""
    if payload.phone is not None:
        exists = await session.execute(select(User.id).where(User.phone == payload.phone))
        if exists.scalar_one_or_none() is not None:
            raise AppException(ErrorCode.PHONE_ALREADY_REGISTERED, "phone already registered")
    if payload.email is not None:
        exists = await session.execute(select(User.id).where(User.email == payload.email))
        if exists.scalar_one_or_none() is not None:
            raise AppException(ErrorCode.EMAIL_ALREADY_REGISTERED, "email already registered")

    user = User(
        phone=payload.phone,
        email=payload.email,
        password_hash=hash_password(payload.password),
        # placeholder — replaced after we know the id
        nickname=payload.nickname or "user",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()  # populate user.id

    if payload.nickname is None:
        user.nickname = _default_nickname(user.id)
        await session.flush()

    access = create_access_token(subject=user.id, audience="user")
    refresh = await _persist_refresh_token(
        session,
        subject_type=SubjectType.USER,
        subject_id=user.id,
        ip=ip,
        user_agent=user_agent,
    )

    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.register",
        target_type="user",
        target_id=user.id,
        ip=ip,
        user_agent=user_agent,
    )

    return UserAuthOut(
        user=_build_user_brief(user),
        access_token=access,
        refresh_token=refresh,
        expires_in=_seconds(ACCESS_TOKEN_TTL),
    )


async def login_user(
    session: AsyncSession,
    payload: UserLoginIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> UserAuthOut:
    """Verify credentials and issue a fresh access/refresh pair."""
    user = await _find_user_by_identifier(session, payload.identifier)

    if user is None or not verify_password(payload.password, user.password_hash):
        # Contract §5.1: merged for anti-enumeration.
        await write_audit(
            session,
            actor_type=AuditActorType.ANONYMOUS,
            actor_id=None,
            action="user.login.failed",
            ip=ip,
            user_agent=user_agent,
            extra={"identifier": payload.identifier},
        )
        raise AppException(ErrorCode.BAD_CREDENTIALS, "bad credentials")

    if user.status != UserStatus.ACTIVE:
        raise AppException(ErrorCode.ACCOUNT_DISABLED, "account disabled")

    user.last_login_at = datetime.now(UTC)
    await session.flush()

    access = create_access_token(subject=user.id, audience="user")
    refresh = await _persist_refresh_token(
        session,
        subject_type=SubjectType.USER,
        subject_id=user.id,
        ip=ip,
        user_agent=user_agent,
    )

    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.login",
        target_type="user",
        target_id=user.id,
        ip=ip,
        user_agent=user_agent,
    )

    return UserAuthOut(
        user=_build_user_brief(user),
        access_token=access,
        refresh_token=refresh,
        expires_in=_seconds(ACCESS_TOKEN_TTL),
    )


# ---------------------------------------------------------------------------
# Merchant: login
# ---------------------------------------------------------------------------
async def login_merchant(
    session: AsyncSession,
    login_name: str,
    password: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[MerchantAccount, TokenPairOut]:
    """Verify merchant credentials and issue a merchant-aud token pair."""
    stmt = select(MerchantAccount).where(
        MerchantAccount.login_name == login_name,
        MerchantAccount.deleted_at.is_(None),
    )
    account = (await session.execute(stmt)).scalar_one_or_none()

    if account is None or not verify_password(password, account.password_hash):
        await write_audit(
            session,
            actor_type=AuditActorType.ANONYMOUS,
            actor_id=None,
            action="merchant.login.failed",
            ip=ip,
            user_agent=user_agent,
            extra={"login_name": login_name},
        )
        raise AppException(ErrorCode.BAD_CREDENTIALS, "bad credentials")

    if account.status != MerchantAccountStatus.ACTIVE:
        raise AppException(ErrorCode.MERCHANT_ACCOUNT_FROZEN, "merchant account frozen")

    account.last_login_at = datetime.now(UTC)
    await session.flush()

    access = create_access_token(
        subject=account.id,
        audience="merchant",
        extra_claims={"role": account.role.value, "shop_id": account.shop_id},
    )
    refresh = await _persist_refresh_token(
        session,
        subject_type=SubjectType.MERCHANT,
        subject_id=account.id,
        ip=ip,
        user_agent=user_agent,
    )

    await write_audit(
        session,
        actor_type=AuditActorType.MERCHANT,
        actor_id=account.id,
        action="merchant.login",
        target_type="merchant_account",
        target_id=account.id,
        ip=ip,
        user_agent=user_agent,
    )

    return account, TokenPairOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=_seconds(ACCESS_TOKEN_TTL),
    )


# ---------------------------------------------------------------------------
# Admin: login
# ---------------------------------------------------------------------------
async def login_admin(
    session: AsyncSession,
    username: str,
    password: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[AdminUser, TokenPairOut]:
    """Verify admin credentials and issue an admin-aud token pair."""
    stmt = select(AdminUser).where(AdminUser.username == username, AdminUser.deleted_at.is_(None))
    admin = (await session.execute(stmt)).scalar_one_or_none()

    if admin is None or not verify_password(password, admin.password_hash):
        await write_audit(
            session,
            actor_type=AuditActorType.ANONYMOUS,
            actor_id=None,
            action="admin.login.failed",
            ip=ip,
            user_agent=user_agent,
            extra={"username": username},
        )
        raise AppException(ErrorCode.BAD_CREDENTIALS, "bad credentials")

    if admin.status != AdminStatus.ACTIVE:
        raise AppException(ErrorCode.ACCOUNT_DISABLED, "admin account disabled")

    admin.last_login_at = datetime.now(UTC)
    await session.flush()

    access = create_access_token(
        subject=admin.id,
        audience="admin",
        extra_claims={"role": admin.role.value},
    )
    refresh = await _persist_refresh_token(
        session,
        subject_type=SubjectType.ADMIN,
        subject_id=admin.id,
        ip=ip,
        user_agent=user_agent,
    )

    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=admin.id,
        action="admin.login",
        target_type="admin_user",
        target_id=admin.id,
        ip=ip,
        user_agent=user_agent,
    )

    return admin, TokenPairOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=_seconds(ACCESS_TOKEN_TTL),
    )


# ---------------------------------------------------------------------------
# Refresh / logout — shared across the three domains
# ---------------------------------------------------------------------------
async def admin_change_password(
    session: AsyncSession,
    admin: AdminUser,
    old_password: str,
    new_password: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Verify old password, rewrite the hash, revoke all self refresh tokens."""
    if not verify_password(old_password, admin.password_hash):
        raise AppException(ErrorCode.OLD_PASSWORD_MISMATCH, "old password mismatch")

    admin.password_hash = hash_password(new_password)
    admin.password_changed_at = datetime.now(UTC)
    await session.flush()

    await revoke_all_sessions_for_admin(session, admin.id)

    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=admin.id,
        action="admin.password.change",
        target_type="admin_user",
        target_id=admin.id,
        ip=ip,
        user_agent=user_agent,
    )


async def refresh_tokens(
    session: AsyncSession,
    refresh_token_plaintext: str,
    subject_type: SubjectType,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> TokenPairOut:
    """Rotate a refresh token: revoke the old, issue a new pair."""
    token_hash = hash_refresh_token(refresh_token_plaintext)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.subject_type == subject_type,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()

    if row is None or row.revoked_at is not None:
        raise AppException(ErrorCode.INVALID_REFRESH_TOKEN, "invalid refresh token")
    if row.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        raise AppException(ErrorCode.INVALID_REFRESH_TOKEN, "refresh token expired")

    # Rotate: revoke the old token first.
    row.revoked_at = datetime.now(UTC)
    await session.flush()

    audience: Audience
    extra_claims: dict[str, object] = {}
    if subject_type == SubjectType.USER:
        audience = "user"
    elif subject_type == SubjectType.MERCHANT:
        audience = "merchant"
        merchant = await session.get(MerchantAccount, row.subject_id)
        if merchant is None:
            raise AppException(ErrorCode.INVALID_REFRESH_TOKEN, "subject missing")
        extra_claims = {"role": merchant.role.value, "shop_id": merchant.shop_id}
    else:
        audience = "admin"
        admin = await session.get(AdminUser, row.subject_id)
        if admin is None:
            raise AppException(ErrorCode.INVALID_REFRESH_TOKEN, "subject missing")
        extra_claims = {"role": admin.role.value}

    access = create_access_token(
        subject=row.subject_id, audience=audience, extra_claims=extra_claims or None
    )
    new_refresh = await _persist_refresh_token(
        session,
        subject_type=subject_type,
        subject_id=row.subject_id,
        ip=ip,
        user_agent=user_agent,
    )

    return TokenPairOut(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=_seconds(ACCESS_TOKEN_TTL),
    )


async def logout(
    session: AsyncSession,
    refresh_token_plaintext: str | None,
    subject_type: SubjectType,
    subject_id: int,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Revoke the supplied refresh token, if any.

    Access tokens remain valid until their own ``exp`` (Phase 1 does not
    implement an access-token blacklist).
    """
    if refresh_token_plaintext:
        await _revoke_refresh_by_hash(session, hash_refresh_token(refresh_token_plaintext))

    actor_type = {
        SubjectType.USER: AuditActorType.USER,
        SubjectType.MERCHANT: AuditActorType.MERCHANT,
        SubjectType.ADMIN: AuditActorType.ADMIN,
    }[subject_type]

    await write_audit(
        session,
        actor_type=actor_type,
        actor_id=subject_id,
        action=f"{subject_type.value}.logout",
        target_type=subject_type.value,
        target_id=subject_id,
        ip=ip,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Forgot-password flow (User domain only in Phase 1)
# ---------------------------------------------------------------------------
async def forgot_password(
    redis: aioredis.Redis,
    payload: ForgotPasswordIn,
) -> None:
    """Generate a 6-digit code, store in Redis, log it (simulated SMS).

    Always succeeds (regardless of account existence) to prevent
    account enumeration. In production this would enqueue an SMS /
    email; Phase 1 just prints to the app log.
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    key = _redis_key_pwreset("user", payload.identifier)
    await redis.setex(key, FORGOT_PASSWORD_TTL_SECONDS, code)
    # SIMULATED CHANNEL — real SMS/email is deferred; contract §5.1
    # says we log the code so devs can complete the flow manually.
    logger.info(
        "forgot-password code issued: identifier=%s code=%s ttl=%ds",
        payload.identifier,
        code,
        FORGOT_PASSWORD_TTL_SECONDS,
    )


async def reset_password(
    session: AsyncSession,
    redis: aioredis.Redis,
    payload: ResetPasswordIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Verify the code, rewrite the password, revoke all refresh tokens."""
    key = _redis_key_pwreset("user", payload.identifier)
    cached = await redis.get(key)
    if cached is None or cached != payload.code:
        raise AppException(ErrorCode.INVALID_CAPTCHA, "invalid or expired code")

    user = await _find_user_by_identifier(session, payload.identifier)
    if user is None:
        # Same error code as bad captcha to prevent enumeration.
        raise AppException(ErrorCode.INVALID_CAPTCHA, "invalid or expired code")

    user.password_hash = hash_password(payload.new_password)
    await session.flush()

    # Wipe the code and revoke all outstanding refresh tokens.
    await redis.delete(key)
    await _revoke_all_refresh_for_subject(session, SubjectType.USER, user.id)

    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.password.reset",
        target_type="user",
        target_id=user.id,
        ip=ip,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Helpers used by merchant onboarding
# ---------------------------------------------------------------------------
def generate_initial_merchant_password() -> str:
    """Public wrapper — kept out of module private for reuse in service tests."""
    return _generate_random_password(12)


def hash_new_password(plain: str) -> str:
    """Wrapper so callers don't need to import ``security`` directly."""
    return hash_password(plain)


# Re-exported for tests / callers that want the shared utilities.
__all__ = [
    "ACCESS_TOKEN_TTL",
    "FORGOT_PASSWORD_TTL_SECONDS",
    "REFRESH_TOKEN_TTL",
    "admin_change_password",
    "forgot_password",
    "generate_initial_merchant_password",
    "hash_new_password",
    "login_admin",
    "login_merchant",
    "login_user",
    "logout",
    "refresh_tokens",
    "register_user",
    "reset_password",
    "revoke_all_sessions_for_admin",
]
