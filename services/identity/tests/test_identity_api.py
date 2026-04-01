import importlib.util
import os
from pathlib import Path
import sys
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient

_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICE_DIR))
sys.modules.pop("config", None)
sys.modules.pop("identity_main", None)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "identity-test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRES_SECONDS"] = "3600"

_MAIN_PATH = _SERVICE_DIR / "main.py"
_SPEC = importlib.util.spec_from_file_location("identity_main", _MAIN_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load identity main module spec")
main = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(main)


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def test_register_success_returns_expected_contract(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 201
    body = response.json()
    UUID(body["id"])
    assert body["email"] == "user@example.com"
    assert isinstance(body["created_at"], str)
    assert body["created_at"].endswith("Z")


def test_register_duplicate_email_returns_409(client):
    first = client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "supersecret123"},
    )
    second = client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "supersecret123"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"


def test_login_success_returns_jwt_token(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "supersecret123"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600

    decoded = jwt.decode(body["access_token"], "identity-test-secret", algorithms=["HS256"])
    assert isinstance(decoded["sub"], str)


def test_login_invalid_credentials_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "invalid@example.com", "password": "supersecret123"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "invalid@example.com", "password": "wrongpassword123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_me_with_valid_token_returns_user(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "supersecret123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "supersecret123"},
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert register.status_code == 201
    assert login.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == register.json()["id"]
    assert body["email"] == "me@example.com"


def test_me_with_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_me_with_missing_authorization_returns_401(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid Authorization header"


def test_register_rejects_malformed_payload(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "missing-password@example.com"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Malformed payload"}
