import logging
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import (
    get_database_url,
    get_jwt_algorithm,
    get_jwt_secret,
    get_xendit_callback_token,
    get_xendit_secret_key,
)


logger = logging.getLogger(__name__)


PLAN_PRICING = {
    "Free": 0,
    "Standard": 50,
    "Premium": 250,
}

PAID_PLAN_NAMES = {"Standard", "Premium"}
EXTERNAL_ID_REGEX = re.compile(r"^upgrade_(?P<user_id>.+)_(?P<suffix>[0-9a-fA-F-]{36})$")


class Base(DeclarativeBase):
    pass


class SubscriptionORM(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    plan_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BillingStatusResponse(BaseModel):
    plan_name: str
    status: str
    expires_at: str | None


class SubscribeRequest(BaseModel):
    plan_name: str = Field(pattern="^(Standard|Premium)$")


class SubscribeResponse(BaseModel):
    invoice_url: str


class XenditWebhookPayload(BaseModel):
    external_id: str
    status: str
    paid_plan_name: str | None = None


class WebhookResponse(BaseModel):
    received: bool


_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


async def request_validation_exception_handler(_, __):
    return JSONResponse(status_code=400, content={"detail": "Malformed payload"})


def _to_iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _extract_user_id_from_external_id(external_id: str) -> str | None:
    match = EXTERNAL_ID_REGEX.match(external_id)
    if match is None:
        return None
    return match.group("user_id")


def _session_factory_or_500() -> async_sessionmaker[AsyncSession]:
    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return _SESSION_FACTORY


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


def _create_xendit_invoice(*, external_id: str, amount: int, description: str) -> str:
    try:
        secret_key = get_xendit_secret_key()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        import xendit
        from xendit.apis import InvoiceApi
        from xendit.exceptions import OpenApiException, XenditSdkException
        from xendit.invoice.model.create_invoice_request import CreateInvoiceRequest
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"xendit-python dependency missing: {exc.name}") from exc

    try:
        xendit.set_api_key(secret_key)
        client = xendit.ApiClient()
        invoice_api = InvoiceApi(client)

        create_invoice_request = cast(
            CreateInvoiceRequest,
            CreateInvoiceRequest(
                external_id=external_id,
                amount=float(amount),
                currency="PHP",
                description=description,
            ),
        )
        invoice = invoice_api.create_invoice(create_invoice_request)

        invoice_url = getattr(invoice, "invoice_url", None)
        if isinstance(invoice_url, str) and invoice_url:
            return invoice_url
        raise HTTPException(status_code=502, detail="Xendit invoice response missing invoice_url")
    except HTTPException:
        raise
    except XenditSdkException as exc:
        logger.exception("Xendit SDK error while creating invoice")
        message = getattr(exc, "errorMessage", None) or str(exc) or "Xendit invoice creation failed"
        raise HTTPException(status_code=502, detail=message) from exc
    except OpenApiException as exc:
        logger.exception("Xendit API error while creating invoice")
        raise HTTPException(status_code=502, detail="Xendit invoice creation failed") from exc
    except Exception as exc:
        logger.exception("Failed to create Xendit invoice")
        raise HTTPException(status_code=502, detail="Failed to create payment invoice") from exc


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
    external_id = f"upgrade_{user_id}_{uuid4()}"

    invoice_url = _create_xendit_invoice(
        external_id=external_id,
        amount=amount,
        description=f"{plan_name} Plan Upgrade",
    )

    async with session_factory() as session:
        result = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
        subscription = result.scalar_one_or_none()

        if subscription is None:
            subscription = SubscriptionORM(
                user_id=user_id,
                plan_name=plan_name,
                status="pending_payment",
                expires_at=None,
            )
            session.add(subscription)
        else:
            subscription.plan_name = plan_name
            subscription.status = "pending_payment"
            subscription.expires_at = None

        await session.commit()

    return SubscribeResponse(invoice_url=invoice_url)


@app.post("/api/v1/billing/webhook/xendit", response_model=WebhookResponse)
async def billing_webhook_xendit(
    payload: XenditWebhookPayload,
    x_callback_token: str | None = Header(default=None, alias="x-callback-token"),
) -> WebhookResponse:
    expected_token = get_xendit_callback_token()
    if expected_token is not None:
        if x_callback_token is None or x_callback_token != expected_token:
            raise HTTPException(status_code=401, detail="Invalid or missing webhook callback token")
    else:
        logger.warning("XENDIT_CALLBACK_TOKEN is not configured; webhook requests are not authenticated")
    if payload.status != "PAID":
        return WebhookResponse(received=True)

    user_id = _extract_user_id_from_external_id(payload.external_id)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid external_id")

    session_factory = _session_factory_or_500()
    expires_at = datetime.now(UTC) + timedelta(days=30)

    async with session_factory() as session:
        result = await session.execute(select(SubscriptionORM).where(SubscriptionORM.user_id == user_id))
        subscription = result.scalar_one_or_none()

        plan_name = payload.paid_plan_name if payload.paid_plan_name in PAID_PLAN_NAMES else None

        if subscription is None:
            subscription = SubscriptionORM(
                user_id=user_id,
                plan_name=plan_name or "Standard",
                status="active",
                expires_at=expires_at,
            )
            session.add(subscription)
        else:
            if plan_name:
                subscription.plan_name = plan_name
            subscription.status = "active"
            subscription.expires_at = expires_at

        await session.commit()

    return WebhookResponse(received=True)
