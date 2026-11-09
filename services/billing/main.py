import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import (
    get_database_url,
    get_jwt_algorithm,
    get_jwt_secret,
    get_xendit_callback_token,
    get_xendit_components_origins,
    get_xendit_secret_key,
)
logger = logging.getLogger(__name__)

PLAN_PRICING = {
    "Hobby": 0,
    "Pro": 99,
}

PAID_PLAN_NAMES = {"Pro"}
HOBBY_CALCULATION_LIMIT = 50

INTENT_STATUS_PENDING_PAYMENT = "pending_payment"
INTENT_STATUS_PAID = "paid"
INTENT_STATUS_SUPERSEDED = "superseded"
INTENT_STATUS_CANCELLED = "cancelled"


class Base(DeclarativeBase):
    pass


class SubscriptionORM(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    plan_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    xendit_plan_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    xendit_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    @property
    def expires_at(self) -> datetime | None:
        """Alias for backward-compatibility with tests expecting expires_at."""
        return self.current_period_end

    @expires_at.setter
    def expires_at(self, value: datetime | None) -> None:
        self.current_period_end = value


class InvoiceIntentORM(Base):
    __tablename__ = "invoice_intents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    xendit_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_name: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="PHP")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    components_sdk_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProTrialORM(Base):
    __tablename__ = "pro_trials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaymentHistoryORM(Base):
    __tablename__ = "payment_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subscription_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    xendit_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cycle_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="PHP")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    receipt_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class ProcessedWebhookORM(Base):
    __tablename__ = "processed_webhooks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class DailyUsageORM(Base):
    __tablename__ = "daily_usage"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    usage_date: Mapped[str] = mapped_column(String(10), primary_key=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UsageReservationORM(Base):
    __tablename__ = "usage_reservations"

    reservation_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    usage_date: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- Pydantic Schemas ---

class TrialStatus(BaseModel):
    eligible: bool
    is_active: bool
    days_remaining: int | None = None
    expires_at: str | None = None


class UsageStatus(BaseModel):
    used: int
    limit: int | None
    unlimited: bool
    next_reset_at: str


class BillingStatusResponse(BaseModel):
    plan_name: str
    status: str
    current_period_end: str | None = None
    expires_at: str | None = None
    current_period_start: str | None = None
    cancel_at_period_end: bool = False
    grace_period_deadline: str | None = None
    trial: TrialStatus
    usage: UsageStatus
    can_cancel: bool = False


class SubscribeRequest(BaseModel):
    # Allow Pro, and accept Standard/Premium for legacy compatibility by mapping them to Pro
    plan_name: str = Field(pattern="^(Pro|Standard|Premium)$")


class SubscribeResponse(BaseModel):
    components_sdk_key: str


class TrialStartResponse(BaseModel):
    status: str
    expires_at: str
    days_remaining: int


class PaymentRecord(BaseModel):
    id: str
    date: str
    amount: str
    raw_amount: int
    currency: str
    status: str
    description: str


class ReceiptResponse(BaseModel):
    receipt_id: str
    user_id: str
    amount: str
    currency: str
    status: str
    date: str
    description: str
    receipt_text: str


class UsageReserveResponse(BaseModel):
    allowed: bool
    unlimited: bool
    reservation_id: str | None = None
    remaining: int | None = None


class UsageActionRequest(BaseModel):
    reservation_id: str | None = None
    user_id: str | None = None


class UsageActionResponse(BaseModel):
    status: str


class XenditPaymentSessionResult(BaseModel):
    components_sdk_key: str
    payment_session_id: str | None = None
    currency: str = "PHP"


class XenditWebhookPayload(BaseModel):
    id: str | None = None
    external_id: str | None = None
    reference_id: str | None = None
    event: str | None = None
    status: str | None = None
    amount: float | None = None
    paid_amount: float | None = None
    currency: str | None = None
    paid_plan_name: str | None = None
    data: dict | None = None


class WebhookResponse(BaseModel):
    received: bool


_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


async def request_validation_exception_handler(_, __):
    return JSONResponse(status_code=400, content={"detail": "Malformed payload"})


def _to_iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _next_utc_reset_iso() -> str:
    now = datetime.now(UTC)
    tomorrow = now.date() + timedelta(days=1)
    reset_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=UTC)
    return reset_dt.isoformat().replace("+00:00", "Z")


def _session_factory_or_500() -> async_sessionmaker[AsyncSession]:
    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return _SESSION_FACTORY


def _to_reference_id(user_id: str) -> str:
    compact_user_id = user_id.replace("-", "")[:16]
    return f"upgrade_{compact_user_id}_{uuid4().hex[:32]}"


def _decode_user_id(authorization: str | None, x_user_id: str | None = None) -> str:
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    try:
        jwt_secret = get_jwt_secret()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured") from exc

    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[get_jwt_algorithm()])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user_id = payload.get("user_id") or payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=401, detail="Token missing user_id/sub")

    return user_id


