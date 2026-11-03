import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICE_DIR))
sys.modules.pop("config", None)

_SPEC = importlib.util.spec_from_file_location("ledger_persistence_unit_main", _SERVICE_DIR / "main.py")
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load ledger main module spec")
main = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(main)


class RecordingSession:
    def __init__(self, *, fail_commit: bool = False):
        self.fail_commit = fail_commit
        self.added: list[Any] = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def add(self, record):
        self.added.append(record)

    async def commit(self):
        if self.fail_commit:
            raise main.SQLAlchemyError("database unavailable")
        self.committed = True


def _payload() -> dict[str, Any]:
    return {
        "request_id": "req-unit",
        "operation_type": "addition",
        "operand_a": 10,
        "operand_b": 5,
        "result": 15,
        "math_transaction_id": "txn-unit",
        "created_at": "2026-10-31T10:00:00Z",
    }


def test_ledger_confirms_only_after_database_commit(monkeypatch):
    session = RecordingSession()
    monkeypatch.setattr(main, "_SESSION_FACTORY", lambda: session)

    response = TestClient(main.app).post("/api/v1/ledger/transactions", json=_payload())

    assert response.status_code == 201
    assert response.json() == {"status": "created"}
    assert session.committed is True
    assert session.added[0].math_transaction_id == "txn-unit"


def test_ledger_returns_503_when_database_commit_fails(monkeypatch):
    session = RecordingSession(fail_commit=True)
    monkeypatch.setattr(main, "_SESSION_FACTORY", lambda: session)

    response = TestClient(main.app).post("/api/v1/ledger/transactions", json=_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "Ledger database unavailable"}
    assert session.committed is False
