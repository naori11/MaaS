import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictFloat, StrictInt
from sqlalchemy import DateTime, Float, String, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import LEDGER_DEFAULT_LIMIT, LEDGER_MAX_LIMIT

logger = logging.getLogger(__name__)


OperationType = Literal["addition", "subtraction", "multiplication", "division"]


class LedgerEventIn(BaseModel):
    request_id: str
    operation_type: OperationType
    operand_a: StrictInt | StrictFloat
    operand_b: StrictInt | StrictFloat
    result: int | float
    math_transaction_id: str
    created_at: str


class LedgerRecord(BaseModel):
    id: str
    request_id: str
    operation_type: OperationType
    operand_a: int | float
    operand_b: int | float
    result: int | float
    math_transaction_id: str
    created_at: str


class EnqueueResponse(BaseModel):
    status: Literal["created"]


class LedgerTransactionsResponse(BaseModel):
    items: list[LedgerRecord]


class Base(DeclarativeBase):
    pass


class LedgerRecordORM(Base):
    __tablename__ = "ledger_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    request_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    operand_a: Mapped[float] = mapped_column(Float, nullable=False)
    operand_b: Mapped[float] = mapped_column(Float, nullable=False)
    result: Mapped[float] = mapped_column(Float, nullable=False)
    math_transaction_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


async def request_validation_exception_handler(_, __):
    return JSONResponse(status_code=400, content={"detail": "Malformed payload"})


def _database_url_from_env() -> str:
    raw_database_url = os.getenv("DATABASE_URL")
    if not raw_database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    if raw_database_url.startswith("postgresql://"):
        return raw_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_database_url


def _parse_iso8601_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Malformed payload") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _to_iso_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize_number(value: float) -> int | float:
    if float(value).is_integer():
        return int(value)
    return value


def _to_api_record(row: LedgerRecordORM) -> LedgerRecord:
    return LedgerRecord(
        id=row.id,
        request_id=row.request_id,
        operation_type=cast(OperationType, row.operation_type),
        operand_a=_normalize_number(row.operand_a),
        operand_b=_normalize_number(row.operand_b),
        result=_normalize_number(row.result),
        math_transaction_id=row.math_transaction_id,
        created_at=_to_iso_z(row.created_at),
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _SESSION_FACTORY

    database_url = _database_url_from_env()
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _SESSION_FACTORY = session_factory

    try:
        yield
    finally:
        await engine.dispose()
        _SESSION_FACTORY = None


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)


@app.post("/api/v1/ledger/transactions", status_code=201, response_model=EnqueueResponse)
async def enqueue_transaction(payload: LedgerEventIn) -> EnqueueResponse:
    created_at = _parse_iso8601_utc(payload.created_at)

    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=503, detail="Ledger database unavailable")

    try:
        async with _SESSION_FACTORY() as session:
            session.add(
                LedgerRecordORM(
                    request_id=payload.request_id,
                    operation_type=payload.operation_type,
                    operand_a=float(payload.operand_a),
                    operand_b=float(payload.operand_b),
                    result=float(payload.result),
                    math_transaction_id=payload.math_transaction_id,
                    created_at=created_at,
                )
            )
            await session.commit()
    except SQLAlchemyError as exc:
        logger.exception("Failed to persist ledger event")
        raise HTTPException(status_code=503, detail="Ledger database unavailable") from exc

    return EnqueueResponse(status="created")


@app.get("/api/v1/ledger/transactions", response_model=LedgerTransactionsResponse)
async def get_transactions(
    limit: int = Query(default=LEDGER_DEFAULT_LIMIT, gt=0, le=LEDGER_MAX_LIMIT),
) -> LedgerTransactionsResponse:
    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=500, detail="Ledger database unavailable")

    async with _SESSION_FACTORY() as session:
        result = await session.execute(
            select(LedgerRecordORM)
            .order_by(LedgerRecordORM.created_at.desc(), LedgerRecordORM.id.desc())
            .limit(limit)
        )
        items = [_to_api_record(row) for row in result.scalars().all()]

    return LedgerTransactionsResponse(items=items)