async def _require_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> str:
    return _decode_user_id(authorization, x_user_id)


def _create_xendit_payment_session(*, reference_id: str, amount: int, description: str) -> XenditPaymentSessionResult:
    try:
        secret_key = get_xendit_secret_key()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        import xendit
        from xendit.exceptions import OpenApiException, XenditSdkException
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"xendit-python dependency missing: {exc.name}") from exc

    target_date = datetime.now(UTC) + timedelta(days=30)
    if target_date.day > 28:
        target_date = target_date.replace(day=28)
    anchor_date = target_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    payload = {
        "reference_id": reference_id,
        "session_type": "SUBSCRIPTION",
        "mode": "COMPONENTS",
        "amount": amount,
        "currency": "PHP",
        "country": "PH",
        "description": description,
        "customer": {
            "reference_id": reference_id,
            "type": "INDIVIDUAL",
            "individual_detail": {
                "given_names": "MaaS User",
            },
        },
        "subscription": {
            "immediate_payment": True,
            "failed_cycle_action": "RESUME",
            "schedule": {
                "interval": "MONTH",
                "interval_count": 1,
                "anchor_date": anchor_date,
                "retry_interval": "DAY",
                "retry_interval_count": 2,
                "total_retry": 3,
            },
        },
        "components_configuration": {
            "origins": get_xendit_components_origins(),
        },
    }

    try:
        xendit.set_api_key(secret_key)
        client = xendit.ApiClient()

        response_data = client.call_api(
            "/sessions",
            "POST",
            body=payload,
            _return_http_data_only=False,
            _preload_content=False,
        )

        if response_data is None:
            raise HTTPException(status_code=502, detail="Xendit session response is empty")

        raw_response: Any
        data_attr = getattr(response_data, "data", None)
        if data_attr is not None:
            raw_response = data_attr
        else:
            read_fn = getattr(response_data, "read", None)
            if callable(read_fn):
                raw_response = read_fn()
            else:
                raw_response = response_data

        response_text = raw_response.decode("utf-8") if isinstance(raw_response, (bytes, bytearray)) else str(raw_response)
        response_payload = cast(dict[str, Any], json.loads(response_text))
        logger.info(
            "Created Xendit subscription payment session reference_id=%s session_id=%s origins=%s",
            reference_id,
            response_payload.get("payment_session_id") or response_payload.get("id"),
            payload["components_configuration"]["origins"],
        )

        components_sdk_key = response_payload.get("components_sdk_key")
        if not isinstance(components_sdk_key, str) or not components_sdk_key:
            raise HTTPException(status_code=502, detail="Xendit payment session response missing components_sdk_key")

        payment_session_id = response_payload.get("payment_session_id") or response_payload.get("id")
        payment_session_currency = response_payload.get("currency")

        return XenditPaymentSessionResult(
            components_sdk_key=components_sdk_key,
            payment_session_id=payment_session_id if isinstance(payment_session_id, str) and payment_session_id else None,
            currency=payment_session_currency if isinstance(payment_session_currency, str) and payment_session_currency else "PHP",
        )
    except HTTPException:
        raise
    except XenditSdkException as exc:
        logger.exception("Xendit SDK error while creating subscription payment session")
        message = getattr(exc, "errorMessage", None) or str(exc) or "Xendit payment session creation failed"
        raise HTTPException(status_code=502, detail=message) from exc
    except OpenApiException as exc:
        logger.exception("Xendit API error while creating subscription payment session")
        raise HTTPException(status_code=502, detail="Xendit payment session creation failed") from exc
    except Exception as exc:
        logger.exception("Failed to create Xendit subscription payment session")
        raise HTTPException(status_code=502, detail="Failed to create payment session") from exc


