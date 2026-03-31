from datetime import datetime
from pathlib import Path
from uuid import UUID
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app  # noqa: E402


client = TestClient(app)


def test_add_valid_integer_payload_returns_expected_contract():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 15, "operand_b": 27},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["operation"] == "addition"
    assert body["result"] == 42

    UUID(body["transaction_id"])
    datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00"))


def test_add_valid_decimal_payload_returns_expected_result():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 1.5, "operand_b": 2.25},
    )

    assert response.status_code == 200
    assert response.json()["result"] == 3.75


def test_add_valid_mixed_numeric_payload_returns_expected_result():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 2, "operand_b": 2.5},
    )

    assert response.status_code == 200
    assert response.json()["result"] == 4.5


def test_add_rejects_malformed_payload_with_missing_field():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": 15},
    )

    assert response.status_code == 400


def test_add_rejects_malformed_payload_with_wrong_type():
    response = client.post(
        "/api/v1/calculate/add",
        json={"operand_a": "15", "operand_b": 27},
    )

    assert response.status_code == 400
