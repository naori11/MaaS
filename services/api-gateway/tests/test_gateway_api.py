import importlib.util
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, Self

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
    def __init__(self, status_code: int, body: dict[str, Any], headers: dict[str, str] | None = None, content: bytes = b""):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {"Content-Type": "application/json"}
        self.content = content

    def json(self) -> dict[str, Any]:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "upstream error",
                request=httpx.Request("POST", "http://test"),
                response=httpx.Response(self.status_code),
            )


Responder = Callable[[str, dict[str, Any], dict[str, str]], FakeResponse | Exception]


class FakeAsyncClient:
    requests: ClassVar[list[dict[str, Any]]] = []
    responder: ClassVar[Responder] = lambda url, json, headers: FakeResponse(200, {"ok": True})

    def __init__(self, *args: Any, **kwargs: Any):
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
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

    def default_responder(url, json, headers):
        if url.endswith("/api/v1/billing/usage/reserve"):
            return FakeResponse(200, {"allowed": True, "reservation_id": "res-test-123"})
        if url.endswith(("/api/v1/billing/usage/commit", "/api/v1/billing/usage/release")):
            return FakeResponse(200, {"status": "ok"})
        if url.endswith("/api/v1/billing/status"):
            return FakeResponse(200, {"plan_name": "Pro", "status": "active"})
        if "/api/v1/calculate/" in url:
            return FakeResponse(200, {"result": 3})
        if url.endswith("/api/v1/ledger/transactions"):
            return FakeResponse(201, {"status": "created", "items": []})
        if url.endswith("/api/v1/ledger/export"):
            return FakeResponse(200, {}, headers={"Content-Type": "text/csv"}, content=b"a,b,c\n1,2,3")
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = default_responder
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
            {"plan_name": "Pro"},
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
    matched = [req for req in FakeAsyncClient.requests if req["url"] == expected_url]
    assert len(matched) == 1
    assert matched[0]["url"] == expected_url


def test_malformed_json_returns_consistent_error():
    response = client.post(
        "/api/v1/auth/login",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert "Malformed payload" in payload["error"]["message"]
    assert "request_id" in payload


def test_invalid_content_type_returns_bad_request():
    response = client.post(
        "/api/v1/auth/login",
        content='{"email":"a@b.com","password":"pwd"}',
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert "Content-Type must be application/json" in payload["error"]["message"]
    assert "request_id" in payload


def test_missing_jwt_on_protected_route_returns_unauthorized():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert "request_id" in payload


def test_invalid_jwt_returns_unauthorized():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert "request_id" in payload


def test_valid_jwt_allows_protected_route():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 200
    math_reqs = [r for r in FakeAsyncClient.requests if "/api/v1/calculate/add" in r["url"]]
    assert len(math_reqs) == 1
    assert math_reqs[0]["headers"]["X-User-Id"] == "user-123"


def test_rate_limiting_blocks_after_threshold():
    for _ in range(60):
        client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "secret"},
        )

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )

    assert blocked.status_code == 429
    payload = blocked.json()
    assert payload["error"]["code"] == "rate_limited"
    assert payload["error"]["message"] == "Rate limit exceeded"


def test_rate_limit_resets_across_windows(monkeypatch):
    current_time = 1_000.0

    def fake_time() -> float:
        return current_time

    monkeypatch.setattr(main, "time", fake_time)

    for _ in range(60):
        client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "secret"},
        )

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )
    assert blocked.status_code == 429

    current_time += 61.0

    allowed = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )
    assert allowed.status_code == 200


def test_billing_status_forwards_get_request_with_authorization():
    token = _valid_gateway_token()
    response = client.get(
        "/api/v1/billing/status",
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req-status-123"},
    )

    assert response.status_code == 200
    billing_reqs = [r for r in FakeAsyncClient.requests if "/api/v1/billing/status" in r["url"]]
    assert len(billing_reqs) >= 1
    req = billing_reqs[0]
    assert req["method"] == "GET"
    assert req["url"] == f"{main.BILLING_SERVICE_URL}/api/v1/billing/status"
    assert req["headers"]["X-User-Id"] == "user-123"
    assert req["headers"]["Authorization"] == f"Bearer {token}"
    assert req["headers"]["X-Request-ID"] == "req-status-123"


def test_auth_me_route_forwards_get_request_with_authorization():
    token = _valid_gateway_token()
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req-me-123"},
    )

    assert response.status_code == 200
    assert len(FakeAsyncClient.requests) == 1
    req = FakeAsyncClient.requests[0]
    assert req["method"] == "GET"
    assert req["url"] == f"{main.IDENTITY_SERVICE_URL}/api/v1/auth/me"
    assert req["headers"]["X-User-Id"] == "user-123"
    assert req["headers"]["Authorization"] == f"Bearer {token}"
    assert req["headers"]["X-Request-ID"] == "req-me-123"


