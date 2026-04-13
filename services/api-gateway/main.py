import uuid
from datetime import datetime, timezone
from threading import Lock
from time import time

import httpx
import jwt
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jwt import InvalidTokenError

from config import (
    BILLING_SERVICE_URL,
    IDENTITY_SERVICE_URL,
    JWT_ALGORITHM,
    JWT_SECRET,
    LEDGER_PUBLISH_TIMEOUT_SECONDS,
    LEDGER_SERVICE_URL,
    MATH_ADD_SERVICE_URL,
    MATH_DIVIDE_SERVICE_URL,
    MATH_MULTIPLY_SERVICE_URL,
    MATH_SUBTRACT_SERVICE_URL,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    UPSTREAM_TIMEOUT_SECONDS,
)


app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_ROUTE_MAP = {
    "/api/v1/auth/register": f"{IDENTITY_SERVICE_URL}/api/v1/auth/register",
    "/api/v1/auth/login": f"{IDENTITY_SERVICE_URL}/api/v1/auth/login",
    "/api/v1/auth/me": f"{IDENTITY_SERVICE_URL}/api/v1/auth/me",
    "/api/v1/billing/status": f"{BILLING_SERVICE_URL}/api/v1/billing/status",
    "/api/v1/billing/subscribe": f"{BILLING_SERVICE_URL}/api/v1/billing/subscribe",
    "/api/v1/billing/webhook/xendit": f"{BILLING_SERVICE_URL}/api/v1/billing/webhook/xendit",
    "/api/v1/calculate/add": f"{MATH_ADD_SERVICE_URL}/api/v1/calculate/add",
    "/api/v1/calculate/subtract": f"{MATH_SUBTRACT_SERVICE_URL}/api/v1/calculate/subtract",
    "/api/v1/calculate/multiply": f"{MATH_MULTIPLY_SERVICE_URL}/api/v1/calculate/multiply",
    "/api/v1/calculate/divide": f"{MATH_DIVIDE_SERVICE_URL}/api/v1/calculate/divide",
    "/api/v1/ledger/transactions": f"{LEDGER_SERVICE_URL}/api/v1/ledger/transactions",
}

_STATUS_CODE_TO_ERROR_CODE = {
    400: "bad_request",
    401: "unauthorized",
    429: "rate_limited",
    500: "internal_error",
}

_RATE_LIMIT_BUCKET: dict[str, int] = {}
_RATE_LIMIT_LOCK = Lock()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") or str(uuid.uuid4())


def _error_payload(status_code: int, message: str, request_id: str) -> dict:
    return {
        "error": {
            "code": _STATUS_CODE_TO_ERROR_CODE.get(status_code, "internal_error"),
            "message": message,
        },
        "request_id": request_id,
    }


_JWT_BYPASS_ROUTES = {
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/billing/webhook/xendit"),
}


def _requires_jwt(method: str, path: str) -> bool:
    route = (method.upper(), path)

    # Explicitly allowlisted routes do NOT require JWT
    if route in _JWT_BYPASS_ROUTES:
        return False

    # For all known routes in the gateway, require JWT by default
    if path in _ROUTE_MAP:
        return True

    # For unknown routes, do not enforce JWT at the gateway
    return False


def _enforce_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    current_window = int(time() // RATE_LIMIT_WINDOW_SECONDS)
    bucket_key = f"{client_host}:{current_window}"

    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_BUCKET[bucket_key] = _RATE_LIMIT_BUCKET.get(bucket_key, 0) + 1
        current_count = _RATE_LIMIT_BUCKET[bucket_key]

    if current_count > RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _enforce_valid_jwt(request: Request) -> None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT secret not configured")

    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc


def _extract_upstream_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "Upstream request failed"

    if isinstance(body, dict):
        if isinstance(body.get("detail"), str):
            return body["detail"]
        if isinstance(body.get("message"), str):
            return body["message"]
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]

    return "Upstream request failed"


def _publishable_calculate_path(path: str) -> bool:
    return path.startswith("/api/v1/calculate/")


def _operation_type_from_path(path: str) -> str:
    suffix = path.removeprefix("/api/v1/calculate/")
    operation_map = {
        "add": "addition",
        "subtract": "subtraction",
        "multiply": "multiplication",
        "divide": "division",
    }
    return operation_map[suffix]


