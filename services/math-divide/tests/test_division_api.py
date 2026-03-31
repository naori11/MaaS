from datetime import datetime
from pathlib import Path
from uuid import UUID
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app  # noqa: E402


client = TestClient(app)


def test_divide_valid_payload_returns_expected_contract():
    response = client.post(
        "/api/v1/calculate/divide",
        json={"operand_a": 84, "operand_b": 2},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["operation"] == "division"
    assert body["result"] == 42

    UUID(body["transaction_id"])
    datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00"))


def test_divide_rejects_divide_by_zero_with_400():
    response = client.post(
        "/api/v1/calculate/divide",
        json={"operand_a": 84, "operand_b": 0},
    )

    assert response.status_code == 400


def test_divide_rejects_malformed_payload_with_400():
    response = client.post(
        "/api/v1/calculate/divide",
        json={"operand_a": 84},
    )

    assert response.status_code == 400