def test_ledger_transactions_forwards_get_with_authorization_and_query_params():
    response = client.get(
        "/api/v1/ledger/transactions?limit=25&cursor=abc",
        headers={"Authorization": f"Bearer {_valid_gateway_token()}", "X-Request-ID": "req-ledger-123"},
    )

    assert response.status_code == 200
    ledger_reqs = [r for r in FakeAsyncClient.requests if "/api/v1/ledger/transactions" in r["url"]]
    assert len(ledger_reqs) == 1
    req = ledger_reqs[0]
    assert req["method"] == "GET"
    assert req["url"] == f"{main.LEDGER_SERVICE_URL}/api/v1/ledger/transactions?limit=25&cursor=abc"
    assert req["headers"]["X-User-Id"] == "user-123"
    assert req["headers"]["X-User-Plan"] == "Pro"
    assert req["headers"]["X-Request-ID"] == "req-ledger-123"


def test_successful_calculate_publishes_ledger_event_and_commits_usage():
    def responder(url, json, headers):
        if url.endswith("/api/v1/billing/usage/reserve"):
            return FakeResponse(200, {"allowed": True, "reservation_id": "res-success-123"})
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
            return FakeResponse(201, {"status": "created"})
        if url.endswith("/api/v1/billing/usage/commit"):
            return FakeResponse(200, {"status": "committed"})
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}", "X-Request-ID": "req-abc"},
    )

    assert response.status_code == 200
    urls = [r["url"] for r in FakeAsyncClient.requests]
    assert any("/api/v1/billing/usage/reserve" in u for u in urls)
    assert any("/api/v1/calculate/add" in u for u in urls)
    assert any("/api/v1/ledger/transactions" in u for u in urls)
    assert any("/api/v1/billing/usage/commit" in u for u in urls)


def test_failed_calculate_does_not_publish_ledger_event_and_releases_usage():
    def responder(url, json, headers):
        if url.endswith("/api/v1/billing/usage/reserve"):
            return FakeResponse(200, {"allowed": True, "reservation_id": "res-fail-123"})
        if url.endswith("/api/v1/calculate/add"):
            return FakeResponse(400, {"detail": "Malformed payload"})
        if url.endswith("/api/v1/billing/usage/release"):
            return FakeResponse(200, {"status": "released"})
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 400
    urls = [r["url"] for r in FakeAsyncClient.requests]
    assert any("/api/v1/billing/usage/reserve" in u for u in urls)
    assert any("/api/v1/calculate/add" in u for u in urls)
    assert not any("/api/v1/ledger/transactions" in u for u in urls)
    assert any("/api/v1/billing/usage/release" in u for u in urls)


def test_calculation_fails_closed_when_usage_reservation_service_is_unavailable():
    def responder(url, json, headers):
        if url.endswith("/api/v1/billing/usage/reserve"):
            return FakeResponse(500, {"detail": "billing unavailable"})
        return FakeResponse(200, {"result": 3})

    FakeAsyncClient.responder = responder

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 503
    assert "could not be verified" in response.json()["error"]["message"]
    assert not any("/api/v1/calculate/add" in request["url"] for request in FakeAsyncClient.requests)


def test_quota_exceeded_returns_consistent_error():
    def responder(url, json, headers):
        if url.endswith("/api/v1/billing/usage/reserve"):
            return FakeResponse(
                429,
                {"detail": "Daily calculation limit reached (50/50). Upgrade to Pro for unlimited calculations."},
            )
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1, "operand_b": 2},
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 429
    err = response.json()["error"]
    assert err["code"] == "quota_exceeded"
    assert "Daily calculation limit reached" in err["message"]
    # No math calculation was attempted
    assert not any("/api/v1/calculate/add" in r["url"] for r in FakeAsyncClient.requests)


def test_ledger_export_forbidden_for_hobby():
    def responder(url, json, headers):
        if url.endswith("/api/v1/billing/status"):
            return FakeResponse(200, {"plan_name": "Hobby", "status": "active"})
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.get(
        "/api/v1/ledger/export",
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 403
    assert "only available on the Pro plan" in response.json()["error"]["message"]


def test_ledger_export_allowed_for_pro():
    def responder(url, json, headers):
        if url.endswith("/api/v1/billing/status"):
            return FakeResponse(200, {"plan_name": "Pro", "status": "active"})
        if url.endswith("/api/v1/ledger/export"):
            return FakeResponse(
                200,
                {},
                headers={"Content-Type": "text/csv", "Content-Disposition": "attachment; filename=math-history.csv"},
                content=b"id,request_id,operation_type,operand_a,operand_b,result,math_transaction_id,created_at\n1,req,add,1,2,3,txn,2026-01-01Z",
            )
        return FakeResponse(200, {"ok": True})

    FakeAsyncClient.responder = responder

    response = client.get(
        "/api/v1/ledger/export",
        headers={"Authorization": f"Bearer {_valid_gateway_token()}"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["Content-Type"]
    assert b"operation_type" in response.content
