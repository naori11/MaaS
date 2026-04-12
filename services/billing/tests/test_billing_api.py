import asyncio
from datetime import UTC, datetime, timedelta
import importlib.util
import os
from pathlib import Path
import sys
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICE_DIR))
sys.modules.pop("config", None)
sys.modules.pop("billing_main", None)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "billing-test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["XENDIT_SECRET_KEY"] = "xnd_test_key"
os.environ["XENDIT_CALLBACK_TOKEN"] = "test-callback-token"

_MAIN_PATH = _SERVICE_DIR / "main.py"
_SPEC = importlib.util.spec_from_file_location("billing_main", _MAIN_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load billing main module spec")
main = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(main)


def _token_for_user(user_id: str) -> str:
    return jwt.encode({"sub": user_id}, "billing-test-secret", algorithm="HS256")


def _get_invoice_intent_by_reference_id(reference_id: str):
    async def _query():
        session_factory = main._session_factory_or_500()
        async with session_factory() as session:
            result = await session.execute(
                select(main.InvoiceIntentORM).where(main.InvoiceIntentORM.external_id == reference_id)
            )
            return result.scalar_one_or_none()

    return asyncio.run(_query())


def _get_invoice_intents_for_user(user_id: str):
    async def _query():
        session_factory = main._session_factory_or_500()
        async with session_factory() as session:
            result = await session.execute(select(main.InvoiceIntentORM).where(main.InvoiceIntentORM.user_id == user_id))
            return list(result.scalars().all())

    return asyncio.run(_query())


def _set_invoice_intent_created_at(reference_id: str, created_at: datetime):
    async def _update():
        session_factory = main._session_factory_or_500()
        async with session_factory() as session:
            result = await session.execute(
                select(main.InvoiceIntentORM).where(main.InvoiceIntentORM.external_id == reference_id)
            )
            intent = result.scalar_one_or_none()
            if intent is None:
                return
            intent.created_at = created_at
            await session.commit()

    asyncio.run(_update())


def test_billing_status_defaults_to_free_when_no_subscription():
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    with TestClient(main.app) as client:
        response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "plan_name": "Free",
        "status": "active",
        "expires_at": None,
    }


def test_billing_status_requires_authorization_header():
    with TestClient(main.app) as client:
        response = client.get("/api/v1/billing/status")

    assert response.status_code == 401


def test_subscribe_creates_pending_subscription_and_persists_invoice_intent(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        assert reference_id.startswith("upgrade_")
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_test_components_sdk_key",
            payment_session_id="ps-test-std",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )

        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        intent = _get_invoice_intent_by_reference_id(observed["reference_id"])

    assert response.status_code == 200
    assert response.json() == {"components_sdk_key": "xnd_public_test_components_sdk_key"}

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["plan_name"] == "Standard"
    assert body["status"] == "pending_payment"
    assert body["expires_at"] is None

    assert intent is not None
    assert intent.user_id == user_id
    assert intent.plan_name == "Standard"
    assert intent.amount == 50
    assert intent.currency == "PHP"
    assert intent.xendit_invoice_id == "ps-test-std"
    assert intent.status == "pending_payment"
    assert intent.components_sdk_key == "xnd_public_test_components_sdk_key"
    assert intent.processed_at is None


def test_subscribe_supersedes_existing_pending_intent_for_different_plan(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    calls: list[tuple[str, int, str]] = []

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        calls.append((reference_id, amount, description))
        if amount == 50:
            return main.XenditPaymentSessionResult(
                components_sdk_key="xnd_public_std_sdk_key",
                payment_session_id="ps-test-std",
                currency="PHP",
            )

        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_premium_sdk_key",
            payment_session_id="ps-test-premium",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        first = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )
        second = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Premium"},
        )
        intents = _get_invoice_intents_for_user(user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(calls) == 2

    assert len(intents) == 2

    standard_intent = next(intent for intent in intents if intent.plan_name == "Standard")
    premium_intent = next(intent for intent in intents if intent.plan_name == "Premium")

    assert standard_intent.status == "superseded"
    assert premium_intent.status == "pending_payment"


def test_subscribe_reuses_same_plan_pending_intent_within_window(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    call_count = {"count": 0}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        call_count["count"] += 1
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_reuse_sdk_key",
            payment_session_id="ps-test-reuse",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        first = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )
        second = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )
        intents = _get_invoice_intents_for_user(user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == {"components_sdk_key": "xnd_public_reuse_sdk_key"}
    assert second.json() == {"components_sdk_key": "xnd_public_reuse_sdk_key"}
    assert call_count["count"] == 1

    assert len(intents) == 1
    assert intents[0].status == "pending_payment"


def test_subscribe_creates_new_intent_when_pending_intent_is_stale(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    calls: list[str] = []

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        calls.append(reference_id)
        return main.XenditPaymentSessionResult(
            components_sdk_key=f"xnd_public_stale_sdk_key_{len(calls)}",
            payment_session_id=f"ps-test-stale-{len(calls)}",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        first = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )
        assert first.status_code == 200

        first_reference_id = calls[0]
        _set_invoice_intent_created_at(first_reference_id, datetime.now(UTC) - timedelta(minutes=31))

        second = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )
        intents = _get_invoice_intents_for_user(user_id)

    assert second.status_code == 200
    assert len(calls) == 2

    assert len(intents) == 2

    stale_intent = next(intent for intent in intents if intent.external_id == first_reference_id)
    current_intent = next(intent for intent in intents if intent.external_id != first_reference_id)

    assert stale_intent.status == "superseded"
    assert current_intent.status == "pending_payment"


def test_subscribe_rejects_invalid_plan_name():
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Free"},
        )

    assert response.status_code == 400


