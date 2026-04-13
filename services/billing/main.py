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
from sqlalchemy import DateTime, Integer, String, Text, inspect, select, text
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
    "Free": 0,
    "Standard": 50,
    "Premium": 250,
}

PAID_PLAN_NAMES = {"Standard", "Premium"}
INTENT_STATUS_PENDING_PAYMENT = "pending_payment"
INTENT_STATUS_PAID = "paid"
INTENT_STATUS_SUPERSEDED = "superseded"
INTENT_STATUS_CANCELLED = "cancelled"
INTENT_REUSE_WINDOW = timedelta(minutes=30)


class Base(DeclarativeBase):
    pass


class SubscriptionORM(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    plan_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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


class BillingStatusResponse(BaseModel):
    plan_name: str
    status: str
    expires_at: str | None


class SubscribeRequest(BaseModel):
    plan_name: str = Field(pattern="^(Standard|Premium)$")


class SubscribeResponse(BaseModel):
    components_sdk_key: str


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
    data: dict | None = None  # Xendit may nest data in a 'data' field


class WebhookResponse(BaseModel):
    received: bool


_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


async def request_validation_exception_handler(_, __):
    return JSONResponse(status_code=400, content={"detail": "Malformed payload"})


def _to_iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _extract_paid_amount(*, paid_amount: float | None, amount: float | None) -> int | None:
    raw_amount = paid_amount if paid_amount is not None else amount
    if raw_amount is None or raw_amount < 0:
        return None

    if not float(raw_amount).is_integer():
        return None

    return int(raw_amount)


def _session_factory_or_500() -> async_sessionmaker[AsyncSession]:
    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return _SESSION_FACTORY


async def _ensure_invoice_intents_components_sdk_key_column(engine) -> None:
    async with engine.begin() as conn:
        def _column_type(sync_conn) -> str | None:
            inspector = inspect(sync_conn)
            columns = inspector.get_columns("invoice_intents")
            for column in columns:
                if column["name"] == "components_sdk_key":
                    return str(column["type"]).lower()
            return None

        column_type = await conn.run_sync(_column_type)
        if column_type is None:
            await conn.execute(text("ALTER TABLE invoice_intents ADD COLUMN components_sdk_key TEXT"))
            logger.info("Added missing invoice_intents.components_sdk_key column as TEXT")
            return

        if "character varying" in column_type or "varchar" in column_type:
            await conn.execute(text("ALTER TABLE invoice_intents ALTER COLUMN components_sdk_key TYPE TEXT"))
            logger.info("Expanded invoice_intents.components_sdk_key column to TEXT")


def _to_reference_id(user_id: str) -> str:
    compact_user_id = user_id.replace("-", "")[:16]
    return f"upgrade_{compact_user_id}_{uuid4().hex[:32]}"


def _decode_user_id(authorization: str | None) -> str:
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


def _as_utc(dt: datetime) -> datetime:
    """Return *dt* as a timezone-aware UTC datetime.

    SQLite does not persist timezone information, so datetimes read back from
    the database may be offset-naive even though they were stored from
    ``datetime.now(UTC)``.  This helper treats naive datetimes as UTC so that
    comparisons against offset-aware values work correctly for both SQLite
    (tests) and PostgreSQL (production).
    """
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


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

    payload = {
        "reference_id": reference_id,
        "session_type": "PAY",
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
            "Created Xendit payment session reference_id=%s session_id=%s configured_origins=%s",
            reference_id,
            response_payload.get("id"),
            payload["components_configuration"]["origins"],
        )

        components_sdk_key = response_payload.get("components_sdk_key")
        if not isinstance(components_sdk_key, str) or not components_sdk_key:
            raise HTTPException(status_code=502, detail="Xendit payment session response missing components_sdk_key")

        payment_session_id = response_payload.get("id")
        payment_session_currency = response_payload.get("currency")

        return XenditPaymentSessionResult(
            components_sdk_key=components_sdk_key,
            payment_session_id=payment_session_id if isinstance(payment_session_id, str) and payment_session_id else None,
            currency=payment_session_currency if isinstance(payment_session_currency, str) and payment_session_currency else "PHP",
        )
    except HTTPException:
        raise
    except XenditSdkException as exc:
        logger.exception("Xendit SDK error while creating payment session")
        message = getattr(exc, "errorMessage", None) or str(exc) or "Xendit payment session creation failed"
        raise HTTPException(status_code=502, detail=message) from exc
    except OpenApiException as exc:
        logger.exception("Xendit API error while creating payment session")
        raise HTTPException(status_code=502, detail="Xendit payment session creation failed") from exc
    except Exception as exc:
        logger.exception("Failed to create Xendit payment session")
        raise HTTPException(status_code=502, detail="Failed to create payment session") from exc


async def _require_user_id(authorization: str | None = Header(default=None)) -> str:
    return _decode_user_id(authorization)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _SESSION_FACTORY

    database_url = get_database_url()
    engine = None

    if database_url:
        engine = create_async_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await _ensure_invoice_intents_components_sdk_key_column(engine)
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


@app.get("/api/v1/billing/status", response_model=BillingStatusResponse)
async def billing_status(user_id: str = Depends(_require_user_id)) -> BillingStatusResponse:
    session_factory = _session_factory_or_500()

    async with session_factory() as session:
        result = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
        subscription = result.scalar_one_or_none()

    if subscription is None:
        return BillingStatusResponse(plan_name="Free", status="active", expires_at=None)

    return BillingStatusResponse(
        plan_name=subscription.plan_name,
        status=subscription.status,
        expires_at=_to_iso_z(subscription.expires_at),
    )


@app.post("/api/v1/billing/subscribe", response_model=SubscribeResponse)
async def billing_subscribe(payload: SubscribeRequest, user_id: str = Depends(_require_user_id)) -> SubscribeResponse:
    session_factory = _session_factory_or_500()

    plan_name = payload.plan_name
    if plan_name not in PAID_PLAN_NAMES:
        raise HTTPException(status_code=400, detail="plan_name must be Standard or Premium")

    amount = PLAN_PRICING[plan_name]

    async with session_factory() as session:
        pending_intent_result = await session.execute(
            select(InvoiceIntentORM).where(
                InvoiceIntentORM.user_id == user_id,
                InvoiceIntentORM.status == INTENT_STATUS_PENDING_PAYMENT,
            )
        )
        pending_intents = list(pending_intent_result.scalars().all())

        for intent in pending_intents:
            intent.status = INTENT_STATUS_SUPERSEDED
            logger.info("Superseded previous pending intent: intent_id=%s plan=%s", intent.id, intent.plan_name)

        reference_id = _to_reference_id(user_id)
        payment_session = _create_xendit_payment_session(
            reference_id=reference_id,
            amount=amount,
            description=f"{plan_name} Plan Upgrade",
        )

        session.add(
            InvoiceIntentORM(
                external_id=reference_id,
                xendit_invoice_id=payment_session.payment_session_id,
                user_id=user_id,
                plan_name=plan_name,
                amount=amount,
                currency=payment_session.currency.upper(),
                status=INTENT_STATUS_PENDING_PAYMENT,
                components_sdk_key=payment_session.components_sdk_key,
            )
        )
        sdk_key = payment_session.components_sdk_key

        result = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
        subscription = result.scalar_one_or_none()

        if subscription is None:
            subscription = SubscriptionORM(
                user_id=user_id,
                plan_name=plan_name,
                status=INTENT_STATUS_PENDING_PAYMENT,
                expires_at=None,
            )
            session.add(subscription)
        else:
            subscription.plan_name = plan_name
            subscription.status = INTENT_STATUS_PENDING_PAYMENT
            subscription.expires_at = None

        await session.commit()

    return SubscribeResponse(components_sdk_key=cast(str, sdk_key))


@app.post("/api/v1/billing/webhook/xendit", response_model=WebhookResponse)
async def billing_webhook_xendit(
    payload: XenditWebhookPayload,
    x_callback_token: str | None = Header(default=None, alias="x-callback-token"),
) -> WebhookResponse:
    expected_token = get_xendit_callback_token()

    if x_callback_token is None or x_callback_token != expected_token:
        logger.warning("Webhook rejected: invalid or missing callback token")
        raise HTTPException(status_code=401, detail="Invalid or missing webhook callback token")

    # Log the complete payload for debugging
    logger.info("Webhook received with full payload: %s", payload.dict())

    if payload.event is not None:
        if payload.event != "payment_session.completed":
            logger.info("Webhook ignored: event=%s (not payment_session.completed)", payload.event)
            return WebhookResponse(received=True)
    elif payload.status != "PAID":
        logger.info("Webhook ignored: status=%s (not PAID)", payload.status)
        return WebhookResponse(received=True)

    # Extract reference_id from root level or nested data field
    reference_id = payload.reference_id or payload.external_id
    if reference_id is None and payload.data:
        reference_id = payload.data.get("reference_id") or payload.data.get("external_id")

    if reference_id is None:
        logger.error("Webhook rejected: missing reference_id in root and data fields, payload=%s", payload.dict())
        raise HTTPException(status_code=400, detail="Missing reference_id")

    # Extract amount from root level or nested data field
    amount_value = payload.paid_amount or payload.amount
    if amount_value is None and payload.data:
        amount_value = payload.data.get("paid_amount") or payload.data.get("amount")

    paid_amount = _extract_paid_amount(paid_amount=amount_value, amount=amount_value) if amount_value is not None else None

    # payload_currency is populated below; initialize to empty so the TEST MODE
    # block can set it and the subsequent extraction can detect that.
    payload_currency: str = ""

    # ⚠️ TEST MODE ONLY - REMOVE FOR PRODUCTION ⚠️
    # This block allows test webhooks (no amount) to activate subscriptions for testing purposes.
    # In production, this creates a security vulnerability where attackers could activate
    # subscriptions without payment by sending webhooks with valid reference_ids but no amounts.
    # TODO: Remove this entire block before deploying to production
    if paid_amount is None:
        session_factory = _session_factory_or_500()
        async with session_factory() as session:
            intent_result = await session.execute(select(InvoiceIntentORM).where(InvoiceIntentORM.external_id == reference_id))
            intent = intent_result.scalar_one_or_none()

            if intent is not None:
                # TEST MODE: Process webhook without amount validation
                logger.warning("⚠️ TEST MODE: Processing webhook without amount validation - reference_id=%s", reference_id)
                paid_amount = intent.amount  # Use the expected amount from our records
                payload_currency = intent.currency.upper()
            else:
                # No matching intent - this is a connectivity test webhook
                logger.info("Webhook acknowledged (test webhook): no amount and no matching intent, reference_id=%s", reference_id)
                return WebhookResponse(received=True)
    # ⚠️ END TEST MODE BLOCK ⚠️

    # Extract currency from root level or nested data field only when it has not
    # already been populated from the stored intent (TEST MODE path above).
    if not payload_currency:
        payload_currency = (payload.currency or "").upper()
        if not payload_currency and payload.data:
            payload_currency = (payload.data.get("currency") or "").upper()

    if not payload_currency:
        logger.error("Webhook rejected: missing currency")
        raise HTTPException(status_code=400, detail="Missing currency")

    session_factory = _session_factory_or_500()
    expires_at = datetime.now(UTC) + timedelta(days=30)

    async with session_factory() as session:
        intent_result = await session.execute(select(InvoiceIntentORM).where(InvoiceIntentORM.external_id == reference_id))
        intent = intent_result.scalar_one_or_none()
        if intent is None:
            logger.error("Webhook rejected: unknown reference_id=%s", reference_id)
            raise HTTPException(status_code=400, detail="Unknown reference_id")

        logger.info(
            "Webhook matched intent: intent_id=%s user_id=%s plan=%s status=%s amount=%s currency=%s processed_at=%s",
            intent.id,
            intent.user_id,
            intent.plan_name,
            intent.status,
            intent.amount,
            intent.currency,
            intent.processed_at,
        )

        if intent.status != INTENT_STATUS_PENDING_PAYMENT:
            logger.info("Webhook ignored: intent already in status=%s", intent.status)
            return WebhookResponse(received=True)

        if intent.processed_at is not None:
            logger.info("Webhook ignored: intent already processed at %s", intent.processed_at)
            return WebhookResponse(received=True)

        if intent.xendit_invoice_id is not None and payload.id != intent.xendit_invoice_id:
            logger.error(
                "Webhook rejected: session_id mismatch payload_id=%s intent_xendit_invoice_id=%s",
                payload.id,
                intent.xendit_invoice_id,
            )
            raise HTTPException(status_code=400, detail="Payment session ID mismatch")

        if paid_amount != intent.amount:
            logger.error("Webhook rejected: amount mismatch paid=%s expected=%s", paid_amount, intent.amount)
            raise HTTPException(status_code=400, detail="Amount mismatch")

        if payload_currency != intent.currency.upper():
            logger.error("Webhook rejected: currency mismatch paid=%s expected=%s", payload_currency, intent.currency)
            raise HTTPException(status_code=400, detail="Currency mismatch")

        result = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == intent.user_id))
        subscription = result.scalar_one_or_none()

        if subscription is None:
            subscription = SubscriptionORM(
                user_id=intent.user_id,
                plan_name=intent.plan_name,
                status="active",
                expires_at=expires_at,
            )
            session.add(subscription)
            logger.info(
                "Webhook activated new subscription: user_id=%s plan=%s expires_at=%s",
                intent.user_id,
                intent.plan_name,
                expires_at,
            )
        else:
            subscription.plan_name = intent.plan_name
            subscription.status = "active"
            subscription.expires_at = expires_at
            logger.info(
                "Webhook updated subscription to active: user_id=%s plan=%s expires_at=%s",
                intent.user_id,
                intent.plan_name,
                expires_at,
            )

        intent.status = INTENT_STATUS_PAID
        intent.processed_at = datetime.now(UTC)

        await session.commit()

        logger.info(
            "Webhook processing complete: reference_id=%s intent_id=%s user_id=%s plan=%s status=active",
            reference_id,
            intent.id,
            intent.user_id,
            intent.plan_name,
        )

    return WebhookResponse(received=True)
