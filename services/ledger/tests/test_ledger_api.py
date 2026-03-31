import importlib.util
from pathlib import Path
import sys
from time import sleep, time

from fastapi.testclient import TestClient

_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICE_DIR))
sys.modules.pop("config", None)

_MAIN_PATH = _SERVICE_DIR / "main.py"
_SPEC = importlib.util.spec_from_file_location("ledger_main", _MAIN_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load ledger main module spec")
main = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(main)



def _wait_for_records(count: int, timeout_seconds: float = 1.0) -> None:
    deadline = time() + timeout_seconds
    while time() < deadline:
        if len(main._RECORDS) >= count:
            return
        sleep(0.01)
    raise AssertionError(f"Expected at least {count} records, got {len(main._RECORDS)}")


def _valid_payload(request_id: str = "req-123") -> dict:
    return {
        "request_id": request_id,
        "operation_type": "addition",
        "operand_a": 15,
        "operand_b": 27,
        "result": 42,
        "math_transaction_id": "a1b2c3d4-e5f6-7890",
        "created_at": "2026-03-30T20:12:30Z",
    }


def setup_function() -> None:
    main._RECORDS.clear()


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


def test_get_transactions_returns_recent_records_with_limit():
    with TestClient(main.app) as client:
        client.post("/api/v1/ledger/transactions", json=_valid_payload("req-1"))
        client.post("/api/v1/ledger/transactions", json=_valid_payload("req-2"))
        client.post("/api/v1/ledger/transactions", json=_valid_payload("req-3"))

        _wait_for_records(3)
        response = client.get("/api/v1/ledger/transactions?limit=2")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["request_id"] == "req-3"
    assert body["items"][1]["request_id"] == "req-2"


def test_queue_full_returns_503(monkeypatch):
    with TestClient(main.app) as client:
        full_queue = main.asyncio.Queue(maxsize=1)
        full_queue.put_nowait(_valid_payload())
        monkeypatch.setattr(main, "_QUEUE", full_queue)

        response = client.post("/api/v1/ledger/transactions", json=_valid_payload("req-overflow"))

    assert response.status_code == 503
    assert response.json() == {"detail": "Ledger queue is full"}
