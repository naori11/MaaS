import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
from typing import Any, Callable, ClassVar

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICE_DIR))
sys.modules.pop("config", None)
sys.modules.pop("api_gateway_main", None)

_MAIN_PATH = _SERVICE_DIR / "main.py"
_SPEC = importlib.util.spec_from_file_location("api_gateway_main", _MAIN_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load api-gateway main module spec")
main = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(main)


def _valid_gateway_token(subject: str = "user-123") -> str:
    payload = {
        "sub": subject,
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
    }
    return jwt.encode(payload, "gateway-test-secret", algorithm="HS256")


class FakeResponse:
    def __init__(self, status_code: int, body: dict[str, Any]):
        self.status_code = status_code
        self._body = body

    def json(self) -> dict[str, Any]:
        return self._body


Responder = Callable[[str, dict[str, Any], dict[str, str]], FakeResponse | Exception]


class FakeAsyncClient:
    requests: ClassVar[list[dict[str, Any]]] = []
    responder: ClassVar[Responder] = lambda url, json, headers: FakeResponse(200, {"ok": True})

    def __init__(self, *args: Any, **kwargs: Any):
        pass

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]) -> FakeResponse:
        self.__class__.requests.append(
            {
                "method": "POST",
                "url": url,
                "json": json,
                "headers": headers,
            }
        )

        result = self.__class__.responder(url, json, headers)
        if isinstance(result, Exception):
            raise result
        return result

    async def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
        self.__class__.requests.append(
            {
                "method": "GET",
                "url": url,
                "headers": headers,
            }
        )

        result = self.__class__.responder(url, {}, headers)
        if isinstance(result, Exception):
            raise result
        return result


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    main._RATE_LIMIT_BUCKET.clear()
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(main, "RATE_LIMIT_REQUESTS", 60)
    monkeypatch.setattr(main, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(main, "JWT_SECRET", "gateway-test-secret")
    monkeypatch.setattr(main, "JWT_ALGORITHM", "HS256")
    FakeAsyncClient.requests = []
    FakeAsyncClient.responder = lambda url, json, headers: FakeResponse(200, {"ok": True})
    yield
    main._RATE_LIMIT_BUCKET.clear()


@pytest.mark.parametrize(
    "path, payload, headers, expected_url",
    [
        (
            "/api/v1/auth/register",
            {"email": "user@example.com", "password": "secret"},
            {},
            f"{main.IDENTITY_SERVICE_URL}/api/v1/auth/register",
        ),
        (
            "/api/v1/auth/login",
            {"email": "user@example.com", "password": "secret"},
            {},
            f"{main.IDENTITY_SERVICE_URL}/api/v1/auth/login",
        ),
        (
            "/api/v1/billing/subscribe",
            {"plan_name": "Standard"},
            {"Authorization": f"Bearer {_valid_gateway_token()}"},
            f"{main.BILLING_SERVICE_URL}/api/v1/billing/subscribe",
        ),
        (
            "/api/v1/billing/webhook/xendit",
            {"external_id": "upgrade_user_123_11111111-1111-1111-1111-111111111111", "status": "PAID"},
            {},
            f"{main.BILLING_SERVICE_URL}/api/v1/billing/webhook/xendit",
        ),
        (
            "/api/v1/calculate/add",
            {"operand_a": 1, "operand_b": 2},
            {"Authorization": f"Bearer {_valid_gateway_token()}"},
            f"{main.MATH_ADD_SERVICE_URL}/api/v1/calculate/add",
        ),
        (
            "/api/v1/calculate/subtract",
            {"operand_a": 4, "operand_b": 2},
            {"Authorization": f"Bearer {_valid_gateway_token()}"},
            f"{main.MATH_SUBTRACT_SERVICE_URL}/api/v1/calculate/subtract",
        ),
        (
            "/api/v1/calculate/multiply",
            {"operand_a": 4, "operand_b": 2},
            {"Authorization": f"Bearer {_valid_gateway_token()}"},
            f"{main.MATH_MULTIPLY_SERVICE_URL}/api/v1/calculate/multiply",
        ),
        (
            "/api/v1/calculate/divide",
            {"operand_a": 4, "operand_b": 2},
            {"Authorization": f"Bearer {_valid_gateway_token()}"},
            f"{main.MATH_DIVIDE_SERVICE_URL}/api/v1/calculate/divide",
        ),
    ],
)
def test_routes_forward_to_expected_upstreams(path, payload, headers, expected_url):
    response = client.post(path, json=payload, headers=headers)

    assert response.status_code == 200
    assert FakeAsyncClient.requests[0]["url"] == expected_url


def test_protected_route_requires_bearer_header():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert "request_id" in body


def test_protected_route_rejects_invalid_jwt():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Invalid credentials"


def test_protected_route_rejects_expired_jwt():
    expired = jwt.encode(
        {
            "sub": "user-123",
            "iat": int((datetime.now(UTC) - timedelta(minutes=10)).timestamp()),
            "exp": int((datetime.now(UTC) - timedelta(minutes=5)).timestamp()),
        },
        "gateway-test-secret",
        algorithm="HS256",
    )

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Invalid credentials"


def test_valid_jwt_allows_protected_route():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 200
    assert FakeAsyncClient.requests[0]["url"].endswith("/api/v1/calculate/add")


def test_auth_routes_do_not_require_bearer_header():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )

    assert response.status_code == 200