async def _get_effective_state(session: AsyncSession, user_id: str) -> dict[str, Any]:
    now = datetime.now(UTC)

    # 1. Fetch subscription
    sub_res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
    subscription = sub_res.scalar_one_or_none()

    # 2. Fetch trial
    trial_res = await session.execute(select(ProTrialORM).where(ProTrialORM.user_id == user_id))
    trial = trial_res.scalar_one_or_none()

    # Evaluate subscription state transitions
    has_active_paid_pro = False
    has_grace_pro = False

    if subscription is not None:
        sub_period_end = _as_utc(subscription.current_period_end) if subscription.current_period_end else None
        sub_grace_deadline = _as_utc(subscription.grace_period_deadline) if subscription.grace_period_deadline else None

        if subscription.status == "active":
            if subscription.cancel_at_period_end and sub_period_end and now > sub_period_end:
                subscription.status = "canceled"
                subscription.updated_at = now
            else:
                has_active_paid_pro = True
        elif subscription.status == "past_due":
            if sub_grace_deadline and now <= sub_grace_deadline:
                # Still within 7-day grace period: retains Pro access!
                has_grace_pro = True
            elif sub_grace_deadline and now > sub_grace_deadline:
                # Grace period expired: downgrade to expired/Hobby
                subscription.status = "expired"
                subscription.updated_at = now

    # Evaluate trial state
    is_trial_active = False
    trial_days_remaining = None
    trial_expires_at = None

    if trial is not None:
        t_expires = _as_utc(trial.expires_at)
        if now < t_expires:
            is_trial_active = True
            remaining_delta = t_expires - now
            trial_days_remaining = max(1, remaining_delta.days + (1 if remaining_delta.seconds > 0 else 0))
            trial_expires_at = _to_iso_z(trial.expires_at)

    trial_eligible = (trial is None) and (not has_active_paid_pro)

    # Effective Pro entitlement
    is_effective_pro = has_active_paid_pro or has_grace_pro or is_trial_active

    # Determine plan name & status
    if has_active_paid_pro:
        plan_name = "Pro"
        status = subscription.status  # "active"
    elif has_grace_pro:
        plan_name = "Pro"
        status = "past_due"
    elif subscription and subscription.status == "pending_payment":
        plan_name = "Pro"
        status = "pending_payment"
    elif is_trial_active:
        plan_name = "Pro"
        status = "active"
    else:
        plan_name = "Hobby"
        status = "active" if subscription is None or subscription.status in ("canceled", "expired") else subscription.status

    can_cancel = bool(subscription and subscription.status == "active" and not subscription.cancel_at_period_end)

    return {
        "subscription": subscription,
        "trial": trial,
        "plan_name": plan_name,
        "status": status,
        "is_pro": is_effective_pro,
        "trial_info": TrialStatus(
            eligible=trial_eligible,
            is_active=is_trial_active,
            days_remaining=trial_days_remaining,
            expires_at=trial_expires_at,
        ),
        "can_cancel": can_cancel,
    }


async def _get_today_usage(session: AsyncSession, user_id: str, is_pro: bool) -> UsageStatus:
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    result = await session.execute(
        select(DailyUsageORM).where(
            DailyUsageORM.user_id == user_id,
            DailyUsageORM.usage_date == today_str,
        )
    )
    usage_row = result.scalar_one_or_none()
    used_count = usage_row.used_count if usage_row else 0

    return UsageStatus(
        used=used_count,
        limit=None if is_pro else HOBBY_CALCULATION_LIMIT,
        unlimited=is_pro,
        next_reset_at=_next_utc_reset_iso(),
    )


# --- Lifespan ---

@asynccontextmanager
async def lifespan(_: FastAPI):
    global _SESSION_FACTORY

    database_url = get_database_url()
    engine = None

    if database_url:
        engine = create_async_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        _SESSION_FACTORY = session_factory
    else:
        logger.warning("DATABASE_URL is not configured; billing endpoints requiring DB will return 500")
        _SESSION_FACTORY = None

    try:
        yield
    finally:
        _SESSION_FACTORY = None
        if engine is not None:
            await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)


# --- Public Billing Endpoints ---

@app.get("/api/v1/billing/status", response_model=BillingStatusResponse)
async def billing_status(user_id: str = Depends(_require_user_id)) -> BillingStatusResponse:
    session_factory = _session_factory_or_500()

    async with session_factory() as session:
        state = await _get_effective_state(session, user_id)
        usage = await _get_today_usage(session, user_id, is_pro=state["is_pro"])
        await session.commit()

        sub = state["subscription"]
        period_end = _to_iso_z(sub.current_period_end) if sub else None
        period_start = _to_iso_z(sub.current_period_start) if sub else None
        cancel_at_period_end = sub.cancel_at_period_end if sub else False
        grace_deadline = _to_iso_z(sub.grace_period_deadline) if sub else None

        return BillingStatusResponse(
            plan_name=state["plan_name"],
            status=state["status"],
            current_period_end=period_end,
            expires_at=period_end,
            current_period_start=period_start,
            cancel_at_period_end=cancel_at_period_end,
            grace_period_deadline=grace_deadline,
            trial=state["trial_info"],
            usage=usage,
            can_cancel=state["can_cancel"],
        )


