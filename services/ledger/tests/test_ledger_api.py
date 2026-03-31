import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse
from uuid import uuid4

import importlib
import pytest
from fastapi.testclient import TestClient


_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICE_DIR))
sys.modules.pop("config", None)

TEST_DATABASE_URL_RAW = os.getenv("LEDGER_TEST_DATABASE_URL")
if not TEST_DATABASE_URL_RAW:
    raise RuntimeError("LEDGER_TEST_DATABASE_URL must be set for dedicated ledger test database")

TEST_DATABASE_URL = TEST_DATABASE_URL_RAW
parsed = urlparse(TEST_DATABASE_URL)
database_name = parsed.path.lstrip("/")
if database_name == "ledger_db":
    raise RuntimeError("Refusing to run tests against ledger_db. Use a dedicated test database.")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

_MAIN_PATH = _SERVICE_DIR / "main.py"
_SPEC = importlib.util.spec_from_file_location("ledger_main", _MAIN_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load ledger main module spec")
main = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(main)



def _asyncpg_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return database_url


async def _truncate_ledger_records() -> None:
    asyncpg = importlib.import_module("asyncpg")
    connection = await asyncpg.connect(_asyncpg_url(TEST_DATABASE_URL))
    try:
        table_name = await connection.fetchval("SELECT to_regclass('public.ledger_records')")
        if table_name is None:
            return
        await connection.execute("TRUNCATE TABLE ledger_records RESTART IDENTITY")
    finally:
        await connection.close()


@pytest.fixture(autouse=True)
def clear_ledger_table() -> None:
    asyncio.run(_truncate_ledger_records())


def _valid_payload(request_id: str = "req-123", created_at: str = "2026-03-30T20:12:30Z") -> dict:
    unique_suffix = uuid4().hex
    return {
        "request_id": request_id,
        "operation_type": "addition",
        "operand_a": 15,
        "operand_b": 27,
        "result": 42,
        "math_transaction_id": f"txn-{request_id}-{unique_suffix}",
        "created_at": created_at,
    }


def test_enqueue_valid_event_returns_202():
    with TestClient(main.app) as client:
        response = client.post("/api/v1/ledger/transactions", json=_valid_payload())

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


def test_enqueue_malformed_payload_returns_400():
    payload = _valid_payload()
    payload.pop("request_id")

    with TestClient(main.app) as client:
        response = client.post("/api/v1/ledger/transactions", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "Malformed payload"}


def test_enqueue_invalid_created_at_returns_400():
    payload = _valid_payload()
    payload["created_at"] = "not-a-date"

    with TestClient(main.app) as client:
        response = client.post("/api/v1/ledger/transactions", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "Malformed payload"}


def _wait_for_transaction_ids(client: TestClient, transaction_ids: list[str], timeout_seconds: float = 3.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get("/api/v1/ledger/transactions?limit=100")
        if response.status_code == 200:
            seen_ids = {item["math_transaction_id"] for item in response.json()["items"]}
            if set(transaction_ids).issubset(seen_ids):
                return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for transaction ids: {transaction_ids}")


def test_get_transactions_returns_recent_records_with_limit():
    with TestClient(main.app) as client:
        payload_1 = _valid_payload(f"req-{uuid4().hex}", "2099-01-01T00:00:01Z")
        payload_2 = _valid_payload(f"req-{uuid4().hex}", "2099-01-01T00:00:02Z")
        payload_3 = _valid_payload(f"req-{uuid4().hex}", "2099-01-01T00:00:03Z")

        client.post("/api/v1/ledger/transactions", json=payload_1)
        client.post("/api/v1/ledger/transactions", json=payload_2)
        client.post("/api/v1/ledger/transactions", json=payload_3)

        _wait_for_transaction_ids(
            client,
            [
                payload_1["math_transaction_id"],
                payload_2["math_transaction_id"],
                payload_3["math_transaction_id"],
            ],
        )
        response = client.get("/api/v1/ledger/transactions?limit=2")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    transaction_ids_in_response = [item["math_transaction_id"] for item in body["items"]]
    assert payload_3["math_transaction_id"] in transaction_ids_in_response
    assert payload_2["math_transaction_id"] in transaction_ids_in_response


def test_queue_full_returns_503(monkeypatch):
    with TestClient(main.app) as client:
        full_queue = main.asyncio.Queue(maxsize=1)
        full_queue.put_nowait(main.LedgerEventIn(**_valid_payload()))
        monkeypatch.setattr(main, "_QUEUE", full_queue)

        response = client.post("/api/v1/ledger/transactions", json=_valid_payload("req-overflow"))

    assert response.status_code == 503
    assert response.json() == {"detail": "Ledger queue is full"}