def test_billing_status_requires_bearer_header():
    response = client.get("/api/v1/billing/status")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


def test_billing_subscribe_requires_bearer_header():
    response = client.post(
        "/api/v1/billing/subscribe",
        json={"plan_name": "Standard"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


def test_billing_webhook_bypasses_jwt():
    response = client.post(
        "/api/v1/billing/webhook/xendit",
        json={"external_id": "upgrade_user_123_11111111-1111-1111-1111-111111111111", "status": "PAID"},
    )

    assert response.status_code == 200
    assert FakeAsyncClient.requests[0]["url"] == f"{main.BILLING_SERVICE_URL}/api/v1/billing/webhook/xendit"


def test_billing_status_forwards_get_request_with_authorization():
    response = client.get(
        "/api/v1/billing/status",
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 200
    assert FakeAsyncClient.requests[0]["method"] == "GET"
    assert FakeAsyncClient.requests[0]["url"] == f"{main.BILLING_SERVICE_URL}/api/v1/billing/status"


def test_auth_me_route_forwards_get_request_with_authorization():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 200
    assert FakeAsyncClient.requests[0]["method"] == "GET"
    assert FakeAsyncClient.requests[0]["url"] == f"{main.IDENTITY_SERVICE_URL}/api/v1/auth/me"


def test_auth_me_route_requires_bearer_header():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_REQUESTS", 1)

    first = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )
    second = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"


def test_request_id_is_forwarded_and_returned():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={
            "Authorization": f"Bearer {_valid_gateway_token()}",
            "X-Request-ID": "req-123",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
    assert FakeAsyncClient.requests[0]["headers"]["X-Request-ID"] == "req-123"


def test_gateway_generates_request_id_when_missing():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 200
    generated = response.headers.get("X-Request-ID")
    assert generated
    assert FakeAsyncClient.requests[0]["headers"]["X-Request-ID"] == generated


def test_unified_error_shape_for_400_content_type_violation():
    response = client.post(
        "/api/v1/calculate/add",
        content="not-json",
        headers={
            "Authorization": f"Bearer {_valid_gateway_token()}",
            "Content-Type": "text/plain",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"
    assert "request_id" in body


def test_unified_error_shape_for_500_upstream_failure():
    FakeAsyncClient.responder = (
        lambda url, json, headers: httpx.RequestError("boom")
    )

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "request_id" in body


def test_upstream_error_is_normalized_to_unified_shape():
    FakeAsyncClient.responder = (
        lambda url, json, headers: FakeResponse(400, {"detail": "Malformed payload"})
    )

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["message"] == "Malformed payload"
    assert "request_id" in body


def test_successful_calculate_publishes_ledger_event():
    def responder(url, json, headers):
        if url.endswith("/api/v1/calculate/add"):
            return FakeResponse(
                200,
                {
                    "operation": "addition",
                    "result": 3,
                    "transaction_id": "txn-123",
                    "timestamp": "2026-03-31T10:00:00Z",
                },
            )
        if url.endswith("/api/v1/ledger/transactions"):
            return FakeResponse(202, {"status": "accepted"})
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}", "X-Request-ID": "req-abc"},
    )

    assert response.status_code == 200
    assert len(FakeAsyncClient.requests) == 2
    assert FakeAsyncClient.requests[1]["url"].endswith("/api/v1/ledger/transactions")
    ledger_payload = FakeAsyncClient.requests[1]["json"]
    assert ledger_payload["request_id"] == "req-abc"
    assert ledger_payload["operation_type"] == "addition"
    assert ledger_payload["operand_a"] == 1
    assert ledger_payload["operand_b"] == 2
    assert ledger_payload["result"] == 3
    assert isinstance(ledger_payload["math_transaction_id"], str)
    assert ledger_payload["math_transaction_id"]
    assert isinstance(ledger_payload["created_at"], str)
    assert ledger_payload["created_at"].endswith("Z")


def test_auth_route_does_not_publish_ledger_event():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert len(FakeAsyncClient.requests) == 1
    assert FakeAsyncClient.requests[0]["url"].endswith("/api/v1/auth/login")


def test_failed_calculate_does_not_publish_ledger_event():
    def responder(url, json, headers):
        if url.endswith("/api/v1/calculate/add"):
            return FakeResponse(400, {"detail": "Malformed payload"})
        if url.endswith("/api/v1/ledger/transactions"):
            return FakeResponse(202, {"status": "accepted"})
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 400
    assert len(FakeAsyncClient.requests) == 1
    assert FakeAsyncClient.requests[0]["url"].endswith("/api/v1/calculate/add")


def test_ledger_publish_failure_does_not_change_calculate_response():
    def responder(url, json, headers):
        if url.endswith("/api/v1/calculate/add"):
            return FakeResponse(
                200,
                {
                    "operation": "addition",
                    "result": 3,
                    "transaction_id": "txn-123",
                    "timestamp": "2026-03-31T10:00:00Z",
                },
            )
        if url.endswith("/api/v1/ledger/transactions"):
            return httpx.RequestError("ledger unavailable")
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "operation": "addition",
        "result": 3,
        "transaction_id": "txn-123",
        "timestamp": "2026-03-31T10:00:00Z",
    }
