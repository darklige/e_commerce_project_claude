"""Application error codes, exception type, and FastAPI handlers.

All handlers emit the unified ``{code, message, data}`` envelope defined
in the API contract §1. Business error codes are the 4-digit integers
in §2 (see :class:`ErrorCode`).
"""

from __future__ import annotations

import enum
import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorCode(int, enum.Enum):
    """Business error codes (contract §2). ``0`` = success."""

    OK = 0

    # 1xxx — auth & session
    UNAUTHENTICATED = 1001
    TOKEN_EXPIRED = 1002
    BAD_CREDENTIALS = 1003
    ACCOUNT_DISABLED = 1004
    INVALID_REFRESH_TOKEN = 1005
    INVALID_CAPTCHA = 1010
    PERMISSION_DENIED = 1020

    # 2xxx — user profile
    USER_NOT_FOUND = 2001
    PHONE_ALREADY_REGISTERED = 2002
    EMAIL_ALREADY_REGISTERED = 2003
    OLD_PASSWORD_MISMATCH = 2010

    # 3xxx — merchant & onboarding
    APPLICATION_ALREADY_PENDING = 3001
    ALREADY_A_MERCHANT = 3002
    APPLICATION_NOT_FOUND = 3003
    APPLICATION_STATUS_INVALID_FOR_ACTION = 3004
    MERCHANT_ACCOUNT_FROZEN = 3010

    # 4xxx — admin
    ADMIN_NOT_FOUND = 4001
    ADMIN_PERMISSION_DENIED = 4020
    # Phase 6 — admin account management
    ADMIN_USERNAME_TAKEN = 4002
    ADMIN_CANNOT_OPERATE_SELF = 4003
    ADMIN_PASSWORD_WEAK = 4004
    ADMIN_LAST_SUPER_ADMIN = 4005

    # 5xxx — validation & generic
    VALIDATION_ERROR = 5001
    RESOURCE_NOT_FOUND = 5002
    RATE_LIMITED = 5003
    IDEMPOTENCY_KEY_MISSING = 5010

    # 6xxx — category / brand (Phase 2)
    CATEGORY_NOT_FOUND = 6001
    CATEGORY_IN_USE = 6002
    CATEGORY_LEVEL_EXCEEDED = 6003
    BRAND_NOT_FOUND = 6011
    BRAND_SLUG_CONFLICT = 6012

    # 7xxx — SPU (Phase 2)
    SPU_NOT_FOUND = 7001
    SPU_PERMISSION_DENIED = 7002
    SPU_STATUS_INVALID_FOR_ACTION = 7003
    SPU_REQUIRES_AT_LEAST_ONE_SKU = 7004
    SPU_ALREADY_OFF_SHELF = 7005

    # 8xxx — SKU (Phase 2)
    SKU_NOT_FOUND = 8001
    SKU_CODE_CONFLICT = 8002
    SKU_STOCK_INSUFFICIENT = 8003
    SKU_SPU_NOT_APPROVED = 8004

    # 95xx — inventory (Phase 2; §2 decision)
    INVENTORY_LOG_NOT_FOUND = 9501
    INVENTORY_DELTA_INVALID = 9502
    INVENTORY_REASON_INVALID = 9503
    INVENTORY_STOCK_INSUFFICIENT = 9504

    # 9xxx — server
    INTERNAL_ERROR = 9000

    # 10xxx — file upload (Phase 2)
    UPLOAD_CONTENT_TYPE_NOT_ALLOWED = 10001
    UPLOAD_FILE_TOO_LARGE = 10002
    UPLOAD_PRESIGN_FAILED = 10003

    # 11xxx — address book (Phase 3)
    ADDRESS_NOT_FOUND = 11001
    ADDRESS_PERMISSION_DENIED = 11002
    ADDRESS_LIMIT_EXCEEDED = 11003

    # 12xxx — cart (Phase 3)
    CART_ITEM_NOT_FOUND = 12001
    CART_SKU_INVALID = 12002
    CART_QUANTITY_EXCEEDS_STOCK = 12003
    CART_QUANTITY_EXCEEDS_LIMIT = 12004
    CART_LIMIT_EXCEEDED = 12005

    # 13xxx — order (Phase 3)
    ORDER_NOT_FOUND = 13001
    ORDER_PERMISSION_DENIED = 13002
    ORDER_STATUS_INVALID_FOR_ACTION = 13003
    ORDER_STOCK_INSUFFICIENT = 13004
    ORDER_CART_EMPTY = 13005
    ORDER_NO_VALID_ITEMS = 13006
    ORDER_ADDRESS_INVALID = 13007
    ORDER_PAYMENT_DEADLINE_PASSED = 13008
    ORDER_IDEMPOTENCY_CONFLICT = 13009
    ORDER_TRACKING_NO_INVALID = 13010
    ORDER_ALREADY_CANCELLED = 13011

    # 14xxx — payment (Phase 3)
    PAYMENT_SESSION_NOT_FOUND = 14001
    PAYMENT_SESSION_NOT_PENDING = 14002
    PAYMENT_CHANNEL_UNSUPPORTED = 14003
    PAYMENT_MOCK_FAILED = 14004

    # 15xxx — aftersales (Phase 4)
    AFTERSALES_NOT_FOUND = 15001
    AFTERSALES_PERMISSION_DENIED = 15002
    AFTERSALES_STATUS_INVALID_FOR_ACTION = 15003
    AFTERSALES_ORDER_TYPE_NOT_ALLOWED = 15004
    AFTERSALES_ORDER_HAS_ACTIVE = 15005
    AFTERSALES_REFUND_AMOUNT_EXCEEDS = 15006
    AFTERSALES_TYPE_ORDER_STATUS_MISMATCH = 15007
    AFTERSALES_NO_ITEMS_SELECTED = 15008
    AFTERSALES_ARBITRATING_NOT_CANCELABLE = 15009

    # 16xxx — aftersales evidence (Phase 4)
    AFTERSALES_EVIDENCE_LIMIT_EXCEEDED = 16001
    AFTERSALES_EVIDENCE_MISMATCH_CASE = 16002

    # 17xxx — aftersales return-tracking (Phase 4)
    AFTERSALES_TRACKING_NO_INVALID = 17001
    AFTERSALES_RETURN_NOT_AGREED = 17002
    AFTERSALES_TRACKING_ALREADY_SUBMITTED = 17003

    # 18xxx — aftersales arbitration (Phase 4)
    AFTERSALES_NOT_ESCALATED = 18001
    AFTERSALES_ARBITRATION_ALREADY_DONE = 18002
    AFTERSALES_FORCE_REFUND_AMOUNT_INVALID = 18003
    # Phase 6 — arbitration ownership / data scope
    AFTERSALES_CLAIMED_BY_OTHER = 18004
    AFTERSALES_NOT_CLAIMED_BY_SELF = 18005

    # 19xxx — reviews (Phase 5)
    REVIEW_NOT_FOUND = 19001
    REVIEW_PERMISSION_DENIED = 19002
    REVIEW_ORDER_NOT_REVIEWABLE = 19003
    REVIEW_EDIT_WINDOW_EXPIRED = 19004
    REVIEW_RATING_INVALID = 19005
    REVIEW_CONTENT_TOO_LONG = 19006
    REVIEW_IMAGES_LIMIT_EXCEEDED = 19007

    # 20xxx — review replies (Phase 5)
    REVIEW_REPLY_NOT_FOUND = 20001
    REVIEW_REPLY_ALREADY_EXISTS = 20002
    REVIEW_REPLY_PERMISSION_DENIED = 20003

    # 21xxx — review reports (Phase 5)
    REVIEW_REPORT_NOT_FOUND = 21001
    REVIEW_REPORT_ALREADY_EXISTS = 21002
    REVIEW_REPORT_REASON_INVALID = 21003

    # 22xxx — notifications (Phase 5)
    NOTIFICATION_NOT_FOUND = 22001
    NOTIFICATION_PERMISSION_DENIED = 22002

    # 23xxx — regions (Phase 5)
    REGION_CODE_INVALID = 23001
    REGION_CODE_MISMATCH = 23002


