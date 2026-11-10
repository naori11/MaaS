import asyncio
import importlib.util
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
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


# --- Catalog & Entitlement Tests ---

def test_billing_status_defaults_to_hobby_when_no_subscription():
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    with TestClient(main.app) as client:
        response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["plan_name"] == "Hobby"
    assert data["status"] == "active"
    assert data["expires_at"] is None
    assert data["can_cancel"] is False
    assert data["trial"]["eligible"] is True
    assert data["trial"]["is_active"] is False
    assert data["usage"]["limit"] == 50
    assert data["usage"]["unlimited"] is False


def test_billing_status_requires_authorization_header():
    with TestClient(main.app) as client:
        response = client.get("/api/v1/billing/status")

    assert response.status_code == 401


# --- Checkout & Subscription Setup Tests ---

def test_subscribe_creates_pending_subscription_and_persists_invoice_intent(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        assert reference_id.startswith("upgrade_")
        assert amount == 99
        assert description == "Pro Plan Monthly Subscription"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_test_components_sdk_key",
            payment_session_id="ps-test-pro",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Pro"},
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
    assert body["plan_name"] == "Pro"
    assert body["status"] == "pending_payment"
    assert body["expires_at"] is None

    assert intent is not None
    assert intent.user_id == user_id
    assert intent.plan_name == "Pro"
    assert intent.amount == 99
    assert intent.currency == "PHP"
    assert intent.xendit_invoice_id == "ps-test-pro"
    assert intent.status == "pending_payment"
    assert intent.components_sdk_key == "xnd_public_test_components_sdk_key"
    assert intent.processed_at is None


def test_subscribe_supersedes_previous_pending_intent(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    calls = []

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        call_num = len(calls) + 1
        calls.append(call_num)
        assert amount == 99
        return main.XenditPaymentSessionResult(
            components_sdk_key=f"xnd_public_sdk_key_{call_num}",
            payment_session_id=f"ps-test-{call_num}",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        first = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Pro"},
        )
        second = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Pro"},
        )
        intents = _get_invoice_intents_for_user(user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(calls) == 2
    assert len(intents) == 2
    assert intents[0].status == "superseded"
    assert intents[1].status == "pending_payment"


def test_subscribe_rejects_invalid_plan_name():
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Hobby"},
        )

    assert response.status_code == 400


# --- Webhooks & Recurring Lifecycle Tests ---

def test_webhook_paid_activates_subscription_for_user(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-pro"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_pro_components_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        subscribe_response = client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Pro"},
        )

        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "payment_session.completed",
                "data": {
                    "payment_session_id": observed["payment_session_id"],
                    "reference_id": observed["reference_id"],
                    "session_type": "SUBSCRIPTION",
                    "amount": 99,
                    "currency": "PHP",
                    "payment_id": "py-test-pro",
                    "recurring_plan_id": "repl-test-pro",
                },
            },
        )

        status_response = client.get(
            "/api/v1/billing/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        history_response = client.get(
            "/api/v1/billing/history",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert subscribe_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == {"received": True}

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["plan_name"] == "Pro"
    assert body["status"] == "active"
    assert isinstance(body["expires_at"], str)
    assert body["usage"]["unlimited"] is True

    # Real payment record persisted
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["status"] == "succeeded"
    assert history[0]["raw_amount"] == 99
    assert history[0]["id"]


def test_webhook_rejects_completed_session_without_payment_amount(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        return main.XenditPaymentSessionResult(
            components_sdk_key="sdk-key",
            payment_session_id="ps-missing-amount",
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        client.post("/api/v1/billing/subscribe", headers={"Authorization": f"Bearer {token}"}, json={"plan_name": "Pro"})
        response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "payment_session.completed",
                "data": {
                    "payment_session_id": "ps-missing-amount",
                    "reference_id": observed["reference_id"],
                    "currency": "PHP",
                    "session_type": "SUBSCRIPTION",
                },
            },
        )
        status = client.get("/api/v1/billing/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 400
    assert status.json()["status"] == "pending_payment"


def test_webhook_paid_is_idempotent(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-idempotent"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_idempotent_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        client.post(
            "/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_name": "Pro"},
        )

        payload = {
            "id": observed["payment_session_id"],
            "reference_id": observed["reference_id"],
            "event": "payment_session.completed",
            "amount": 99,
            "currency": "PHP",
        }

        first = client.post("/api/v1/billing/webhook/xendit", headers={"x-callback-token": "test-callback-token"}, json=payload)
        second = client.post("/api/v1/billing/webhook/xendit", headers={"x-callback-token": "test-callback-token"}, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200


def test_webhook_cycle_failure_enters_grace_period_and_recovers(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-cycle"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_cycle_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        # 1. Initial activation
        client.post("/api/v1/billing/subscribe", headers={"Authorization": f"Bearer {token}"}, json={"plan_name": "Pro"})
        client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "payment_session.completed",
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "amount": 99,
                "currency": "PHP",
                "data": {"id": "plan_test_cycle_1"},
            },
        )

        # 2. Cycle failure webhook
        fail_response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "recurring.cycle.failed",
                "id": "evt_fail_1",
                "data": {"plan_id": "plan_test_cycle_1", "id": "cycle_fail_1"},
            },
        )
        assert fail_response.status_code == 200

        # User is in past_due with 7-day grace period, but retains Pro access!
        status_during_grace = client.get("/api/v1/billing/status", headers={"Authorization": f"Bearer {token}"}).json()
        assert status_during_grace["plan_name"] == "Pro"
        assert status_during_grace["status"] == "past_due"
        assert status_during_grace["grace_period_deadline"] is not None
        assert status_during_grace["usage"]["unlimited"] is True

        # 3. Recovery webhook within 7 days
        recover_response = client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "recurring.cycle.succeeded",
                "id": "evt_recov_1",
                "data": {"plan_id": "plan_test_cycle_1", "id": "cycle_recov_1"},
            },
        )
        assert recover_response.status_code == 200

        # Restores active status and clears grace period
        status_after_recovery = client.get("/api/v1/billing/status", headers={"Authorization": f"Bearer {token}"}).json()
        assert status_after_recovery["plan_name"] == "Pro"
        assert status_after_recovery["status"] == "active"
        assert status_after_recovery["grace_period_deadline"] is None