@app.post("/api/v1/billing/subscribe", response_model=SubscribeResponse)
async def billing_subscribe(payload: SubscribeRequest, user_id: str = Depends(_require_user_id)) -> SubscribeResponse:
    session_factory = _session_factory_or_500()

    # Map legacy names (Standard, Premium) to Pro
    requested_plan = "Pro" if payload.plan_name in ("Pro", "Standard", "Premium") else payload.plan_name
    if requested_plan not in PAID_PLAN_NAMES:
        raise HTTPException(status_code=400, detail="plan_name must be Pro")

    amount = PLAN_PRICING["Pro"]  # 99 PHP

    async with session_factory() as session:
        # Supersede any old pending intents
        pending_res = await session.execute(
            select(InvoiceIntentORM).where(
                InvoiceIntentORM.user_id == user_id,
                InvoiceIntentORM.status == INTENT_STATUS_PENDING_PAYMENT,
            )
        )
        for old_intent in pending_res.scalars().all():
            old_intent.status = INTENT_STATUS_SUPERSEDED

        reference_id = _to_reference_id(user_id)
        payment_session = _create_xendit_payment_session(
            reference_id=reference_id,
            amount=amount,
            description=f"{requested_plan} Plan Monthly Subscription",
        )

        session.add(
            InvoiceIntentORM(
                external_id=reference_id,
                xendit_invoice_id=payment_session.payment_session_id,
                user_id=user_id,
                plan_name="Pro",
                amount=amount,
                currency=payment_session.currency.upper(),
                status=INTENT_STATUS_PENDING_PAYMENT,
                components_sdk_key=payment_session.components_sdk_key,
            )
        )

        sub_res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
        subscription = sub_res.scalar_one_or_none()

        now = datetime.now(UTC)
        if subscription is None:
            subscription = SubscriptionORM(
                user_id=user_id,
                plan_name="Pro",
                status=INTENT_STATUS_PENDING_PAYMENT,
                cancel_at_period_end=False,
                created_at=now,
                updated_at=now,
            )
            session.add(subscription)
        else:
            subscription.plan_name = "Pro"
            # Keep status pending_payment until verified payment success
            subscription.status = INTENT_STATUS_PENDING_PAYMENT
            subscription.updated_at = now

        await session.commit()

    return SubscribeResponse(components_sdk_key=payment_session.components_sdk_key)


@app.post("/api/v1/billing/trial/start", response_model=TrialStartResponse)
async def billing_start_trial(user_id: str = Depends(_require_user_id)) -> TrialStartResponse:
    session_factory = _session_factory_or_500()

    async with session_factory() as session:
        # Check eligibility: one-time trial per account
        trial_res = await session.execute(select(ProTrialORM).where(ProTrialORM.user_id == user_id))
        if trial_res.scalar_one_or_none() is not None:
            raise HTTPException(status_code=400, detail="Trial already used for this account")

        # Must not have active paid Pro subscription
        sub_res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
        subscription = sub_res.scalar_one_or_none()
        if subscription and subscription.status == "active":
            raise HTTPException(status_code=400, detail="Account already has an active Pro subscription")

        now = datetime.now(UTC)
        expires_at = now + timedelta(days=7)
        trial = ProTrialORM(
            id=str(uuid4()),
            user_id=user_id,
            started_at=now,
            expires_at=expires_at,
        )
        session.add(trial)
        await session.commit()

    return TrialStartResponse(
        status="active",
        expires_at=_to_iso_z(expires_at) or "",
        days_remaining=7,
    )


@app.post("/api/v1/billing/cancel", response_model=BillingStatusResponse)
async def billing_cancel(user_id: str = Depends(_require_user_id)) -> BillingStatusResponse:
    session_factory = _session_factory_or_500()

    async with session_factory() as session:
        sub_res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
        subscription = sub_res.scalar_one_or_none()

        if subscription is None or subscription.status != "active":
            raise HTTPException(status_code=400, detail="No active subscription to cancel")

        now = datetime.now(UTC)
        subscription.cancel_at_period_end = True
        subscription.canceled_at = now
        subscription.updated_at = now
        await session.commit()

    return await billing_status(user_id=user_id)