# ---------------------------------------------------------------------------
# Default HTTP status per error code
# ---------------------------------------------------------------------------
_DEFAULT_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.OK: status.HTTP_200_OK,
    ErrorCode.UNAUTHENTICATED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.BAD_CREDENTIALS: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ACCOUNT_DISABLED: status.HTTP_403_FORBIDDEN,
    ErrorCode.INVALID_REFRESH_TOKEN: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INVALID_CAPTCHA: status.HTTP_400_BAD_REQUEST,
    ErrorCode.PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.USER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.PHONE_ALREADY_REGISTERED: status.HTTP_409_CONFLICT,
    ErrorCode.EMAIL_ALREADY_REGISTERED: status.HTTP_409_CONFLICT,
    ErrorCode.OLD_PASSWORD_MISMATCH: status.HTTP_400_BAD_REQUEST,
    ErrorCode.APPLICATION_ALREADY_PENDING: status.HTTP_409_CONFLICT,
    ErrorCode.ALREADY_A_MERCHANT: status.HTTP_409_CONFLICT,
    ErrorCode.APPLICATION_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.APPLICATION_STATUS_INVALID_FOR_ACTION: status.HTTP_409_CONFLICT,
    ErrorCode.MERCHANT_ACCOUNT_FROZEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.ADMIN_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.ADMIN_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.ADMIN_USERNAME_TAKEN: status.HTTP_409_CONFLICT,
    ErrorCode.ADMIN_CANNOT_OPERATE_SELF: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ADMIN_PASSWORD_WEAK: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ADMIN_LAST_SUPER_ADMIN: status.HTTP_400_BAD_REQUEST,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.CATEGORY_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CATEGORY_IN_USE: status.HTTP_409_CONFLICT,
    ErrorCode.CATEGORY_LEVEL_EXCEEDED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.BRAND_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.BRAND_SLUG_CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.SPU_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.SPU_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.SPU_STATUS_INVALID_FOR_ACTION: status.HTTP_409_CONFLICT,
    ErrorCode.SPU_REQUIRES_AT_LEAST_ONE_SKU: status.HTTP_409_CONFLICT,
    ErrorCode.SPU_ALREADY_OFF_SHELF: status.HTTP_409_CONFLICT,
    ErrorCode.SKU_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.SKU_CODE_CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.SKU_STOCK_INSUFFICIENT: status.HTTP_409_CONFLICT,
    ErrorCode.SKU_SPU_NOT_APPROVED: status.HTTP_409_CONFLICT,
    ErrorCode.INVENTORY_LOG_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.INVENTORY_DELTA_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVENTORY_REASON_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVENTORY_STOCK_INSUFFICIENT: status.HTTP_409_CONFLICT,
    ErrorCode.UPLOAD_CONTENT_TYPE_NOT_ALLOWED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UPLOAD_FILE_TOO_LARGE: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UPLOAD_PRESIGN_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.ADDRESS_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.ADDRESS_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.ADDRESS_LIMIT_EXCEEDED: status.HTTP_409_CONFLICT,
    ErrorCode.CART_ITEM_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CART_SKU_INVALID: status.HTTP_409_CONFLICT,
    ErrorCode.CART_QUANTITY_EXCEEDS_STOCK: status.HTTP_409_CONFLICT,
    ErrorCode.CART_QUANTITY_EXCEEDS_LIMIT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.CART_LIMIT_EXCEEDED: status.HTTP_409_CONFLICT,
    ErrorCode.ORDER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.ORDER_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.ORDER_STATUS_INVALID_FOR_ACTION: status.HTTP_409_CONFLICT,
    ErrorCode.ORDER_STOCK_INSUFFICIENT: status.HTTP_409_CONFLICT,
    ErrorCode.ORDER_CART_EMPTY: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ORDER_NO_VALID_ITEMS: status.HTTP_409_CONFLICT,
    ErrorCode.ORDER_ADDRESS_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ORDER_PAYMENT_DEADLINE_PASSED: status.HTTP_409_CONFLICT,
    ErrorCode.ORDER_IDEMPOTENCY_CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.ORDER_TRACKING_NO_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.ORDER_ALREADY_CANCELLED: status.HTTP_409_CONFLICT,
    ErrorCode.PAYMENT_SESSION_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.PAYMENT_SESSION_NOT_PENDING: status.HTTP_409_CONFLICT,
    ErrorCode.PAYMENT_CHANNEL_UNSUPPORTED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.PAYMENT_MOCK_FAILED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.IDEMPOTENCY_KEY_MISSING: 422,
    ErrorCode.AFTERSALES_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.AFTERSALES_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.AFTERSALES_STATUS_INVALID_FOR_ACTION: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_ORDER_TYPE_NOT_ALLOWED: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_ORDER_HAS_ACTIVE: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_REFUND_AMOUNT_EXCEEDS: status.HTTP_400_BAD_REQUEST,
    ErrorCode.AFTERSALES_TYPE_ORDER_STATUS_MISMATCH: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_NO_ITEMS_SELECTED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.AFTERSALES_ARBITRATING_NOT_CANCELABLE: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_EVIDENCE_LIMIT_EXCEEDED: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_EVIDENCE_MISMATCH_CASE: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_TRACKING_NO_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.AFTERSALES_RETURN_NOT_AGREED: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_TRACKING_ALREADY_SUBMITTED: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_NOT_ESCALATED: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_ARBITRATION_ALREADY_DONE: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_FORCE_REFUND_AMOUNT_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.AFTERSALES_CLAIMED_BY_OTHER: status.HTTP_409_CONFLICT,
    ErrorCode.AFTERSALES_NOT_CLAIMED_BY_SELF: status.HTTP_403_FORBIDDEN,
    # Phase 5
    ErrorCode.REVIEW_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.REVIEW_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.REVIEW_ORDER_NOT_REVIEWABLE: status.HTTP_409_CONFLICT,
    ErrorCode.REVIEW_EDIT_WINDOW_EXPIRED: status.HTTP_409_CONFLICT,
    ErrorCode.REVIEW_RATING_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.REVIEW_CONTENT_TOO_LONG: status.HTTP_400_BAD_REQUEST,
    ErrorCode.REVIEW_IMAGES_LIMIT_EXCEEDED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.REVIEW_REPLY_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.REVIEW_REPLY_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.REVIEW_REPLY_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.REVIEW_REPORT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.REVIEW_REPORT_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.REVIEW_REPORT_REASON_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.NOTIFICATION_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.NOTIFICATION_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.REGION_CODE_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.REGION_CODE_MISMATCH: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