def test_cancellation_preserves_access_at_period_end(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-cancel"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_cancel_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        # Subscribe and activate
        client.post("/api/v1/billing/subscribe", headers={"Authorization": f"Bearer {token}"}, json={"plan_name": "Pro"})
        client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "payment_session.completed",
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "amount": 99,
                "currency": "PHP",
            },
        )

        # Cancel renewal at period end
        cancel_res = client.post("/api/v1/billing/cancel", headers={"Authorization": f"Bearer {token}"})
        assert cancel_res.status_code == 200
        body = cancel_res.json()
        assert body["cancel_at_period_end"] is True
        assert body["status"] == "active"
        assert body["usage"]["unlimited"] is True


# --- Pro Preview Trial Tests ---

def test_pro_preview_trial_lifecycle():
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    with TestClient(main.app) as client:
        # Check initial eligibility
        status_before = client.get("/api/v1/billing/status", headers={"Authorization": f"Bearer {token}"}).json()
        assert status_before["trial"]["eligible"] is True
        assert status_before["trial"]["is_active"] is False

        # Explicit start of 7-day trial
        trial_start = client.post("/api/v1/billing/trial/start", headers={"Authorization": f"Bearer {token}"})
        assert trial_start.status_code == 200
        assert trial_start.json()["days_remaining"] == 7

        # Status now shows active Pro with unlimited calculations during preview
        status_during = client.get("/api/v1/billing/status", headers={"Authorization": f"Bearer {token}"}).json()
        assert status_during["plan_name"] == "Pro"
        assert status_during["status"] == "active"
        assert status_during["trial"]["is_active"] is True
        assert status_during["trial"]["eligible"] is False
        assert status_during["usage"]["unlimited"] is True

        # Second attempt to start trial is rejected (one-time eligibility)
        trial_second = client.post("/api/v1/billing/trial/start", headers={"Authorization": f"Bearer {token}"})
        assert trial_second.status_code == 400