@app.get("/api/v1/billing/history", response_model=list[PaymentRecord])
async def billing_payment_history(user_id: str = Depends(_require_user_id)) -> list[PaymentRecord]:
    session_factory = _session_factory_or_500()

    async with session_factory() as session:
        res = await session.execute(
            select(PaymentHistoryORM)
            .where(PaymentHistoryORM.user_id == user_id)
            .order_by(PaymentHistoryORM.created_at.desc())
        )
        records = res.scalars().all()

        return [
            PaymentRecord(
                id=rec.id,
                date=_to_iso_z(rec.created_at) or "",
                amount=f"₱{rec.amount}.00",
                raw_amount=rec.amount,
                currency=rec.currency,
                status=rec.status,
                description=rec.description,
            )
            for rec in records
        ]


@app.get("/api/v1/billing/receipts/{payment_id}", response_model=ReceiptResponse)
async def billing_get_receipt(payment_id: str, user_id: str = Depends(_require_user_id)) -> ReceiptResponse:
    session_factory = _session_factory_or_500()

    async with session_factory() as session:
        res = await session.execute(
            select(PaymentHistoryORM).where(
                PaymentHistoryORM.id == payment_id,
                PaymentHistoryORM.user_id == user_id,
            )
        )
        record = res.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Receipt not found")

        receipt_text = (
            f"=== Math as a Service Receipt ===\n"
            f"Receipt ID: {record.id}\n"
            f"Date: {_to_iso_z(record.created_at)}\n"
            f"Description: {record.description}\n"
            f"Amount: ₱{record.amount}.00 {record.currency}\n"
            f"Status: {record.status.upper()}\n"
            f"Customer: {user_id}\n"
            f"Thank you for using MaaS!\n"
        )

        return ReceiptResponse(
            receipt_id=record.id,
            user_id=record.user_id,
            amount=f"₱{record.amount}.00",
            currency=record.currency,
            status=record.status,
            date=_to_iso_z(record.created_at) or "",
            description=record.description,
            receipt_text=receipt_text,
        )


# --- Usage Reservation & Quota Flow ---

@app.post("/api/v1/billing/usage/reserve", response_model=UsageReserveResponse)
async def billing_reserve_usage(user_id: str = Depends(_require_user_id)) -> UsageReserveResponse:
    session_factory = _session_factory_or_500()
    now = datetime.now(UTC)
    today_str = now.strftime("%Y-%m-%d")

    async with session_factory() as session:
        state = await _get_effective_state(session, user_id)
        if state["is_pro"]:
            return UsageReserveResponse(allowed=True, unlimited=True, reservation_id=None, remaining=None)

        # Hobby quota check: clean up expired reservations first
        await session.execute(
            delete(UsageReservationORM).where(
                UsageReservationORM.user_id == user_id,
                UsageReservationORM.status == "reserved",
                UsageReservationORM.expires_at < now,
            )
        )

        # Get or create daily usage
        res = await session.execute(
            select(DailyUsageORM).where(
                DailyUsageORM.user_id == user_id,
                DailyUsageORM.usage_date == today_str,
            )
        )
        daily_usage = res.scalar_one_or_none()
        if daily_usage is None:
            daily_usage = DailyUsageORM(
                user_id=user_id,
                usage_date=today_str,
                used_count=0,
                reserved_count=0,
            )
            session.add(daily_usage)

        total_in_flight = daily_usage.used_count + daily_usage.reserved_count
        if total_in_flight >= HOBBY_CALCULATION_LIMIT:
            logger.info("Quota exceeded for user %s: used=%d, reserved=%d", user_id, daily_usage.used_count, daily_usage.reserved_count)
            raise HTTPException(
                status_code=429,
                detail="Daily calculation limit reached (50/50). Upgrade to Pro for unlimited calculations.",
            )

        # Reserve
        reservation_id = str(uuid4())
        reservation = UsageReservationORM(
            reservation_id=reservation_id,
            user_id=user_id,
            usage_date=today_str,
            status="reserved",
            created_at=now,
            expires_at=now + timedelta(seconds=60),
        )
        session.add(reservation)
        daily_usage.reserved_count += 1
        await session.commit()

        remaining = HOBBY_CALCULATION_LIMIT - (daily_usage.used_count + daily_usage.reserved_count)
        return UsageReserveResponse(
            allowed=True,
            unlimited=False,
            reservation_id=reservation_id,
            remaining=max(0, remaining),
        )