def test_webhook_paid_activates_subscription_for_user(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-premium"
        assert amount == 250
        assert description == "Premium Plan Upgrade"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_premium_components_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        subscribe_response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Premium"},
        )

        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "payment_session.completed",
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "amount": 250,
                "currency": "PHP",
            },
        )

        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        intent = _get_invoice_intent_by_reference_id(observed["reference_id"])

    assert subscribe_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == {"received": True}

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["plan_name"] == "Premium"
    assert body["status"] == "active"
    assert isinstance(body["expires_at"], str)

    assert intent is not None
    assert intent.status == "paid"
    assert intent.processed_at is not None


def test_webhook_rejects_unknown_reference_id():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": "inv-unknown",
                "reference_id": f"upgrade_{user_id}_{uuid4()}",
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

    assert response.status_code == 400


def test_webhook_rejects_amount_mismatch(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-amount"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_amount_components_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        subscribe_response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )

        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "status": "PAID",
                "amount": 999,
                "currency": "PHP",
            },
        )

        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert subscribe_response.status_code == 200
    assert response.status_code == 400

    body = status_response.json()
    assert body["plan_name"] == "Standard"
    assert body["status"] == "pending_payment"


def test_webhook_rejects_currency_mismatch(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-currency"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_currency_components_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        subscribe_response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )

        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "status": "PAID",
                "amount": 50,
                "currency": "USD",
            },
        )

        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert subscribe_response.status_code == 200
    assert response.status_code == 400

    body = status_response.json()
    assert body["plan_name"] == "Standard"
    assert body["status"] == "pending_payment"


def test_webhook_rejects_payment_session_id_mismatch(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-match"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_id_components_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        subscribe_response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )

        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": "ps-test-mismatch",
                "reference_id": observed["reference_id"],
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

    assert subscribe_response.status_code == 200
    assert response.status_code == 400


def test_webhook_paid_is_idempotent(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-idempotent"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_idempotent_components_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        subscribe_response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )

        first = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

        first_status = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        second = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

        second_status = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        intent = _get_invoice_intent_by_reference_id(observed["reference_id"])

    assert subscribe_response.status_code == 200
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == {"received": True}
    assert second.json() == {"received": True}

    first_body = first_status.json()
    second_body = second_status.json()
    assert first_body["plan_name"] == "Standard"
    assert first_body["status"] == "active"
    assert first_body["expires_at"] == second_body["expires_at"]

    assert intent is not None
    assert intent.status == "paid"
    assert intent.processed_at is not None


def test_webhook_superseded_intent_is_acknowledged_without_subscription_activation(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-superseded"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_superseded_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        subscribe_response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )

        stale_reference = observed["reference_id"]

        client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Premium"},
        )

        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": observed["payment_session_id"],
                "reference_id": stale_reference,
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        stale_intent = _get_invoice_intent_by_reference_id(stale_reference)

    assert subscribe_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == {"received": True}

    status_body = status_response.json()
    assert status_body["plan_name"] == "Premium"
    assert status_body["status"] == "pending_payment"
    assert stale_intent is not None
    assert stale_intent.status == "superseded"
    assert stale_intent.processed_at is None


def test_webhook_non_paid_is_acknowledged_without_changes():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "reference_id": f"upgrade_{user_id}_{uuid4()}",
                "status": "PENDING",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_webhook_rejects_request_with_wrong_callback_token():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "wrong-token"},
            json={
                "reference_id": f"upgrade_{user_id}_{uuid4()}",
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

    assert response.status_code == 401


def test_webhook_rejects_request_with_missing_callback_token():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            json={
                "reference_id": f"upgrade_{user_id}_{uuid4()}",
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

    assert response.status_code == 401


def test_components_origins_defaults_to_https_localhost(monkeypatch):
    monkeypatch.delenv("XENDIT_COMPONENTS_ORIGINS", raising=False)

    assert main.get_xendit_components_origins() == ["https://localhost:3000"]


def test_components_origins_normalizes_to_https(monkeypatch):
    monkeypatch.setenv("XENDIT_COMPONENTS_ORIGINS", "http://localhost:3000,https://app.example.com,maas.example.com")

    assert main.get_xendit_components_origins() == [
        "https://localhost:3000",
        "https://app.example.com",
        "https://maas.example.com",
    ]


def test_subscribe_uses_configured_components_origins(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    monkeypatch.setenv("XENDIT_COMPONENTS_ORIGINS", "http://localhost:3000,https://staging.example.com")

    observed: dict[str, object] = {}

    class _FakeApiClient:
        def call_api(self, *_args, **kwargs):
            observed["body"] = kwargs.get("body")

            class _Response:
                @staticmethod
                def read():
                    return (
                        b'{"id":"ps-test-origins","currency":"PHP","components_sdk_key":"xnd_public_test_components_sdk_key"}'
                    )

            return _Response()

    class _FakeXenditModule:
        class exceptions:
            class OpenApiException(Exception):
                pass

            class XenditSdkException(Exception):
                pass

        @staticmethod
        def set_api_key(_key: str):
            return None

        @staticmethod
        def ApiClient():
            return _FakeApiClient()

    monkeypatch.setitem(sys.modules, "xendit", _FakeXenditModule)
    monkeypatch.setitem(sys.modules, "xendit.exceptions", _FakeXenditModule.exceptions)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Standard"},
        )

    assert response.status_code == 200
    assert response.json() == {"components_sdk_key": "xnd_public_test_components_sdk_key"}
    assert observed["body"]["components_configuration"]["origins"] == [
        "https://localhost:3000",
        "https://staging.example.com",
    ]
