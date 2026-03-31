from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictFloat, StrictInt


app = FastAPI()


class AdditionRequest(BaseModel):
    operand_a: StrictInt | StrictFloat
    operand_b: StrictInt | StrictFloat


class AdditionResponse(BaseModel):
    operation: Literal["addition"]
    result: int | float
    transaction_id: str
    timestamp: str


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_, __):
    return JSONResponse(status_code=400, content={"detail": "Malformed payload"})


def _normalize_result(result: float) -> int | float:
    if result.is_integer():
        return int(result)
    return result


@app.post("/api/v1/calculate/add", response_model=AdditionResponse)
def add(payload: AdditionRequest) -> AdditionResponse:
    raw_result = float(payload.operand_a) + float(payload.operand_b)

    return AdditionResponse(
        operation="addition",
        result=_normalize_result(raw_result),
        transaction_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