@app.post("/api/v1/billing/usage/commit", response_model=UsageActionResponse)
async def billing_commit_usage(
    payload: UsageActionRequest,
    user_id: str = Depends(_require_user_id),
) -> UsageActionResponse:
    reservation_id = payload.reservation_id
    if not reservation_id:
        return UsageActionResponse(status="ok")

    session_factory = _session_factory_or_500()
    async with session_factory() as session:
        res = await session.execute(
            select(UsageReservationORM).where(
                UsageReservationORM.reservation_id == reservation_id,
                UsageReservationORM.status == "reserved",
            )
        )
        reservation = res.scalar_one_or_none()
        if reservation is not None:
            reservation.status = "committed"
            today_res = await session.execute(
                select(DailyUsageORM).where(
                    DailyUsageORM.user_id == reservation.user_id,
                    DailyUsageORM.usage_date == reservation.usage_date,
                )
            )
            daily_usage = today_res.scalar_one_or_none()
            if daily_usage:
                daily_usage.reserved_count = max(0, daily_usage.reserved_count - 1)
                daily_usage.used_count += 1
            await session.commit()

    return UsageActionResponse(status="committed")


@app.post("/api/v1/billing/usage/release", response_model=UsageActionResponse)
async def billing_release_usage(
    payload: UsageActionRequest,
    user_id: str = Depends(_require_user_id),
) -> UsageActionResponse:
    reservation_id = payload.reservation_id
    if not reservation_id:
        return UsageActionResponse(status="ok")

    session_factory = _session_factory_or_500()
    async with session_factory() as session:
        res = await session.execute(
            select(UsageReservationORM).where(
                UsageReservationORM.reservation_id == reservation_id,
                UsageReservationORM.status == "reserved",
            )
        )
        reservation = res.scalar_one_or_none()
        if reservation is not None:
            reservation.status = "released"
            today_res = await session.execute(
                select(DailyUsageORM).where(
                    DailyUsageORM.user_id == reservation.user_id,
                    DailyUsageORM.usage_date == reservation.usage_date,
                )
            )
            daily_usage = today_res.scalar_one_or_none()
            if daily_usage:
                daily_usage.reserved_count = max(0, daily_usage.reserved_count - 1)
            await session.commit()

    return UsageActionResponse(status="released")


@app.get("/api/v1/billing/usage", response_model=UsageStatus)
async def billing_get_usage(user_id: str = Depends(_require_user_id)) -> UsageStatus:
    session_factory = _session_factory_or_500()

    async with session_factory() as session:
        state = await _get_effective_state(session, user_id)
        return await _get_today_usage(session, user_id, is_pro=state["is_pro"])


# --- Xendit Webhook Consumer ---

def _extract_paid_amount(*, paid_amount: float | None, amount: float | None) -> int | None:
    raw_amount = paid_amount if paid_amount is not None else amount
    if raw_amount is None or raw_amount < 0:
        return None
    if not float(raw_amount).is_integer():
        return None
    return int(raw_amount)