def _build_ledger_event(request_id: str, path: str, request_payload: dict, response_payload: dict) -> dict:
    return {
        "request_id": request_id,
        "operation_type": _operation_type_from_path(path),
        "operand_a": request_payload["operand_a"],
        "operand_b": request_payload["operand_b"],
        "result": response_payload["result"],
        "math_transaction_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


async def _publish_ledger_event(event: dict, request_id: str) -> None:
    timeout = httpx.Timeout(LEDGER_PUBLISH_TIMEOUT_SECONDS)
    headers = {
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            await client.post(
                f"{LEDGER_SERVICE_URL}/api/v1/ledger/transactions",
                json=event,
                headers=headers,
            )
    except Exception:
        pass


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming_request_id = request.headers.get("X-Request-ID")
    request.state.request_id = incoming_request_id or str(uuid.uuid4())

    response = await call_next(request)
    response.headers["X-Request-ID"] = _request_id(request)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = _request_id(request)
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(exc.status_code, detail, request_id),
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _):
    request_id = _request_id(request)
    return JSONResponse(
        status_code=500,
        content=_error_payload(500, "Internal server error", request_id),
        headers={"X-Request-ID": request_id},
    )


async def _proxy_post(request: Request, upstream_url: str, background_tasks: BackgroundTasks | None = None) -> JSONResponse:
    _enforce_rate_limit(request)

    if _requires_jwt(request.method, request.url.path):
        _enforce_valid_jwt(request)

    content_type = request.headers.get("Content-Type", "")
    if not content_type.lower().startswith("application/json"):
        raise HTTPException(status_code=400, detail="Content-Type must be application/json")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Malformed payload") from exc

    request_id = _request_id(request)
    upstream_headers = {
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    authorization = request.headers.get("Authorization")
    if authorization:
        upstream_headers["Authorization"] = authorization

    if request.url.path == "/api/v1/billing/webhook/xendit":
        # Log all incoming headers for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Xendit webhook headers: %s", dict(request.headers))

        callback_token = request.headers.get("x-callback-token")
        if callback_token:
            upstream_headers["x-callback-token"] = callback_token
        else:
            logger.warning("x-callback-token header not found in webhook request")

    timeout = httpx.Timeout(UPSTREAM_TIMEOUT_SECONDS)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream_response = await client.post(
                upstream_url,
                json=payload,
                headers=upstream_headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail="Upstream service unavailable") from exc

    if upstream_response.status_code >= 400:
        raise HTTPException(
            status_code=upstream_response.status_code,
            detail=_extract_upstream_error_message(upstream_response),
        )

    try:
        response_payload = upstream_response.json()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid upstream response") from exc

    if background_tasks is not None and _publishable_calculate_path(request.url.path):
        try:
            ledger_event = _build_ledger_event(request_id, request.url.path, payload, response_payload)
            background_tasks.add_task(_publish_ledger_event, ledger_event, request_id)
        except Exception:
            pass

    return JSONResponse(
        status_code=upstream_response.status_code,
        content=response_payload,
        headers={"X-Request-ID": request_id},
        background=background_tasks,
    )


async def _proxy_get(request: Request, upstream_url: str) -> JSONResponse:
    _enforce_rate_limit(request)

    if _requires_jwt(request.method, request.url.path):
        _enforce_valid_jwt(request)

    request_id = _request_id(request)
    upstream_headers = {
        "X-Request-ID": request_id,
    }

    authorization = request.headers.get("Authorization")
    if authorization:
        upstream_headers["Authorization"] = authorization

    upstream_query = request.url.query
    resolved_upstream_url = upstream_url if not upstream_query else f"{upstream_url}?{upstream_query}"

    timeout = httpx.Timeout(UPSTREAM_TIMEOUT_SECONDS)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream_response = await client.get(resolved_upstream_url, headers=upstream_headers)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail="Upstream service unavailable") from exc

    if upstream_response.status_code >= 400:
        raise HTTPException(
            status_code=upstream_response.status_code,
            detail=_extract_upstream_error_message(upstream_response),
        )

    try:
        response_payload = upstream_response.json()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid upstream response") from exc

    return JSONResponse(
        status_code=upstream_response.status_code,
        content=response_payload,
        headers={"X-Request-ID": request_id},
    )


@app.post("/api/v1/auth/register")
async def register(request: Request) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/auth/register"])


@app.get("/api/v1/auth/me")
async def me(request: Request) -> JSONResponse:
    return await _proxy_get(request, _ROUTE_MAP["/api/v1/auth/me"])


@app.post("/api/v1/auth/login")
async def login(request: Request) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/auth/login"])


@app.get("/api/v1/billing/status")
async def billing_status(request: Request) -> JSONResponse:
    return await _proxy_get(request, _ROUTE_MAP["/api/v1/billing/status"])


@app.get("/api/v1/ledger/transactions")
async def ledger_transactions(request: Request) -> JSONResponse:
    return await _proxy_get(request, _ROUTE_MAP["/api/v1/ledger/transactions"])


@app.post("/api/v1/billing/subscribe")
async def billing_subscribe(request: Request) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/billing/subscribe"])


@app.post("/api/v1/billing/webhook/xendit")
async def billing_webhook_xendit(request: Request) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/billing/webhook/xendit"])


@app.post("/api/v1/calculate/add")
async def add(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/calculate/add"], background_tasks)


@app.post("/api/v1/calculate/subtract")
async def subtract(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/calculate/subtract"], background_tasks)


@app.post("/api/v1/calculate/multiply")
async def multiply(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/calculate/multiply"], background_tasks)


@app.post("/api/v1/calculate/divide")
async def divide(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    return await _proxy_post(request, _ROUTE_MAP["/api/v1/calculate/divide"], background_tasks)