# --- Usage Reservation & Quota Boundary Tests ---

def test_usage_reservation_commit_and_release_flow():
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    with TestClient(main.app) as client:
        # 1. Hobby user reserve
        reserve_res = client.post("/api/v1/billing/usage/reserve", headers={"Authorization": f"Bearer {token}"})
        assert reserve_res.status_code == 200
        data = reserve_res.json()
        assert data["allowed"] is True
        assert data["unlimited"] is False
        assert data["reservation_id"] is not None
        res_id = data["reservation_id"]

        # Commit reservation
        commit_res = client.post(
            "/api/v1/billing/usage/commit",
            headers={"Authorization": f"Bearer {token}"},
            json={"reservation_id": res_id},
        )
        assert commit_res.status_code == 200

        # Check usage count incremented
        usage = client.get("/api/v1/billing/usage", headers={"Authorization": f"Bearer {token}"}).json()
        assert usage["used"] == 1
        assert usage["limit"] == 50

        # 2. Release reservation test
        reserve_res2 = client.post("/api/v1/billing/usage/reserve", headers={"Authorization": f"Bearer {token}"})
        res_id2 = reserve_res2.json()["reservation_id"]
        client.post(
            "/api/v1/billing/usage/release",
            headers={"Authorization": f"Bearer {token}"},
            json={"reservation_id": res_id2},
        )

        usage2 = client.get("/api/v1/billing/usage", headers={"Authorization": f"Bearer {token}"}).json()
        assert usage2["used"] == 1  # Not incremented on release


def test_hobby_limit_reached_returns_429():
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)

    with TestClient(main.app) as client:
        # Manually set used_count to 50
        async def _set_max_usage():
            session_factory = main._session_factory_or_500()
            today_str = datetime.now(UTC).strftime("%Y-%m-%d")
            async with session_factory() as session:
                session.add(main.DailyUsageORM(user_id=user_id, usage_date=today_str, used_count=50, reserved_count=0))
                await session.commit()

        asyncio.run(_set_max_usage())

        # Attempt to reserve quota
        res = client.post("/api/v1/billing/usage/reserve", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 429
        assert "Daily calculation limit reached" in res.json()["detail"]


# --- Receipts Test ---

def test_payment_receipt_retrieval(monkeypatch):
    user_id = f"user-{uuid4().hex}"
    token = _token_for_user(user_id)
    observed: dict[str, str] = {}

    def _fake_payment_session(*, reference_id: str, amount: int, description: str):
        observed["reference_id"] = reference_id
        observed["payment_session_id"] = "ps-test-receipt"
        return main.XenditPaymentSessionResult(
            components_sdk_key="xnd_public_receipt_sdk_key",
            payment_session_id=observed["payment_session_id"],
            currency="PHP",
        )

    monkeypatch.setattr(main, "_create_xendit_payment_session", _fake_payment_session)

    with TestClient(main.app) as client:
        client.post("/api/v1/billing/subscribe", headers={"Authorization": f"Bearer {token}"}, json={"plan_name": "Pro"})
        client.post(
            "/api/v1/billing/webhook/xendit",
            headers={"x-callback-token": "test-callback-token"},
            json={
                "event": "payment_session.completed",
                "id": observed["payment_session_id"],
                "reference_id": observed["reference_id"],
                "amount": 99,
                "currency": "PHP",
            },
        )

        history = client.get("/api/v1/billing/history", headers={"Authorization": f"Bearer {token}"}).json()
        payment_id = history[0]["id"]

        receipt_res = client.get(f"/api/v1/billing/receipts/{payment_id}", headers={"Authorization": f"Bearer {token}"})
        assert receipt_res.status_code == 200
        receipt = receipt_res.json()
        assert receipt["amount"] == "₱99.00"
        assert "Math as a Service Receipt" in receipt["receipt_text"]


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