@app.post("/api/v1/billing/webhook/xendit", response_model=WebhookResponse)
async def billing_webhook_xendit(
    payload: XenditWebhookPayload,
    x_callback_token: str | None = Header(default=None, alias="x-callback-token"),
) -> WebhookResponse:
    expected_token = get_xendit_callback_token()

    if x_callback_token is None or x_callback_token != expected_token:
        logger.warning("Webhook rejected: invalid or missing callback token")
        raise HTTPException(status_code=401, detail="Invalid or missing webhook callback token")

    logger.info("Webhook received with full payload: %s", payload.model_dump())

    event_type = payload.event or ("payment.paid" if payload.status == "PAID" else "unknown")

    # Idempotency identifier
    data_dict = payload.data or {}
    webhook_id = (
        payload.id
        or data_dict.get("payment_id")
        or data_dict.get("payment_session_id")
        or data_dict.get("id")
        or payload.reference_id
        or payload.external_id
    )
    idempotency_key = f"{event_type}:{webhook_id}" if webhook_id else None

    session_factory = _session_factory_or_500()

    # Check if webhook has already been processed
    if idempotency_key:
        async with session_factory() as session:
            already_processed = await session.get(ProcessedWebhookORM, idempotency_key)
            if already_processed:
                logger.info("Webhook already processed: %s", idempotency_key)
                return WebhookResponse(received=True)

    # 1. Handle Recurring Cycle Events (Renewal Success, Failure, Retrying)
    if event_type in ("recurring.cycle.succeeded", "cycle.succeeded"):
        cycle_plan_id = data_dict.get("recurring_plan_id") or data_dict.get("plan_id") or payload.id
        async with session_factory() as session:
            sub = None
            if cycle_plan_id:
                res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.xendit_plan_id == cycle_plan_id))
                sub = res.scalar_one_or_none()

            if sub is None and (payload.reference_id or data_dict.get("reference_id")):
                ref = payload.reference_id or data_dict.get("reference_id")
                intent_res = await session.execute(select(InvoiceIntentORM).where(InvoiceIntentORM.external_id == ref))
                intent = intent_res.scalar_one_or_none()
                if intent:
                    sub_res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == intent.user_id))
                    sub = sub_res.scalar_one_or_none()

            now = datetime.now(UTC)
            if sub is not None:
                current_end = _as_utc(sub.current_period_end) if sub.current_period_end else now
                sub.current_period_end = max(now, current_end) + timedelta(days=30)
                sub.status = "active"
                sub.grace_period_deadline = None
                sub.updated_at = now

                session.add(
                    PaymentHistoryORM(
                        id=str(uuid4()),
                        user_id=sub.user_id,
                        subscription_id=sub.id,
                        cycle_id=data_dict.get("id"),
                        amount=99,
                        currency="PHP",
                        status="succeeded",
                        description="Pro Plan Monthly Subscription - Renewal",
                        created_at=now,
                    )
                )

            if idempotency_key:
                session.add(ProcessedWebhookORM(id=idempotency_key, event_type=event_type, processed_at=now))

            await session.commit()
        return WebhookResponse(received=True)

    if event_type in ("recurring.cycle.retrying", "recurring.cycle.failed", "cycle.failed"):
        cycle_plan_id = data_dict.get("recurring_plan_id") or data_dict.get("plan_id") or payload.id
        async with session_factory() as session:
            sub = None
            if cycle_plan_id:
                res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.xendit_plan_id == cycle_plan_id))
                sub = res.scalar_one_or_none()

            if sub is None and (payload.reference_id or data_dict.get("reference_id")):
                ref = payload.reference_id or data_dict.get("reference_id")
                intent_res = await session.execute(select(InvoiceIntentORM).where(InvoiceIntentORM.external_id == ref))
                intent = intent_res.scalar_one_or_none()
                if intent:
                    sub_res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == intent.user_id))
                    sub = sub_res.scalar_one_or_none()

            now = datetime.now(UTC)
            if sub is not None:
                sub.status = "past_due"
                if not sub.grace_period_deadline:
                    sub.grace_period_deadline = now + timedelta(days=7)
                sub.updated_at = now

                session.add(
                    PaymentHistoryORM(
                        id=str(uuid4()),
                        user_id=sub.user_id,
                        subscription_id=sub.id,
                        cycle_id=data_dict.get("id"),
                        amount=99,
                        currency="PHP",
                        status="failed",
                        description="Pro Plan Monthly Subscription - Renewal Failed (7-Day Grace Period)",
                        created_at=now,
                    )
                )

            if idempotency_key:
                session.add(ProcessedWebhookORM(id=idempotency_key, event_type=event_type, processed_at=now))

            await session.commit()
        return WebhookResponse(received=True)

    if event_type in ("recurring.plan.deactivated", "plan.deactivated"):
        plan_id = data_dict.get("recurring_plan_id") or data_dict.get("plan_id") or data_dict.get("id") or payload.id
        async with session_factory() as session:
            res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.xendit_plan_id == plan_id))
            sub = res.scalar_one_or_none()
            now = datetime.now(UTC)
            if sub is not None:
                sub.status = "expired"
                sub.updated_at = now

            if idempotency_key:
                session.add(ProcessedWebhookORM(id=idempotency_key, event_type=event_type, processed_at=now))

            await session.commit()
        return WebhookResponse(received=True)

    # A plan activation means the payment method was linked. It is not proof that
    # the initial subscription cycle was paid, so persist the provider plan ID
    # but wait for a payment-confirming event before granting Pro access.
    if event_type in ("recurring.plan.activated", "plan.activated"):
        reference_id = payload.reference_id or data_dict.get("reference_id")
        plan_id = data_dict.get("recurring_plan_id") or data_dict.get("plan_id") or data_dict.get("id")
        async with session_factory() as session:
            intent = None
            if reference_id:
                result = await session.execute(
                    select(InvoiceIntentORM).where(InvoiceIntentORM.external_id == reference_id)
                )
                intent = result.scalar_one_or_none()
            if intent is not None and plan_id:
                result = await session.execute(
                    select(SubscriptionORM).where(SubscriptionORM.user_id == intent.user_id)
                )
                subscription = result.scalar_one_or_none()
                if subscription is not None:
                    subscription.xendit_plan_id = plan_id
                    subscription.updated_at = datetime.now(UTC)
            if idempotency_key:
                session.add(ProcessedWebhookORM(id=idempotency_key, event_type=event_type, processed_at=datetime.now(UTC)))
            await session.commit()
        return WebhookResponse(received=True)

    # 2. Handle the confirmed initial payment.
    is_initial_activation = (
        event_type in ("payment_session.completed", "payment.capture")
        or (payload.status == "PAID" and event_type == "payment.paid")
    )

    if not is_initial_activation:
        logger.info("Webhook ignored: event=%s, status=%s", payload.event, payload.status)
        return WebhookResponse(received=True)

    reference_id = payload.reference_id or payload.external_id
    if reference_id is None and payload.data:
        reference_id = payload.data.get("reference_id") or payload.data.get("external_id")

    if reference_id is None:
        logger.error("Webhook rejected: missing reference_id in payload=%s", payload.model_dump())
        raise HTTPException(status_code=400, detail="Missing reference_id")

    amount_value = payload.paid_amount or payload.amount
    if amount_value is None and payload.data:
        amount_value = payload.data.get("paid_amount") or payload.data.get("amount")

    paid_amount = _extract_paid_amount(paid_amount=amount_value, amount=amount_value) if amount_value is not None else None
    payload_currency = (payload.currency or "").upper()
    if not payload_currency and payload.data:
        payload_currency = (payload.data.get("currency") or "").upper()

    if paid_amount is None:
        logger.error("Webhook rejected: missing or invalid paid amount")
        raise HTTPException(status_code=400, detail="Missing payment amount")

    if not payload_currency:
        raise HTTPException(status_code=400, detail="Missing currency")

    now = datetime.now(UTC)
    period_end = now + timedelta(days=30)

    async with session_factory() as session:
        intent_res = await session.execute(select(InvoiceIntentORM).where(InvoiceIntentORM.external_id == reference_id))
        intent = intent_res.scalar_one_or_none()
        if intent is None:
            logger.error("Webhook rejected: unknown reference_id=%s", reference_id)
            raise HTTPException(status_code=400, detail="Unknown reference_id")

        if intent.status != INTENT_STATUS_PENDING_PAYMENT or intent.processed_at is not None:
            logger.info("Webhook ignored: intent already processed or not pending")
            return WebhookResponse(received=True)

        payment_session_id = data_dict.get("payment_session_id") or payload.id
        if intent.xendit_invoice_id is not None and payment_session_id != intent.xendit_invoice_id:
            raise HTTPException(status_code=400, detail="Payment session ID mismatch")

        if paid_amount != intent.amount:
            raise HTTPException(status_code=400, detail="Amount mismatch")

        if payload_currency != intent.currency.upper():
            raise HTTPException(status_code=400, detail="Currency mismatch")

        sub_res = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == intent.user_id))
        subscription = sub_res.scalar_one_or_none()

        plan_id_from_data = (
            data_dict.get("recurring_plan_id") or data_dict.get("plan_id") or data_dict.get("id")
        )

        if subscription is None:
            subscription = SubscriptionORM(
                user_id=intent.user_id,
                plan_name="Pro",
                status="active",
                xendit_plan_id=plan_id_from_data,
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False,
                grace_period_deadline=None,
                created_at=now,
                updated_at=now,
            )
            session.add(subscription)
        else:
            subscription.plan_name = "Pro"
            subscription.status = "active"
            if plan_id_from_data:
                subscription.xendit_plan_id = plan_id_from_data
            subscription.current_period_start = now
            subscription.current_period_end = period_end
            subscription.cancel_at_period_end = False
            subscription.grace_period_deadline = None
            subscription.updated_at = now

        intent.status = INTENT_STATUS_PAID
        intent.processed_at = now

        # Add initial payment record
        session.add(
            PaymentHistoryORM(
                id=str(uuid4()),
                user_id=intent.user_id,
                subscription_id=subscription.id,
                xendit_payment_id=data_dict.get("payment_id") or data_dict.get("payment_request_id") or payment_session_id,
                amount=intent.amount,
                currency=intent.currency,
                status="succeeded",
                description="Pro Plan Monthly Subscription - Month 1",
                created_at=now,
            )
        )

        if idempotency_key:
            session.add(ProcessedWebhookORM(id=idempotency_key, event_type=event_type, processed_at=now))

        await session.commit()

    return WebhookResponse(received=True)
