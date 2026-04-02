import importlib.util
import os
from pathlib import Path
import sys
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICE_DIR))
sys.modules.pop("config", None)
sys.modules.pop("billing_main", None)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "billing-test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["XENDIT_SECRET_KEY"] = "xnd_test_key"

_MAIN_PATH = _SERVICE_DIR / "main.py"
_SPEC = importlib.util.spec_from_file_location("billing_main", _MAIN_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load billing main module spec")
main = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(main)


def _token_for_user(user_id: str) -> str:
    return jwt.encode({"sub": user_id}, "billing-test-secret", algorithm="HS256")


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


def test_subscribe_creates_pending_subscription_and_returns_invoice_url(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    def _fake_invoice(*, external_id: str, amount: int, description: str) -> str:
        assert external_id.startswith(f"upgrade_{user_id}_")
        assert amount == 50
        assert description == "Standard Plan Upgrade"
        return "https://pay.xendit.co/test-invoice"

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

    assert response.status_code == 200
    assert response.json() == {"invoice_url": "https://pay.xendit.co/test-invoice"}

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["plan_name"] == "Standard"
    assert body["status"] == "pending_payment"
    assert body["expires_at"] is None


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


def test_webhook_paid_activates_subscription_for_user():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            json={
                "external_id": f"upgrade_{user_id}_{uuid4()}",
                "status": "PAID",
                "paid_plan_name": "Premium",
            },
        )

        token = _token_for_user(user_id)
        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["plan_name"] == "Premium"
    assert body["status"] == "active"
    assert isinstance(body["expires_at"], str)


def test_webhook_non_paid_is_acknowledged_without_changes():
    user_id = f"user-{uuid4().hex}"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            json={
                "external_id": f"upgrade_{user_id}_{uuid4()}",
                "status": "PENDING",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}
