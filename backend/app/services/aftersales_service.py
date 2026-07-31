"""Aftersales service — Phase 4 contract §5-§13.

Owns the 12-state aftersales lifecycle. All state transitions go through
:func:`_transition` so ``aftersales_status_history`` rows and status
flips stay consistent. Refund execution is delegated to
:mod:`app.services.refund_service`.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppException, ErrorCode
from app.core.rbac import AftersalesScope, aftersales_scope_for_admin
from app.models.admin_user import AdminUser
from app.models.aftersales import (
    Aftersales,
    AftersalesArbitrationOutcome,
    AftersalesCloseReason,
    AftersalesEscalationReason,
    AftersalesReasonCategory,
    AftersalesStatus,
    AftersalesType,
)
from app.models.aftersales_evidence import (
    AftersalesEvidence,
    AftersalesEvidenceStage,
    AftersalesEvidenceUploaderType,
)
from app.models.aftersales_item import AftersalesItem
from app.models.aftersales_message import (
    AftersalesMessage,
    AftersalesMessageKind,
    AftersalesMessageSenderType,
)
from app.models.aftersales_status_history import (
    AftersalesActorType,
    AftersalesStatusHistory,
)
from app.models.audit_log import AuditActorType
from app.models.merchant import MerchantAccount
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.user import User
from app.schemas.aftersales import (
    AftersalesAppealIn,
    AftersalesConfirmReceiveIn,
    AftersalesCreateIn,
    AftersalesDetailOut,
    AftersalesEvidenceIn,
    AftersalesEvidenceOut,
    AftersalesForceRefundIn,
    AftersalesItemOut,
    AftersalesListItemOut,
    AftersalesMerchantApproveIn,
    AftersalesMerchantRejectIn,
    AftersalesMessageOut,
    AftersalesNudgeOut,
    AftersalesRefuseReceiveIn,
    AftersalesResolveIn,
    AftersalesShipExchangeIn,
    AftersalesStatsOverviewOut,
    AftersalesStatusHistoryOut,
    AftersalesSubmitTrackingIn,
    MerchantAftersalesStatsOut,
)
from app.services import refund_service, risk_service
from app.services.audit_service import write_audit


async def _notify_aftersales_event(
    session: AsyncSession,
    aftersales: Aftersales,
    *,
    event: str,
) -> None:
    """Best-effort notification hook (Phase 5)."""
    try:
        from app.models.admin_user import AdminRole
        from app.models.notification import NotificationCategory
        from app.services import notification_service

        if event == "created":
            await notification_service.notify_merchants_of_shop(
                session,
                aftersales.shop_id,
                NotificationCategory.AFTERSALES,
                title=f"新的售后申请 {aftersales.aftersales_no}",
                body=aftersales.reason_note[:80] if aftersales.reason_note else "用户发起售后",
                action_url=f"/merchant/aftersales/{aftersales.id}",
                related_type="aftersales",
                related_id=aftersales.id,
            )
        elif event == "merchant_approved":
            await notification_service.notify_user(
                session,
                aftersales.user_id,
                NotificationCategory.AFTERSALES,
                title=f"售后 {aftersales.aftersales_no} 已通过审核",
                body="商家已同意您的售后申请",
                action_url=f"/user/aftersales/{aftersales.id}",
                related_type="aftersales",
                related_id=aftersales.id,
            )
        elif event == "merchant_rejected":
            await notification_service.notify_user(
                session,
                aftersales.user_id,
                NotificationCategory.AFTERSALES,
                title=f"售后 {aftersales.aftersales_no} 已被驳回",
                body=aftersales.merchant_review_note or "商家驳回",
                action_url=f"/user/aftersales/{aftersales.id}",
                related_type="aftersales",
                related_id=aftersales.id,
            )
        elif event == "escalated":
            await notification_service.notify_admins(
                session,
                NotificationCategory.AFTERSALES,
                role_filter=AdminRole.CUSTOMER_SERVICE_ADMIN,
                title=f"售后升级仲裁 {aftersales.aftersales_no}",
                body=(
                    aftersales.escalation_reason.value
                    if aftersales.escalation_reason
                    else "escalated"
                ),
                action_url=f"/admin/aftersales/{aftersales.id}",
                related_type="aftersales",
                related_id=aftersales.id,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Constants & tiny helpers
# ---------------------------------------------------------------------------
FINAL_STATUSES: frozenset[AftersalesStatus] = frozenset(
    {
        AftersalesStatus.COMPLETED_REFUNDED,
        AftersalesStatus.COMPLETED_EXCHANGED,
        AftersalesStatus.USER_CANCELLED,
        AftersalesStatus.SYSTEM_CLOSED,
        AftersalesStatus.MERCHANT_REJECTED,
    }
)

_ORDER_STATUS_ALLOWED: dict[AftersalesType, frozenset[OrderStatus]] = {
    AftersalesType.REFUND_ONLY: frozenset({OrderStatus.PAID, OrderStatus.SHIPPED}),
    AftersalesType.RETURN_REFUND: frozenset({OrderStatus.SHIPPED, OrderStatus.COMPLETED}),
    AftersalesType.EXCHANGE: frozenset({OrderStatus.SHIPPED, OrderStatus.COMPLETED}),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _as_aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; coerce back to UTC when reading."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ---------------------------------------------------------------------------
# aftersales_no generation
# ---------------------------------------------------------------------------
def _generate_aftersales_no() -> str:
    today = _now().strftime("%Y%m%d")
    tail = f"{secrets.randbelow(10_000_000_000):010d}"
    return f"AS{today}{tail}"


async def _insert_aftersales_with_unique_no(
    session: AsyncSession,
    row: Aftersales,
) -> None:
    """Insert an ``Aftersales`` row, retrying on aftersales_no collisions.

    Wraps each attempt in a SAVEPOINT so a duplicate-key failure can be
    rolled back without discarding the outer transaction.
    """
    last_error: Exception | None = None
    for _ in range(5):
        row.aftersales_no = _generate_aftersales_no()
        try:
            async with session.begin_nested():
                session.add(row)
                await session.flush()
            return
        except IntegrityError as exc:
            last_error = exc
            continue
    raise AppException(
        ErrorCode.INTERNAL_ERROR,
        f"failed to generate a unique aftersales_no: {last_error}",
    )


# ---------------------------------------------------------------------------
# History / transitions
# ---------------------------------------------------------------------------
async def _write_history(
    session: AsyncSession,
    aftersales: Aftersales,
    *,
    from_status: str | None,
    to_status: str,
    actor_type: AftersalesActorType,
    actor_id: int | None,
    note: str | None,
) -> None:
    session.add(
        AftersalesStatusHistory(
            aftersales_id=aftersales.id,
            from_status=from_status,
            to_status=to_status,
            actor_type=actor_type,
            actor_id=actor_id,
            note=note,
        )
    )
    await session.flush()


async def _transition(
    session: AsyncSession,
    aftersales: Aftersales,
    to_status: AftersalesStatus,
    *,
    actor_type: AftersalesActorType,
    actor_id: int | None,
    note: str | None,
    allowed_from: Iterable[AftersalesStatus],
) -> None:
    allowed = set(allowed_from)
    if aftersales.status not in allowed:
        raise AppException(
            ErrorCode.AFTERSALES_STATUS_INVALID_FOR_ACTION,
            f"cannot transition from {aftersales.status.value} to {to_status.value}",
        )
    from_str = aftersales.status.value
    aftersales.status = to_status
    await _write_history(
        session,
        aftersales,
        from_status=from_str,
        to_status=to_status.value,
        actor_type=actor_type,
        actor_id=actor_id,
        note=note,
    )


async def _write_message(
    session: AsyncSession,
    aftersales: Aftersales,
    *,
    sender_type: AftersalesMessageSenderType,
    sender_id: int | None,
    kind: AftersalesMessageKind,
    content: str,
) -> None:
    session.add(
        AftersalesMessage(
            aftersales_id=aftersales.id,
            sender_type=sender_type,
            sender_id=sender_id,
            kind=kind,
            content=content,
        )
    )
    await session.flush()


async def _write_evidences(
    session: AsyncSession,
    aftersales: Aftersales,
    *,
    keys: Iterable[str],
    stage: AftersalesEvidenceStage,
    uploader_type: AftersalesEvidenceUploaderType,
    uploader_id: int,
) -> None:
    settings = get_settings()
    limit = settings.MAX_EVIDENCE_IMAGES_PER_STAGE
    keys_list = [k for k in keys if k]
    if not keys_list:
        return
    if len(keys_list) > limit:
        raise AppException(
            ErrorCode.AFTERSALES_EVIDENCE_LIMIT_EXCEEDED,
            f"at most {limit} evidence images per stage",
        )
    # Check current count for this stage.
    existing_stmt = select(func.count(AftersalesEvidence.id)).where(
        AftersalesEvidence.aftersales_id == aftersales.id,
        AftersalesEvidence.stage == stage,
    )
    existing = int((await session.execute(existing_stmt)).scalar_one())
    if existing + len(keys_list) > limit:
        raise AppException(
            ErrorCode.AFTERSALES_EVIDENCE_LIMIT_EXCEEDED,
            f"aftersales stage '{stage.value}' evidence total would exceed {limit}",
        )
    for k in keys_list:
        session.add(
            AftersalesEvidence(
                aftersales_id=aftersales.id,
                uploader_type=uploader_type,
                uploader_id=uploader_id,
                stage=stage,
                image_url=k,
            )
        )
    await session.flush()


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
async def _load(session: AsyncSession, aftersales_id: int) -> Aftersales:
    row = await session.get(Aftersales, aftersales_id)
    if row is None or row.deleted_at is not None:
        raise AppException(ErrorCode.AFTERSALES_NOT_FOUND, "aftersales not found")
    return row


async def _load_for_user(session: AsyncSession, user: User, aftersales_id: int) -> Aftersales:
    row = await _load(session, aftersales_id)
    if row.user_id != user.id:
        raise AppException(
            ErrorCode.AFTERSALES_PERMISSION_DENIED,
            "aftersales belongs to another user",
        )
    return row


async def _load_for_shop(
    session: AsyncSession, account: MerchantAccount, aftersales_id: int
) -> Aftersales:
    row = await _load(session, aftersales_id)
    if row.shop_id != account.shop_id:
        raise AppException(
            ErrorCode.AFTERSALES_PERMISSION_DENIED,
            "aftersales belongs to another shop",
        )
    return row


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
async def _load_items(session: AsyncSession, aftersales_id: int) -> list[AftersalesItem]:
    stmt = (
        select(AftersalesItem)
        .where(AftersalesItem.aftersales_id == aftersales_id)
        .order_by(AftersalesItem.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _load_history(session: AsyncSession, aftersales_id: int) -> list[AftersalesStatusHistory]:
    stmt = (
        select(AftersalesStatusHistory)
        .where(AftersalesStatusHistory.aftersales_id == aftersales_id)
        .order_by(AftersalesStatusHistory.created_at, AftersalesStatusHistory.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _load_evidences(session: AsyncSession, aftersales_id: int) -> list[AftersalesEvidence]:
    stmt = (
        select(AftersalesEvidence)
        .where(AftersalesEvidence.aftersales_id == aftersales_id)
        .order_by(AftersalesEvidence.created_at, AftersalesEvidence.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _load_messages(session: AsyncSession, aftersales_id: int) -> list[AftersalesMessage]:
    stmt = (
        select(AftersalesMessage)
        .where(AftersalesMessage.aftersales_id == aftersales_id)
        .order_by(AftersalesMessage.created_at, AftersalesMessage.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _serialize_detail(session: AsyncSession, aftersales: Aftersales) -> AftersalesDetailOut:
    await session.refresh(aftersales)
    items = await _load_items(session, aftersales.id)
    history = await _load_history(session, aftersales.id)
    evidences = await _load_evidences(session, aftersales.id)
    messages = await _load_messages(session, aftersales.id)
    return AftersalesDetailOut(
        id=aftersales.id,
        aftersales_no=aftersales.aftersales_no,
        order_id=aftersales.order_id,
        user_id=aftersales.user_id,
        shop_id=aftersales.shop_id,
        type=aftersales.type,
        status=aftersales.status,
        reason_category=aftersales.reason_category,
        reason_note=aftersales.reason_note,
        refund_amount_cents=aftersales.refund_amount_cents,
        actual_refund_cents=aftersales.actual_refund_cents,
        merchant_review_deadline=aftersales.merchant_review_deadline,
        escalated_at=aftersales.escalated_at,
        escalation_reason=aftersales.escalation_reason,
        arbitrator_admin_id=aftersales.arbitrator_admin_id,
        nudge_count=aftersales.nudge_count,
        appeal_count=aftersales.appeal_count,
        created_at=aftersales.created_at,
        updated_at=aftersales.updated_at,
        merchant_reviewed_at=aftersales.merchant_reviewed_at,
        merchant_review_note=aftersales.merchant_review_note,
        return_address=aftersales.return_address,
        return_carrier=aftersales.return_carrier,
        return_tracking_no=aftersales.return_tracking_no,
        return_shipped_at=aftersales.return_shipped_at,
        return_ship_deadline=aftersales.return_ship_deadline,
        merchant_received_at=aftersales.merchant_received_at,
        merchant_receive_deadline=aftersales.merchant_receive_deadline,
        merchant_refuse_receive=aftersales.merchant_refuse_receive,
        merchant_refuse_note=aftersales.merchant_refuse_note,
        exchange_carrier=aftersales.exchange_carrier,
        exchange_tracking_no=aftersales.exchange_tracking_no,
        exchange_shipped_at=aftersales.exchange_shipped_at,
        exchange_confirm_deadline=aftersales.exchange_confirm_deadline,
        exchange_confirmed_at=aftersales.exchange_confirmed_at,
        arbitrated_at=aftersales.arbitrated_at,
        arbitration_conclusion=aftersales.arbitration_conclusion,
        arbitration_outcome=aftersales.arbitration_outcome,
        refunded_at=aftersales.refunded_at,
        refund_txn_no=aftersales.refund_txn_no,
        closed_at=aftersales.closed_at,
        close_reason=aftersales.close_reason,
        last_nudged_at=aftersales.last_nudged_at,
        items=[AftersalesItemOut.model_validate(i) for i in items],
        status_history=[AftersalesStatusHistoryOut.model_validate(h) for h in history],
        evidences=[AftersalesEvidenceOut.model_validate(e) for e in evidences],
        messages=[AftersalesMessageOut.model_validate(m) for m in messages],
    )


def _serialize_list(rows: list[Aftersales]) -> list[AftersalesListItemOut]:
    return [AftersalesListItemOut.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
async def _has_active_aftersales(session: AsyncSession, order_id: int) -> bool:
    stmt = select(func.count(Aftersales.id)).where(
        Aftersales.order_id == order_id,
        Aftersales.deleted_at.is_(None),
        Aftersales.status.notin_(FINAL_STATUSES),
    )
    return int((await session.execute(stmt)).scalar_one()) > 0


async def _validate_items(
    session: AsyncSession,
    order: Order,
    items_in: list[Any],
    refund_amount_cents: int,
) -> list[tuple[OrderItem, int, int]]:
    """Validate the requested item lines against the parent order.

    Returns list of (order_item_row, quantity, per-line subtotal).
    """
    if not items_in:
        raise AppException(ErrorCode.AFTERSALES_NO_ITEMS_SELECTED, "no order_item selected")
    order_items_stmt = select(OrderItem).where(OrderItem.order_id == order.id)
    order_items = {r.id: r for r in (await session.execute(order_items_stmt)).scalars().all()}
    lines: list[tuple[OrderItem, int, int]] = []
    total = 0
    for it in items_in:
        oi = order_items.get(it.order_item_id)
        if oi is None:
            raise AppException(
                ErrorCode.AFTERSALES_NO_ITEMS_SELECTED,
                f"order_item {it.order_item_id} not in this order",
            )
        if it.quantity < 1 or it.quantity > oi.quantity:
            raise AppException(
                ErrorCode.AFTERSALES_NO_ITEMS_SELECTED,
                f"item {oi.id} quantity out of range",
            )
        line_amount = oi.unit_price_cents * it.quantity
        total += line_amount
        lines.append((oi, it.quantity, line_amount))
    if refund_amount_cents > total:
        raise AppException(
            ErrorCode.AFTERSALES_REFUND_AMOUNT_EXCEEDS,
            f"refund_amount_cents ({refund_amount_cents}) > items total ({total})",
        )
    return lines


# ---------------------------------------------------------------------------
# Order-side link (contract §13)
# ---------------------------------------------------------------------------
async def _order_side_link(session: AsyncSession, aftersales: Aftersales) -> None:
    order = await session.get(Order, aftersales.order_id)
    if order is None:
        return
    refunded = aftersales.actual_refund_cents or aftersales.refund_amount_cents
    if refunded > 0:
        order.total_refunded_cents = (order.total_refunded_cents or 0) + refunded
        # Full refund → close the order; partial → keep status, set flag.
        if order.total_refunded_cents >= order.total_cents:
            if order.status != OrderStatus.CLOSED:
                order.status = OrderStatus.CLOSED
        else:
            order.has_partial_refund = True
    await session.flush()


# ---------------------------------------------------------------------------
# Refund trigger
# ---------------------------------------------------------------------------
async def _trigger_refund(session: AsyncSession, aftersales: Aftersales) -> None:
    """Simulate refund + flip to completed_refunded + order-side link."""
    await refund_service.simulate_refund(session, aftersales)
    # refunding → completed_refunded is a system-driven step.
    await _transition(
        session,
        aftersales,
        AftersalesStatus.COMPLETED_REFUNDED,
        actor_type=AftersalesActorType.SYSTEM,
        actor_id=None,
        note="mock refund succeeded",
        allowed_from=[AftersalesStatus.REFUNDING],
    )
    aftersales.closed_at = _now()
    aftersales.close_reason = AftersalesCloseReason.COMPLETED
    await session.flush()
    await _order_side_link(session, aftersales)


# ---------------------------------------------------------------------------
# User: create
# ---------------------------------------------------------------------------
async def user_create(
    session: AsyncSession,
    user: User,
    order_id: int,
    payload: AftersalesCreateIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    settings = get_settings()

    order = await session.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise AppException(ErrorCode.ORDER_NOT_FOUND, "order not found")

    # Order status must permit this aftersales type.
    allowed = _ORDER_STATUS_ALLOWED.get(payload.type, frozenset())
    if order.status not in allowed:
        raise AppException(
            ErrorCode.AFTERSALES_ORDER_TYPE_NOT_ALLOWED,
            f"order status '{order.status.value}' not allowed for type '{payload.type.value}'",
        )

    # One active aftersales per order.
    if await _has_active_aftersales(session, order.id):
        raise AppException(
            ErrorCode.AFTERSALES_ORDER_HAS_ACTIVE,
            "order already has an active aftersales case",
        )

    # Validate items + refund cap.
    lines = await _validate_items(session, order, payload.items, payload.refund_amount_cents)

    now = _now()
    review_deadline = now + timedelta(hours=settings.MERCHANT_REVIEW_TIMEOUT_HOURS)

    # Risk assessment — if flagged, auto-escalate.
    risk_flagged = await risk_service.assess_aftersales_request(session, user)

    row = Aftersales(
        aftersales_no="pending",
        order_id=order.id,
        user_id=user.id,
        shop_id=order.shop_id,
        type=payload.type,
        status=AftersalesStatus.PENDING_MERCHANT_REVIEW,
        reason_category=payload.reason_category,
        reason_note=payload.reason_note,
        refund_amount_cents=payload.refund_amount_cents,
        merchant_review_deadline=review_deadline,
    )
    if risk_flagged:
        row.status = AftersalesStatus.ADMIN_ARBITRATING
        row.escalation_reason = AftersalesEscalationReason.RISK_FLAGGED
        row.escalated_at = now

    await _insert_aftersales_with_unique_no(session, row)

    # aftersales_items.
    for oi, qty, subtotal in lines:
        session.add(
            AftersalesItem(
                aftersales_id=row.id,
                order_item_id=oi.id,
                quantity=qty,
                refund_amount_cents=subtotal,
            )
        )
    await session.flush()

    # Initial evidences.
    await _write_evidences(
        session,
        row,
        keys=payload.evidence_image_keys,
        stage=AftersalesEvidenceStage.APPLY,
        uploader_type=AftersalesEvidenceUploaderType.USER,
        uploader_id=user.id,
    )

    # Initial history row.
    await _write_history(
        session,
        row,
        from_status=None,
        to_status=row.status.value,
        actor_type=AftersalesActorType.USER,
        actor_id=user.id,
        note="created",
    )
    if risk_flagged:
        await _write_message(
            session,
            row,
            sender_type=AftersalesMessageSenderType.SYSTEM,
            sender_id=None,
            kind=AftersalesMessageKind.SYSTEM_NOTICE,
            content="risk flagged — auto escalated to platform arbitration",
        )

    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.aftersales.create",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"order_id": order.id, "type": payload.type.value},
    )
    await _notify_aftersales_event(session, row, event="created")
    if risk_flagged:
        await _notify_aftersales_event(session, row, event="escalated")
    return await _serialize_detail(session, row)


# ---------------------------------------------------------------------------
# User: list / detail / cancel / submit-tracking / confirm-exchange / nudge /
# appeal / add-evidence
# ---------------------------------------------------------------------------
def _split_status_multi(value: str | None) -> list[AftersalesStatus] | None:
    if not value:
        return None
    out: list[AftersalesStatus] = []
    for raw in value.split(","):
        token = raw.strip()
        if not token:
            continue
        try:
            out.append(AftersalesStatus(token))
        except ValueError as exc:
            raise AppException(ErrorCode.VALIDATION_ERROR, f"unknown status '{token}'") from exc
    return out or None


def _split_type_multi(value: str | None) -> list[AftersalesType] | None:
    if not value:
        return None
    out: list[AftersalesType] = []
    for raw in value.split(","):
        token = raw.strip()
        if not token:
            continue
        try:
            out.append(AftersalesType(token))
        except ValueError as exc:
            raise AppException(ErrorCode.VALIDATION_ERROR, f"unknown type '{token}'") from exc
    return out or None


async def _paginate(
    session: AsyncSession,
    stmt_base: Any,
    stmt_count: Any,
    *,
    page: int,
    size: int,
    order_by: Any = None,
) -> tuple[list[Aftersales], int]:
    total = int((await session.execute(stmt_count)).scalar_one())
    ob = order_by if order_by is not None else Aftersales.created_at.desc()
    rows_stmt = stmt_base.order_by(ob, Aftersales.id.desc()).offset((page - 1) * size).limit(size)
    rows = list((await session.execute(rows_stmt)).scalars().all())
    return rows, total


async def user_list(
    session: AsyncSession,
    user: User,
    *,
    status_filter: str | None,
    type_filter: str | None,
    keyword: str | None,
    page: int,
    size: int,
) -> tuple[list[AftersalesListItemOut], int]:
    where = [Aftersales.user_id == user.id, Aftersales.deleted_at.is_(None)]
    statuses = _split_status_multi(status_filter)
    if statuses:
        where.append(Aftersales.status.in_(statuses))
    types = _split_type_multi(type_filter)
    if types:
        where.append(Aftersales.type.in_(types))
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append(
            or_(
                Aftersales.aftersales_no.ilike(kw),
                Aftersales.order_id.in_(select(Order.id).where(Order.order_no.ilike(kw))),
            )
        )
    stmt = select(Aftersales).where(and_(*where))
    stmt_count = select(func.count(Aftersales.id)).where(and_(*where))
    rows, total = await _paginate(session, stmt, stmt_count, page=page, size=size)
    return _serialize_list(rows), total


async def user_get_detail(
    session: AsyncSession, user: User, aftersales_id: int
) -> AftersalesDetailOut:
    row = await _load_for_user(session, user, aftersales_id)
    return await _serialize_detail(session, row)


async def user_cancel(
    session: AsyncSession,
    user: User,
    aftersales_id: int,
    cancel_note: str | None,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_user(session, user, aftersales_id)
    if row.status == AftersalesStatus.ADMIN_ARBITRATING:
        raise AppException(
            ErrorCode.AFTERSALES_ARBITRATING_NOT_CANCELABLE,
            "case is in arbitration and cannot be cancelled by user",
        )
    await _transition(
        session,
        row,
        AftersalesStatus.USER_CANCELLED,
        actor_type=AftersalesActorType.USER,
        actor_id=user.id,
        note=cancel_note,
        allowed_from=[
            AftersalesStatus.PENDING_MERCHANT_REVIEW,
            AftersalesStatus.MERCHANT_AGREED_WAITING_RETURN,
            AftersalesStatus.MERCHANT_REJECTED,
        ],
    )
    row.closed_at = _now()
    row.close_reason = AftersalesCloseReason.USER_CANCELLED
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.aftersales.cancel",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    return await _serialize_detail(session, row)


async def user_submit_tracking(
    session: AsyncSession,
    user: User,
    aftersales_id: int,
    payload: AftersalesSubmitTrackingIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_user(session, user, aftersales_id)
    if row.status != AftersalesStatus.MERCHANT_AGREED_WAITING_RETURN:
        raise AppException(
            ErrorCode.AFTERSALES_RETURN_NOT_AGREED,
            "case has not been agreed for return yet",
        )
    if row.return_tracking_no:
        raise AppException(
            ErrorCode.AFTERSALES_TRACKING_ALREADY_SUBMITTED,
            "tracking already submitted",
        )
    settings = get_settings()
    now = _now()
    row.return_carrier = payload.carrier
    row.return_tracking_no = payload.tracking_no
    row.return_shipped_at = now
    row.merchant_receive_deadline = now + timedelta(days=settings.MERCHANT_RECEIVE_TIMEOUT_DAYS)
    await _transition(
        session,
        row,
        AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE,
        actor_type=AftersalesActorType.USER,
        actor_id=user.id,
        note=f"carrier={payload.carrier} tracking={payload.tracking_no}",
        allowed_from=[AftersalesStatus.MERCHANT_AGREED_WAITING_RETURN],
    )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.aftersales.submit_tracking",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"carrier": payload.carrier, "tracking_no": payload.tracking_no},
    )
    return await _serialize_detail(session, row)


async def user_confirm_exchange(
    session: AsyncSession,
    user: User,
    aftersales_id: int,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_user(session, user, aftersales_id)
    await _transition(
        session,
        row,
        AftersalesStatus.COMPLETED_EXCHANGED,
        actor_type=AftersalesActorType.USER,
        actor_id=user.id,
        note="user confirmed exchange",
        allowed_from=[AftersalesStatus.EXCHANGE_SHIPPED_WAITING_RECEIVE],
    )
    now = _now()
    row.exchange_confirmed_at = now
    row.closed_at = now
    row.close_reason = AftersalesCloseReason.COMPLETED
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.aftersales.confirm_exchange",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    return await _serialize_detail(session, row)


async def user_nudge(
    session: AsyncSession,
    user: User,
    aftersales_id: int,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesNudgeOut:
    settings = get_settings()
    row = await _load_for_user(session, user, aftersales_id)
    if row.status != AftersalesStatus.PENDING_MERCHANT_REVIEW:
        raise AppException(
            ErrorCode.AFTERSALES_STATUS_INVALID_FOR_ACTION,
            "nudge only allowed while pending merchant review",
        )
    # 24h rate-limit: at most NUDGE_MAX_PER_DAY.
    day_ago = _now() - timedelta(hours=24)
    recent_stmt = select(func.count(AftersalesMessage.id)).where(
        AftersalesMessage.aftersales_id == row.id,
        AftersalesMessage.kind == AftersalesMessageKind.NUDGE,
        AftersalesMessage.created_at >= day_ago,
    )
    recent = int((await session.execute(recent_stmt)).scalar_one())
    if recent >= settings.NUDGE_MAX_PER_DAY:
        raise AppException(
            ErrorCode.RATE_LIMITED,
            f"nudge rate-limit reached ({settings.NUDGE_MAX_PER_DAY}/24h)",
        )
    now = _now()
    row.nudge_count += 1
    row.last_nudged_at = now
    await _write_message(
        session,
        row,
        sender_type=AftersalesMessageSenderType.USER,
        sender_id=user.id,
        kind=AftersalesMessageKind.NUDGE,
        content="user nudged",
    )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.aftersales.nudge",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    await session.refresh(row)
    return AftersalesNudgeOut(
        nudge_count=row.nudge_count,
        last_nudged_at=row.last_nudged_at or now,
    )


async def user_appeal(
    session: AsyncSession,
    user: User,
    aftersales_id: int,
    payload: AftersalesAppealIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_user(session, user, aftersales_id)
    if row.status == AftersalesStatus.ADMIN_ARBITRATING:
        raise AppException(
            ErrorCode.AFTERSALES_ARBITRATING_NOT_CANCELABLE,
            "case already in arbitration",
        )
    if row.appeal_count >= 1:
        raise AppException(
            ErrorCode.AFTERSALES_STATUS_INVALID_FOR_ACTION,
            "appeal already used",
        )
    now = _now()
    await _transition(
        session,
        row,
        AftersalesStatus.ADMIN_ARBITRATING,
        actor_type=AftersalesActorType.USER,
        actor_id=user.id,
        note="user appeal",
        allowed_from=[AftersalesStatus.MERCHANT_REJECTED],
    )
    row.escalation_reason = AftersalesEscalationReason.USER_APPEAL
    row.escalated_at = now
    row.appeal_count += 1
    await _write_message(
        session,
        row,
        sender_type=AftersalesMessageSenderType.USER,
        sender_id=user.id,
        kind=AftersalesMessageKind.APPEAL,
        content=payload.reason,
    )
    await _write_evidences(
        session,
        row,
        keys=payload.evidence_image_keys,
        stage=AftersalesEvidenceStage.APPEAL,
        uploader_type=AftersalesEvidenceUploaderType.USER,
        uploader_id=user.id,
    )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.aftersales.appeal",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    return await _serialize_detail(session, row)


async def user_add_evidence(
    session: AsyncSession,
    user: User,
    aftersales_id: int,
    payload: AftersalesEvidenceIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_user(session, user, aftersales_id)
    await _write_evidences(
        session,
        row,
        keys=[payload.image_key],
        stage=payload.stage,
        uploader_type=AftersalesEvidenceUploaderType.USER,
        uploader_id=user.id,
    )
    if payload.note:
        # Persist note on the just-inserted row (most-recent match).
        stmt = (
            select(AftersalesEvidence)
            .where(
                AftersalesEvidence.aftersales_id == row.id,
                AftersalesEvidence.stage == payload.stage,
                AftersalesEvidence.image_url == payload.image_key,
            )
            .order_by(AftersalesEvidence.id.desc())
            .limit(1)
        )
        latest = (await session.execute(stmt)).scalar_one_or_none()
        if latest is not None:
            latest.note = payload.note
            await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.USER,
        actor_id=user.id,
        action="user.aftersales.add_evidence",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"stage": payload.stage.value},
    )
    return await _serialize_detail(session, row)


# ---------------------------------------------------------------------------
# Merchant: list / detail / approve / reject / confirm-received /
# refuse-receive / ship-exchange / note
# ---------------------------------------------------------------------------
async def merchant_list(
    session: AsyncSession,
    account: MerchantAccount,
    *,
    status_filter: str | None,
    type_filter: str | None,
    overdue_soon: bool | None,
    keyword: str | None,
    page: int,
    size: int,
) -> tuple[list[AftersalesListItemOut], int]:
    where = [Aftersales.shop_id == account.shop_id, Aftersales.deleted_at.is_(None)]
    statuses = _split_status_multi(status_filter)
    if statuses:
        where.append(Aftersales.status.in_(statuses))
    types = _split_type_multi(type_filter)
    if types:
        where.append(Aftersales.type.in_(types))
    if overdue_soon:
        soon = _now() + timedelta(hours=24)
        where.append(Aftersales.merchant_review_deadline < soon)
        where.append(Aftersales.status == AftersalesStatus.PENDING_MERCHANT_REVIEW)
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append(
            or_(
                Aftersales.aftersales_no.ilike(kw),
                Aftersales.order_id.in_(select(Order.id).where(Order.order_no.ilike(kw))),
            )
        )
    stmt = select(Aftersales).where(and_(*where))
    stmt_count = select(func.count(Aftersales.id)).where(and_(*where))
    rows, total = await _paginate(
        session,
        stmt,
        stmt_count,
        page=page,
        size=size,
        order_by=Aftersales.merchant_review_deadline.asc(),
    )
    return _serialize_list(rows), total


async def merchant_stats_summary(
    session: AsyncSession, account: MerchantAccount
) -> MerchantAftersalesStatsOut:
    """Build the merchant aftersales dashboard summary for one shop."""
    now = _now()
    soon = now + timedelta(hours=24)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async def _c(*conds: Any) -> int:
        stmt = select(func.count(Aftersales.id)).where(
            Aftersales.shop_id == account.shop_id,
            Aftersales.deleted_at.is_(None),
            *conds,
        )
        return int((await session.execute(stmt)).scalar_one())

    pending_review = await _c(Aftersales.status == AftersalesStatus.PENDING_MERCHANT_REVIEW)
    overdue_soon = await _c(
        Aftersales.status == AftersalesStatus.PENDING_MERCHANT_REVIEW,
        Aftersales.merchant_review_deadline < soon,
    )
    waiting_receive = await _c(Aftersales.status == AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE)
    waiting_ship = await _c(Aftersales.status == AftersalesStatus.MERCHANT_AGREED_WAITING_SHIP)
    completed_this_month = await _c(
        Aftersales.status.in_(
            [
                AftersalesStatus.COMPLETED_REFUNDED,
                AftersalesStatus.COMPLETED_EXCHANGED,
            ]
        ),
        Aftersales.closed_at.is_not(None),
        Aftersales.closed_at >= month_start,
    )
    return MerchantAftersalesStatsOut(
        pending_review_count=pending_review,
        overdue_soon_count=overdue_soon,
        waiting_receive_count=waiting_receive,
        waiting_ship_count=waiting_ship,
        completed_this_month_count=completed_this_month,
    )


async def merchant_get_detail(
    session: AsyncSession, account: MerchantAccount, aftersales_id: int
) -> AftersalesDetailOut:
    row = await _load_for_shop(session, account, aftersales_id)
    return await _serialize_detail(session, row)


async def merchant_approve(
    session: AsyncSession,
    account: MerchantAccount,
    aftersales_id: int,
    payload: AftersalesMerchantApproveIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    settings = get_settings()
    row = await _load_for_shop(session, account, aftersales_id)
    if payload.actual_refund_cents > row.refund_amount_cents:
        raise AppException(
            ErrorCode.AFTERSALES_REFUND_AMOUNT_EXCEEDS,
            "actual_refund_cents cannot exceed the requested amount",
        )
    now = _now()
    row.actual_refund_cents = payload.actual_refund_cents
    row.merchant_reviewed_at = now
    row.merchant_review_note = payload.review_note

    if row.type == AftersalesType.REFUND_ONLY:
        await _transition(
            session,
            row,
            AftersalesStatus.REFUNDING,
            actor_type=AftersalesActorType.MERCHANT,
            actor_id=account.id,
            note="merchant approved (refund_only)",
            allowed_from=[AftersalesStatus.PENDING_MERCHANT_REVIEW],
        )
        await _trigger_refund(session, row)
    else:
        if not payload.return_address:
            raise AppException(
                ErrorCode.VALIDATION_ERROR,
                "return_address required for return/exchange approval",
            )
        row.return_address = payload.return_address
        row.return_ship_deadline = now + timedelta(days=settings.USER_RETURN_TIMEOUT_DAYS)
        await _transition(
            session,
            row,
            AftersalesStatus.MERCHANT_AGREED_WAITING_RETURN,
            actor_type=AftersalesActorType.MERCHANT,
            actor_id=account.id,
            note="merchant approved (waiting return)",
            allowed_from=[AftersalesStatus.PENDING_MERCHANT_REVIEW],
        )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.MERCHANT,
        actor_id=account.id,
        action="merchant.aftersales.approve",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"actual_refund_cents": payload.actual_refund_cents},
    )
    await _notify_aftersales_event(session, row, event="merchant_approved")
    return await _serialize_detail(session, row)


async def merchant_reject(
    session: AsyncSession,
    account: MerchantAccount,
    aftersales_id: int,
    payload: AftersalesMerchantRejectIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_shop(session, account, aftersales_id)
    now = _now()
    row.merchant_reviewed_at = now
    row.merchant_review_note = payload.review_note
    await _transition(
        session,
        row,
        AftersalesStatus.MERCHANT_REJECTED,
        actor_type=AftersalesActorType.MERCHANT,
        actor_id=account.id,
        note=payload.review_note,
        allowed_from=[AftersalesStatus.PENDING_MERCHANT_REVIEW],
    )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.MERCHANT,
        actor_id=account.id,
        action="merchant.aftersales.reject",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    await _notify_aftersales_event(session, row, event="merchant_rejected")
    return await _serialize_detail(session, row)


async def merchant_confirm_received(
    session: AsyncSession,
    account: MerchantAccount,
    aftersales_id: int,
    payload: AftersalesConfirmReceiveIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_shop(session, account, aftersales_id)
    row.merchant_received_at = _now()
    await _write_evidences(
        session,
        row,
        keys=payload.evidence_image_keys,
        stage=AftersalesEvidenceStage.MERCHANT_RECEIVE,
        uploader_type=AftersalesEvidenceUploaderType.MERCHANT,
        uploader_id=account.id,
    )
    if row.type == AftersalesType.RETURN_REFUND:
        await _transition(
            session,
            row,
            AftersalesStatus.REFUNDING,
            actor_type=AftersalesActorType.MERCHANT,
            actor_id=account.id,
            note=payload.note or "merchant confirmed received",
            allowed_from=[AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE],
        )
        await _trigger_refund(session, row)
    else:  # EXCHANGE
        await _transition(
            session,
            row,
            AftersalesStatus.MERCHANT_AGREED_WAITING_SHIP,
            actor_type=AftersalesActorType.MERCHANT,
            actor_id=account.id,
            note=payload.note or "merchant confirmed received (exchange)",
            allowed_from=[AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE],
        )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.MERCHANT,
        actor_id=account.id,
        action="merchant.aftersales.confirm_received",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    return await _serialize_detail(session, row)


async def merchant_refuse_receive(
    session: AsyncSession,
    account: MerchantAccount,
    aftersales_id: int,
    payload: AftersalesRefuseReceiveIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_shop(session, account, aftersales_id)
    now = _now()
    row.merchant_refuse_receive = True
    row.merchant_refuse_note = payload.refuse_note
    await _write_evidences(
        session,
        row,
        keys=payload.evidence_image_keys,
        stage=AftersalesEvidenceStage.MERCHANT_RECEIVE,
        uploader_type=AftersalesEvidenceUploaderType.MERCHANT,
        uploader_id=account.id,
    )
    await _transition(
        session,
        row,
        AftersalesStatus.ADMIN_ARBITRATING,
        actor_type=AftersalesActorType.MERCHANT,
        actor_id=account.id,
        note=payload.refuse_note,
        allowed_from=[AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE],
    )
    row.escalation_reason = AftersalesEscalationReason.MERCHANT_REFUSE_RECEIVE
    row.escalated_at = now
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.MERCHANT,
        actor_id=account.id,
        action="merchant.aftersales.refuse_receive",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    await _notify_aftersales_event(session, row, event="escalated")
    return await _serialize_detail(session, row)


async def merchant_ship_exchange(
    session: AsyncSession,
    account: MerchantAccount,
    aftersales_id: int,
    payload: AftersalesShipExchangeIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    settings = get_settings()
    row = await _load_for_shop(session, account, aftersales_id)
    now = _now()
    row.exchange_carrier = payload.carrier
    row.exchange_tracking_no = payload.tracking_no
    row.exchange_shipped_at = now
    row.exchange_confirm_deadline = now + timedelta(days=settings.EXCHANGE_CONFIRM_TIMEOUT_DAYS)
    await _transition(
        session,
        row,
        AftersalesStatus.EXCHANGE_SHIPPED_WAITING_RECEIVE,
        actor_type=AftersalesActorType.MERCHANT,
        actor_id=account.id,
        note=f"exchange shipped carrier={payload.carrier} tracking={payload.tracking_no}",
        allowed_from=[AftersalesStatus.MERCHANT_AGREED_WAITING_SHIP],
    )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.MERCHANT,
        actor_id=account.id,
        action="merchant.aftersales.ship_exchange",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"carrier": payload.carrier, "tracking_no": payload.tracking_no},
    )
    return await _serialize_detail(session, row)


async def merchant_note(
    session: AsyncSession,
    account: MerchantAccount,
    aftersales_id: int,
    note: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load_for_shop(session, account, aftersales_id)
    row.merchant_review_note = note
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.MERCHANT,
        actor_id=account.id,
        action="merchant.aftersales.note",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    return await _serialize_detail(session, row)


# ---------------------------------------------------------------------------
# Admin: list / detail / take-over / resolve / force-refund / note /
# stats-overview
# ---------------------------------------------------------------------------
def _apply_admin_scope(where: list[Any], admin: AdminUser) -> list[Any]:
    """Constrain the query to what ``admin`` may see.

    ``CUSTOMER_SERVICE_AGENT`` only sees ``admin_arbitrating`` cases that
    are unclaimed or claimed by themselves; every other role sees all.
    """
    if aftersales_scope_for_admin(admin.role) == AftersalesScope.OWN_AND_UNCLAIMED:
        where.append(Aftersales.status == AftersalesStatus.ADMIN_ARBITRATING)
        where.append(
            or_(
                Aftersales.arbitrator_admin_id.is_(None),
                Aftersales.arbitrator_admin_id == admin.id,
            )
        )
    return where


async def admin_list(
    session: AsyncSession,
    admin: AdminUser,
    *,
    status_filter: str | None,
    type_filter: str | None,
    shop_id: int | None,
    user_id: int | None,
    escalation_reason: str | None,
    keyword: str | None,
    page: int,
    size: int,
) -> tuple[list[AftersalesListItemOut], int]:
    where: list[Any] = [Aftersales.deleted_at.is_(None)]
    where = _apply_admin_scope(where, admin)
    statuses = _split_status_multi(status_filter)
    if statuses:
        where.append(Aftersales.status.in_(statuses))
    types = _split_type_multi(type_filter)
    if types:
        where.append(Aftersales.type.in_(types))
    if shop_id is not None:
        where.append(Aftersales.shop_id == shop_id)
    if user_id is not None:
        where.append(Aftersales.user_id == user_id)
    if escalation_reason:
        try:
            reason = AftersalesEscalationReason(escalation_reason)
        except ValueError as exc:
            raise AppException(
                ErrorCode.VALIDATION_ERROR,
                f"unknown escalation_reason '{escalation_reason}'",
            ) from exc
        where.append(Aftersales.escalation_reason == reason)
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append(
            or_(
                Aftersales.aftersales_no.ilike(kw),
                Aftersales.order_id.in_(select(Order.id).where(Order.order_no.ilike(kw))),
            )
        )
    stmt = select(Aftersales).where(and_(*where))
    stmt_count = select(func.count(Aftersales.id)).where(and_(*where))
    rows, total = await _paginate(
        session,
        stmt,
        stmt_count,
        page=page,
        size=size,
        order_by=Aftersales.escalated_at.desc().nulls_last(),
    )
    return _serialize_list(rows), total


async def admin_get_detail(
    session: AsyncSession, admin: AdminUser, aftersales_id: int
) -> AftersalesDetailOut:
    row = await _load(session, aftersales_id)
    if aftersales_scope_for_admin(admin.role) == AftersalesScope.OWN_AND_UNCLAIMED:
        visible = row.status == AftersalesStatus.ADMIN_ARBITRATING and (
            row.arbitrator_admin_id is None or row.arbitrator_admin_id == admin.id
        )
        if not visible:
            raise AppException(
                ErrorCode.AFTERSALES_NOT_CLAIMED_BY_SELF,
                "case is outside your scope",
            )
    return await _serialize_detail(session, row)


async def admin_release(
    session: AsyncSession,
    admin: AdminUser,
    aftersales_id: int,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    """Put a claimed case back into the pool (CS lead / super).

    Route guard enforces ``admin:aftersales:manage``, so this is only
    reachable by roles that may reassign work.
    """
    row = await _load(session, aftersales_id)
    if row.status != AftersalesStatus.ADMIN_ARBITRATING:
        raise AppException(
            ErrorCode.AFTERSALES_NOT_ESCALATED,
            "case not in arbitration",
        )
    if row.arbitrated_at is not None:
        raise AppException(
            ErrorCode.AFTERSALES_ARBITRATION_ALREADY_DONE,
            "case already arbitrated",
        )
    if row.arbitrator_admin_id is None:
        raise AppException(
            ErrorCode.AFTERSALES_NOT_CLAIMED_BY_SELF,
            "case is unclaimed, nothing to release",
        )
    previous_owner = row.arbitrator_admin_id
    row.arbitrator_admin_id = None
    await _write_message(
        session,
        row,
        sender_type=AftersalesMessageSenderType.SYSTEM,
        sender_id=None,
        kind=AftersalesMessageKind.SYSTEM_NOTICE,
        content=f"case released to the pool by admin #{admin.id} (was #{previous_owner})",
    )
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=admin.id,
        action="admin.aftersales.release",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"previous_owner": previous_owner},
    )
    return await _serialize_detail(session, row)


async def admin_take_over(
    session: AsyncSession,
    admin: AdminUser,
    aftersales_id: int,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load(session, aftersales_id)
    if row.status != AftersalesStatus.ADMIN_ARBITRATING:
        raise AppException(
            ErrorCode.AFTERSALES_NOT_ESCALATED,
            "case not in arbitration",
        )
    if row.arbitrator_admin_id and row.arbitrator_admin_id != admin.id:
        # Not a hard error — signal to caller via message row.
        await _write_message(
            session,
            row,
            sender_type=AftersalesMessageSenderType.SYSTEM,
            sender_id=None,
            kind=AftersalesMessageKind.SYSTEM_NOTICE,
            content=f"admin #{admin.id} attempted to take over case already owned by #{row.arbitrator_admin_id}",
        )
    row.arbitrator_admin_id = admin.id
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=admin.id,
        action="admin.aftersales.take_over",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    return await _serialize_detail(session, row)


async def admin_resolve(
    session: AsyncSession,
    admin: AdminUser,
    aftersales_id: int,
    payload: AftersalesResolveIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load(session, aftersales_id)
    if row.status != AftersalesStatus.ADMIN_ARBITRATING:
        raise AppException(
            ErrorCode.AFTERSALES_NOT_ESCALATED,
            "case not in arbitration",
        )
    if row.arbitrated_at is not None:
        raise AppException(
            ErrorCode.AFTERSALES_ARBITRATION_ALREADY_DONE,
            "case already arbitrated",
        )
    now = _now()
    row.arbitrator_admin_id = admin.id
    row.arbitration_conclusion = payload.conclusion
    row.arbitration_outcome = payload.outcome
    row.arbitrated_at = now
    await _write_evidences(
        session,
        row,
        keys=payload.evidence_image_keys,
        stage=AftersalesEvidenceStage.ARBITRATION,
        uploader_type=AftersalesEvidenceUploaderType.ADMIN,
        uploader_id=admin.id,
    )

    if payload.outcome == AftersalesArbitrationOutcome.SIDE_WITH_MERCHANT:
        # No refund — close case as arbitration_closed.
        await _transition(
            session,
            row,
            AftersalesStatus.SYSTEM_CLOSED,
            actor_type=AftersalesActorType.ADMIN,
            actor_id=admin.id,
            note="arbitration: side_with_merchant",
            allowed_from=[AftersalesStatus.ADMIN_ARBITRATING],
        )
        row.closed_at = now
        row.close_reason = AftersalesCloseReason.ARBITRATION_CLOSED
        await session.flush()
    else:
        if payload.actual_refund_cents is None or payload.actual_refund_cents <= 0:
            raise AppException(
                ErrorCode.AFTERSALES_FORCE_REFUND_AMOUNT_INVALID,
                "actual_refund_cents required for user-side / partial verdicts",
            )
        row.actual_refund_cents = payload.actual_refund_cents
        await _transition(
            session,
            row,
            AftersalesStatus.REFUNDING,
            actor_type=AftersalesActorType.ADMIN,
            actor_id=admin.id,
            note=f"arbitration: {payload.outcome.value}",
            allowed_from=[AftersalesStatus.ADMIN_ARBITRATING],
        )
        await _trigger_refund(session, row)
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=admin.id,
        action="admin.aftersales.resolve",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"outcome": payload.outcome.value},
    )
    return await _serialize_detail(session, row)


async def admin_force_refund(
    session: AsyncSession,
    admin: AdminUser,
    aftersales_id: int,
    payload: AftersalesForceRefundIn,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load(session, aftersales_id)
    if row.status in FINAL_STATUSES:
        raise AppException(
            ErrorCode.AFTERSALES_STATUS_INVALID_FOR_ACTION,
            "case already in a final status",
        )
    if payload.amount_cents <= 0 or payload.amount_cents > row.refund_amount_cents * 2:
        # Guard against absurd values; contract §18003.
        raise AppException(
            ErrorCode.AFTERSALES_FORCE_REFUND_AMOUNT_INVALID,
            "amount_cents out of range",
        )
    row.actual_refund_cents = payload.amount_cents
    row.arbitrator_admin_id = admin.id
    now = _now()
    if row.escalated_at is None:
        row.escalated_at = now
        row.escalation_reason = AftersalesEscalationReason.MANUAL

    # Allow force-refund from any non-final status.
    non_final = [
        s for s in AftersalesStatus if s not in FINAL_STATUSES and s != AftersalesStatus.REFUNDING
    ]
    await _transition(
        session,
        row,
        AftersalesStatus.REFUNDING,
        actor_type=AftersalesActorType.ADMIN,
        actor_id=admin.id,
        note=f"admin force refund: {payload.note}",
        allowed_from=non_final,
    )
    await _trigger_refund(session, row)
    await session.flush()
    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=admin.id,
        action="admin.aftersales.force_refund",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
        extra={"amount_cents": payload.amount_cents, "note": payload.note},
    )
    return await _serialize_detail(session, row)


async def admin_note(
    session: AsyncSession,
    admin: AdminUser,
    aftersales_id: int,
    note: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AftersalesDetailOut:
    row = await _load(session, aftersales_id)
    await _write_message(
        session,
        row,
        sender_type=AftersalesMessageSenderType.ADMIN,
        sender_id=admin.id,
        kind=AftersalesMessageKind.REPLY,
        content=note,
    )
    await write_audit(
        session,
        actor_type=AuditActorType.ADMIN,
        actor_id=admin.id,
        action="admin.aftersales.note",
        target_type="aftersales",
        target_id=row.id,
        ip=ip,
        user_agent=user_agent,
    )
    return await _serialize_detail(session, row)


def _today_range() -> tuple[datetime, datetime]:
    now = _now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


async def admin_stats_overview(session: AsyncSession) -> AftersalesStatsOverviewOut:
    start, end = _today_range()

    async def _c(*conds: Any) -> int:
        stmt = select(func.count(Aftersales.id)).where(*conds)
        return int((await session.execute(stmt)).scalar_one())

    pending = await _c(
        Aftersales.deleted_at.is_(None),
        Aftersales.status == AftersalesStatus.PENDING_MERCHANT_REVIEW,
    )
    escalated_pending = await _c(
        Aftersales.deleted_at.is_(None),
        Aftersales.status == AftersalesStatus.ADMIN_ARBITRATING,
        Aftersales.arbitrator_admin_id.is_(None),
    )
    in_progress = await _c(
        Aftersales.deleted_at.is_(None),
        Aftersales.status.notin_(FINAL_STATUSES),
    )
    resolved_today = await _c(
        Aftersales.deleted_at.is_(None),
        Aftersales.closed_at.is_not(None),
        Aftersales.closed_at >= start,
        Aftersales.closed_at < end,
    )
    # avg resolution hours over all resolved cases
    stmt = select(Aftersales.created_at, Aftersales.closed_at).where(
        Aftersales.deleted_at.is_(None),
        Aftersales.closed_at.is_not(None),
    )
    rows = list((await session.execute(stmt)).all())
    if rows:
        deltas = [
            (
                (_as_aware(closed_at) or closed_at) - (_as_aware(created_at) or created_at)
            ).total_seconds()
            / 3600.0
            for created_at, closed_at in rows
        ]
        avg = sum(deltas) / len(deltas)
    else:
        avg = 0.0
    return AftersalesStatsOverviewOut(
        pending_review_count=pending,
        escalated_pending_count=escalated_pending,
        in_progress_count=in_progress,
        resolved_today_count=resolved_today,
        avg_resolution_hours=round(avg, 2),
    )


# ---------------------------------------------------------------------------
# Timeout scans (called by process_timeouts)
# ---------------------------------------------------------------------------
async def scan_merchant_review_timeouts(session: AsyncSession, batch: int = 100) -> int:
    """PENDING_MERCHANT_REVIEW past deadline → ADMIN_ARBITRATING (merchant_timeout)."""
    now = _now()
    stmt = (
        select(Aftersales)
        .where(
            Aftersales.status == AftersalesStatus.PENDING_MERCHANT_REVIEW,
            Aftersales.merchant_review_deadline < now,
        )
        .limit(batch)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    for row in rows:
        await _transition(
            session,
            row,
            AftersalesStatus.ADMIN_ARBITRATING,
            actor_type=AftersalesActorType.SYSTEM,
            actor_id=None,
            note="merchant review timeout",
            allowed_from=[AftersalesStatus.PENDING_MERCHANT_REVIEW],
        )
        row.escalated_at = now
        row.escalation_reason = AftersalesEscalationReason.MERCHANT_TIMEOUT
        await _write_message(
            session,
            row,
            sender_type=AftersalesMessageSenderType.SYSTEM,
            sender_id=None,
            kind=AftersalesMessageKind.SYSTEM_NOTICE,
            content="merchant review timeout → auto escalated",
        )
    return len(rows)


async def scan_user_return_timeouts(session: AsyncSession, batch: int = 100) -> int:
    """MERCHANT_AGREED_WAITING_RETURN past deadline → SYSTEM_CLOSED (user_ship_timeout)."""
    now = _now()
    stmt = (
        select(Aftersales)
        .where(
            Aftersales.status == AftersalesStatus.MERCHANT_AGREED_WAITING_RETURN,
            Aftersales.return_ship_deadline.is_not(None),
            Aftersales.return_ship_deadline < now,
        )
        .limit(batch)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    for row in rows:
        await _transition(
            session,
            row,
            AftersalesStatus.SYSTEM_CLOSED,
            actor_type=AftersalesActorType.SYSTEM,
            actor_id=None,
            note="user 7d return timeout",
            allowed_from=[AftersalesStatus.MERCHANT_AGREED_WAITING_RETURN],
        )
        row.closed_at = now
        row.close_reason = AftersalesCloseReason.USER_SHIP_TIMEOUT
        await _write_message(
            session,
            row,
            sender_type=AftersalesMessageSenderType.SYSTEM,
            sender_id=None,
            kind=AftersalesMessageKind.SYSTEM_NOTICE,
            content="user return-ship 7d timeout → case closed",
        )
    return len(rows)


async def scan_merchant_receive_timeouts(session: AsyncSession, batch: int = 100) -> int:
    """RETURN_SHIPPED_WAITING_RECEIVE past deadline → auto-confirm & continue."""
    now = _now()
    stmt = (
        select(Aftersales)
        .where(
            Aftersales.status == AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE,
            Aftersales.merchant_receive_deadline.is_not(None),
            Aftersales.merchant_receive_deadline < now,
        )
        .limit(batch)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    for row in rows:
        row.merchant_received_at = now
        if row.type == AftersalesType.RETURN_REFUND:
            await _transition(
                session,
                row,
                AftersalesStatus.REFUNDING,
                actor_type=AftersalesActorType.SYSTEM,
                actor_id=None,
                note="merchant receive 15d timeout → auto refund",
                allowed_from=[AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE],
            )
            await _trigger_refund(session, row)
        else:  # EXCHANGE
            await _transition(
                session,
                row,
                AftersalesStatus.MERCHANT_AGREED_WAITING_SHIP,
                actor_type=AftersalesActorType.SYSTEM,
                actor_id=None,
                note="merchant receive 15d timeout → auto confirm receive",
                allowed_from=[AftersalesStatus.RETURN_SHIPPED_WAITING_RECEIVE],
            )
        await _write_message(
            session,
            row,
            sender_type=AftersalesMessageSenderType.SYSTEM,
            sender_id=None,
            kind=AftersalesMessageKind.SYSTEM_NOTICE,
            content="merchant receive 15d timeout → auto confirmed",
        )
    return len(rows)


async def scan_exchange_confirm_timeouts(session: AsyncSession, batch: int = 100) -> int:
    """EXCHANGE_SHIPPED_WAITING_RECEIVE past deadline → COMPLETED_EXCHANGED."""
    now = _now()
    stmt = (
        select(Aftersales)
        .where(
            Aftersales.status == AftersalesStatus.EXCHANGE_SHIPPED_WAITING_RECEIVE,
            Aftersales.exchange_confirm_deadline.is_not(None),
            Aftersales.exchange_confirm_deadline < now,
        )
        .limit(batch)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    for row in rows:
        await _transition(
            session,
            row,
            AftersalesStatus.COMPLETED_EXCHANGED,
            actor_type=AftersalesActorType.SYSTEM,
            actor_id=None,
            note="exchange 15d auto-confirm",
            allowed_from=[AftersalesStatus.EXCHANGE_SHIPPED_WAITING_RECEIVE],
        )
        row.exchange_confirmed_at = now
        row.closed_at = now
        row.close_reason = AftersalesCloseReason.AUTO_CONFIRMED
        await _write_message(
            session,
            row,
            sender_type=AftersalesMessageSenderType.SYSTEM,
            sender_id=None,
            kind=AftersalesMessageKind.SYSTEM_NOTICE,
            content="exchange 15d auto-confirmed",
        )
    return len(rows)


# Assignments to satisfy Ruff (unused args in _validate_items reserved for future)
_ = AftersalesReasonCategory  # keep import from being flagged
_ = AftersalesEvidence


__all__ = [
    "FINAL_STATUSES",
    "admin_force_refund",
    "admin_get_detail",
    "admin_list",
    "admin_note",
    "admin_release",
    "admin_resolve",
    "admin_stats_overview",
    "admin_take_over",
    "merchant_approve",
    "merchant_confirm_received",
    "merchant_get_detail",
    "merchant_list",
    "merchant_note",
    "merchant_refuse_receive",
    "merchant_reject",
    "merchant_ship_exchange",
    "merchant_stats_summary",
    "scan_exchange_confirm_timeouts",
    "scan_merchant_receive_timeouts",
    "scan_merchant_review_timeouts",
    "scan_user_return_timeouts",
    "user_add_evidence",
    "user_appeal",
    "user_cancel",
    "user_confirm_exchange",
    "user_create",
    "user_get_detail",
    "user_list",
    "user_nudge",
    "user_submit_tracking",
]
