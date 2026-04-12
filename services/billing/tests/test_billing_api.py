import asyncio
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


def _get_invoice_intent_by_external_id(external_id: str):
    async def _query():
        session_factory = main._session_factory_or_500()
        async with session_factory() as session:
            result = await session.execute(
                select(main.InvoiceIntentORM).where(main.InvoiceIntentORM.external_id == external_id)
            )
            return result.scalar_one_or_none()

    return asyncio.run(_query())


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

    def _fake_invoice(*, external_id: str, amount: int, description: str):
        observed["external_id"] = external_id
        assert external_id.startswith("upgrade_")
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditInvoiceResult(
            invoice_url="https://pay.xendit.co/test-invoice",
            invoice_id="inv-test-std",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_invoice", _fake_invoice)

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

        intent = _get_invoice_intent_by_external_id(observed["external_id"])

    assert response.status_code == 200
    assert response.json() == {"invoice_url": "https://pay.xendit.co/test-invoice"}

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
    assert intent.xendit_invoice_id == "inv-test-std"
    assert intent.status == "pending_payment"
    assert intent.processed_at is None


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

    def _fake_invoice(*, external_id: str, amount: int, description: str):
        observed["external_id"] = external_id
        observed["invoice_id"] = "inv-test-premium"
        assert amount == 250
        assert description == "Premium Plan Upgrade"
        return main.XenditInvoiceResult(
            invoice_url="https://pay.xendit.co/premium-invoice",
            invoice_id=observed["invoice_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_invoice", _fake_invoice)

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
                "id": observed["invoice_id"],
                "external_id": observed["external_id"],
                "status": "PAID",
                "amount": 250,
                "currency": "PHP",
                "paid_plan_name": "Standard",
            },
        )

        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        intent = _get_invoice_intent_by_external_id(observed["external_id"])

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


def test_webhook_rejects_unknown_external_id():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "id": "inv-unknown",
                "external_id": f"upgrade_{user_id}_{uuid4()}",
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

    def _fake_invoice(*, external_id: str, amount: int, description: str):
        observed["external_id"] = external_id
        observed["invoice_id"] = "inv-test-amount"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditInvoiceResult(
            invoice_url="https://pay.xendit.co/amount-invoice",
            invoice_id=observed["invoice_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_invoice", _fake_invoice)

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
                "id": observed["invoice_id"],
                "external_id": observed["external_id"],
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

    def _fake_invoice(*, external_id: str, amount: int, description: str):
        observed["external_id"] = external_id
        observed["invoice_id"] = "inv-test-currency"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditInvoiceResult(
            invoice_url="https://pay.xendit.co/currency-invoice",
            invoice_id=observed["invoice_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_invoice", _fake_invoice)

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
                "id": observed["invoice_id"],
                "external_id": observed["external_id"],
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


def test_webhook_rejects_invoice_id_mismatch(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_invoice(*, external_id: str, amount: int, description: str):
        observed["external_id"] = external_id
        observed["invoice_id"] = "inv-test-match"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditInvoiceResult(
            invoice_url="https://pay.xendit.co/id-invoice",
            invoice_id=observed["invoice_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_invoice", _fake_invoice)

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
                "id": "inv-test-mismatch",
                "external_id": observed["external_id"],
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

    def _fake_invoice(*, external_id: str, amount: int, description: str):
        observed["external_id"] = external_id
        observed["invoice_id"] = "inv-test-idempotent"
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return main.XenditInvoiceResult(
            invoice_url="https://pay.xendit.co/idempotent-invoice",
            invoice_id=observed["invoice_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_invoice", _fake_invoice)

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
                "id": observed["invoice_id"],
                "external_id": observed["external_id"],
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
                "id": observed["invoice_id"],
                "external_id": observed["external_id"],
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

        second_status = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        intent = _get_invoice_intent_by_external_id(observed["external_id"])

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


def test_webhook_non_paid_is_acknowledged_without_changes():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "external_id": f"upgrade_{user_id}_{uuid4()}",
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
                "external_id": f"upgrade_{user_id}_{uuid4()}",
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
                "external_id": f"upgrade_{user_id}_{uuid4()}",
                "status": "PAID",
                "amount": 50,
                "currency": "PHP",
            },
        )

    assert response.status_code == 401
