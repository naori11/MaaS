import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictFloat, StrictInt

from config import LEDGER_DEFAULT_LIMIT, LEDGER_MAX_LIMIT, LEDGER_QUEUE_MAXSIZE



class LedgerEventIn(BaseModel):
    request_id: str
    operation_type: Literal["addition", "subtraction", "multiplication", "division"]
    operand_a: StrictInt | StrictFloat
    operand_b: StrictInt | StrictFloat
    result: int | float
    math_transaction_id: str
    created_at: str


class LedgerRecord(BaseModel):
    id: str
    request_id: str
    operation_type: Literal["addition", "subtraction", "multiplication", "division"]
    operand_a: StrictInt | StrictFloat
    operand_b: StrictInt | StrictFloat
    result: int | float
    math_transaction_id: str
    created_at: str


class EnqueueResponse(BaseModel):
    status: Literal["accepted"]


class LedgerTransactionsResponse(BaseModel):
    items: list[LedgerRecord]


_QUEUE: asyncio.Queue[LedgerEventIn] | None = None
_RECORDS: list[LedgerRecord] = []
_RECORDS_LOCK = asyncio.Lock()
_WORKER_TASK: asyncio.Task | None = None


async def request_validation_exception_handler(_, __):
    return JSONResponse(status_code=400, content={"detail": "Malformed payload"})


def _validate_iso8601_utc(value: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Malformed payload") from exc


async def _worker(queue: asyncio.Queue[LedgerEventIn]) -> None:
    while True:
        item = await queue.get()
        record = LedgerRecord(id=str(uuid4()), **item.model_dump())
        async with _RECORDS_LOCK:
            _RECORDS.append(record)
        queue.task_done()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _QUEUE, _WORKER_TASK
    _QUEUE = asyncio.Queue(maxsize=LEDGER_QUEUE_MAXSIZE)
    _WORKER_TASK = asyncio.create_task(_worker(_QUEUE))
    try:
        yield
    finally:
        if _WORKER_TASK is not None:
            _WORKER_TASK.cancel()
            with suppress(asyncio.CancelledError):
                await _WORKER_TASK


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)


@app.post("/api/v1/ledger/transactions", status_code=202, response_model=EnqueueResponse)
async def enqueue_transaction(payload: LedgerEventIn) -> EnqueueResponse:
    _validate_iso8601_utc(payload.created_at)

    if _QUEUE is None:
        raise HTTPException(status_code=500, detail="Ledger queue unavailable")

    try:
        _QUEUE.put_nowait(payload)
    except asyncio.QueueFull as exc:
        raise HTTPException(status_code=503, detail="Ledger queue is full") from exc

    return EnqueueResponse(status="accepted")


@app.get("/api/v1/ledger/transactions", response_model=LedgerTransactionsResponse)
async def get_transactions(limit: int = Query(default=LEDGER_DEFAULT_LIMIT, gt=0, le=LEDGER_MAX_LIMIT)) -> LedgerTransactionsResponse:
    async with _RECORDS_LOCK:
        recent = list(reversed(_RECORDS[-limit:]))
    return LedgerTransactionsResponse(items=recent)