class AppException(Exception):
    """Business exception carrying an :class:`ErrorCode` and HTTP status."""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        *,
        http_status: int | None = None,
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message or code.name.lower().replace("_", " ")
        self.http_status = http_status or _DEFAULT_HTTP_STATUS.get(
            code, status.HTTP_400_BAD_REQUEST
        )
        self.data = data
        super().__init__(self.message)


def envelope(
    *,
    code: ErrorCode | int = ErrorCode.OK,
    message: str = "ok",
    data: Any = None,
) -> dict[str, Any]:
    """Build the standard ``{code, message, data}`` response body."""
    code_int = code.value if isinstance(code, ErrorCode) else int(code)
    return {"code": code_int, "message": message, "data": data}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
async def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=envelope(code=exc.code, message=exc.message, data=exc.data),
    )


async def _validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=envelope(
            code=ErrorCode.VALIDATION_ERROR,
            message="validation error",
            data={"errors": errors},
        ),
    )


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Map common HTTP statuses to closest business code so front-end
    # can rely on the envelope even for framework-raised exceptions.
    fallback = ErrorCode.INTERNAL_ERROR
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        fallback = ErrorCode.UNAUTHENTICATED
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        fallback = ErrorCode.PERMISSION_DENIED
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        fallback = ErrorCode.RESOURCE_NOT_FOUND
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        fallback = ErrorCode.RATE_LIMITED

    return JSONResponse(
        status_code=exc.status_code,
        content=envelope(code=fallback, message=str(exc.detail), data=None),
    )


async def _unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope(code=ErrorCode.INTERNAL_ERROR, message="internal error", data=None),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire all custom exception handlers onto the FastAPI app."""
    app.add_exception_handler(AppException, _app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        _validation_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        StarletteHTTPException,
        _http_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(Exception, _unhandled_exception_handler)


__all__ = [
    "AppException",
    "ErrorCode",
    "envelope",
    "register_exception_handlers",
]
